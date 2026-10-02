"""Reproducible CSE307 Track 1 simulation; all online features use past accesses."""
from collections import Counter, deque
from pathlib import Path
import csv
import gzip
import hashlib
import json
import platform
import sys
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import sklearn
from sklearn.tree import DecisionTreeClassifier, export_text

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results'
FEATURES = ['recency', 'frequency64', 'frequency_total']
POLICIES = ['FIFO', 'LRU', 'OPT', 'Learned']
CAPACITIES = [8, 12, 16, 24]
SEEDS = list(range(100, 110))
HALF = 3000


def workload(seed, scenario='random', half=HALF):
    rng = np.random.default_rng(seed)
    trace = []
    cursor = 0
    for _ in range(half):
        if rng.random() < .9:
            trace.append(cursor % 8)
            cursor += 1
        else:
            trace.append(int(rng.integers(8, 64)))
    for i in range(half):
        if scenario == 'random':
            trace.append(int(rng.integers(0, 64)))
        elif scenario == 'bursty':
            base = ((i // 128) % 8) * 8
            trace.append(base + int(rng.integers(8)) if rng.random() < .8
                         else int(rng.integers(64)))
        else:
            raise ValueError(scenario)
    return trace


def next_uses(trace):
    future = {}
    answer = [0] * len(trace)
    for i in range(len(trace) - 1, -1, -1):
        page = trace[i]
        answer[i] = future.get(page, len(trace) + 1)
        future[page] = i
    return answer


def simulate(trace, frames, policy, model=None, collect=False):
    """Return fault flags and optional oracle-labelled rows on LRU cache states.

    The next-use map is consulted only by OPT or offline training labels.
    Future data are never input to the learned policy.
    """
    if frames < 1:
        raise ValueError('frames must be positive')
    cache, loaded, last = set(), {}, {}
    total, recent = Counter(), Counter()
    window = deque()
    nxt = next_uses(trace) if policy == 'OPT' or collect else None
    future = {} if nxt is not None else None
    if nxt is not None:
        for i, page in reversed(list(enumerate(trace))):
            future[page] = i
    flags, samples = [], []
    for i, page in enumerate(trace):
        if nxt is not None:
            future[page] = nxt[i]
        fault = page not in cache
        flags.append(int(fault))
        if fault:
            if len(cache) == frames:
                candidates = sorted(cache)
                x = [[i - last[p], recent[p], total[p]] for p in candidates]
                if collect:
                    furthest = max(future[p] for p in candidates)
                    samples.extend((i, p, *row, int(future[p] == furthest))
                                   for p, row in zip(candidates, x))
                if policy == 'FIFO':
                    victim = min(candidates, key=lambda p: (loaded[p], p))
                elif policy == 'LRU':
                    victim = min(candidates, key=lambda p: (last[p], p))
                elif policy == 'OPT':
                    victim = max(candidates, key=lambda p: (future[p], -p))
                elif policy == 'Learned':
                    positive = list(model.classes_).index(1)
                    score = model.predict_proba(x)[:, positive]
                    # Equal scores fall back to least recently used, then page ID.
                    victim = max(zip(candidates, score),
                                 key=lambda pair: (pair[1], i-last[pair[0]], -pair[0]))[0]
                else:
                    raise ValueError(policy)
                cache.remove(victim)
            cache.add(page)
            loaded[page] = i
        last[page] = i
        total[page] += 1
        window.append(page)
        recent[page] += 1
        if len(window) > 64:
            recent[window.popleft()] -= 1
    return np.array(flags, dtype=np.int8), samples


def write_csv(path, rows):
    rows = list(rows)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / 'traces').mkdir(exist_ok=True)
    training, train_manifest = [], []
    for seed in range(8):
        trace = workload(seed)[:HALF]
        write_csv(OUT / 'traces' / f'train_{seed}.csv',
                  ({'index':i, 'page':p} for i,p in enumerate(trace)))
        for capacity in [8, 16, 24]:
            _, rows = simulate(trace, capacity, 'LRU', collect=True)
            training.extend((seed, capacity, *r) for r in rows)
        train_manifest.append(seed)
    x = np.array([r[4:7] for r in training])
    y = np.array([r[7] for r in training])
    model = DecisionTreeClassifier(max_depth=5, min_samples_leaf=30,
                                   class_weight='balanced', random_state=307)
    model.fit(x, y)
    with gzip.open(OUT / 'training_candidates.csv.gz', 'wt', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['seed','frames','index','page',*FEATURES,'oracle_candidate'])
        writer.writerows(training)
    (OUT / 'tree.txt').write_text(export_text(model, feature_names=FEATURES), encoding='utf-8')
    all_rows, window_rows, hashes = [], [], {}
    started = time.perf_counter()
    with gzip.open(OUT / 'access_results.csv.gz', 'wt', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['scenario','seed','frames','policy','index','page','fault'])
        for scenario in ['random','bursty']:
            for seed in SEEDS:
                trace = workload(seed, scenario)
                path = OUT / 'traces' / f'{scenario}_{seed}.csv'
                write_csv(path, ({'index':i,'phase':'before' if i < HALF else 'after','page':p}
                                 for i,p in enumerate(trace)))
                hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
                for capacity in CAPACITIES:
                    for policy in POLICIES:
                        faults, _ = simulate(trace, capacity, policy, model)
                        writer.writerows((scenario,seed,capacity,policy,i,p,int(v))
                                         for i,(p,v) in enumerate(zip(trace,faults)))
                        for phase,a,b in [('before',0,HALF),('after',HALF,2*HALF)]:
                            count = int(faults[a:b].sum())
                            all_rows.append(dict(scenario=scenario,seed=seed,frames=capacity,
                                                 policy=policy,phase=phase,accesses=b-a,
                                                 faults=count,hit_ratio=1-count/(b-a)))
                        if capacity == 16:
                            for a in range(0,2*HALF,250):
                                window_rows.append(dict(scenario=scenario,seed=seed,policy=policy,
                                                        midpoint=a+125,hit_ratio=1-float(faults[a:a+250].mean())))
                print(f'Completed {scenario}, seed {seed}', flush=True)
    write_csv(OUT / 'raw_metrics.csv', all_rows)
    write_csv(OUT / 'window_metrics.csv', window_rows)
    summary = []
    for scenario in ['random','bursty']:
        for capacity in CAPACITIES:
            for policy in POLICIES:
                for phase in ['before','after']:
                    rows = [r for r in all_rows if (r['scenario'],r['frames'],r['policy'],r['phase'])
                            == (scenario,capacity,policy,phase)]
                    hit = np.array([r['hit_ratio'] for r in rows])
                    summary.append(dict(scenario=scenario,frames=capacity,policy=policy,phase=phase,
                                        mean_faults=float(np.mean([r['faults'] for r in rows])),
                                        mean_hit=float(hit.mean()),sd_hit=float(hit.std(ddof=1)),n=len(rows)))
    write_csv(OUT / 'summary.csv', summary)
    metadata = dict(python=sys.version,numpy=np.__version__,sklearn=sklearn.__version__,
                    matplotlib=matplotlib.__version__,platform=platform.platform(),
                    training_seeds=train_manifest,test_seeds=SEEDS,half=HALF,pages=64,
                    capacities=CAPACITIES,training_rows=len(y),positive_rows=int(y.sum()),
                    tree_depth=int(model.get_depth()),tree_leaves=int(model.get_n_leaves()),
                    feature_importance=dict(zip(FEATURES,model.feature_importances_.tolist())),
                    evaluation_seconds=time.perf_counter()-started,trace_sha256=hashes)
    (OUT / 'metadata.json').write_text(json.dumps(metadata,indent=2), encoding='utf-8')
    plots(summary,window_rows)
    print(json.dumps(metadata,indent=2))


def plots(summary, windows):
    colors = ['#52738f','#c07838','#36826c','#915990']
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig, axs = plt.subplots(1,2,figsize=(10,3.6),sharey=True)
    for ax,scenario in zip(axs,['random','bursty']):
        for offset,(policy,color) in enumerate(zip(POLICIES,colors)):
            rows = [next(r for r in summary if (r['scenario'],r['frames'],r['policy'],r['phase'])
                         == (scenario,16,policy,phase)) for phase in ['before','after']]
            ax.bar(np.arange(2)+(offset-1.5)*.18,[r['mean_hit']*100 for r in rows],.18,
                   yerr=[r['sd_hit']*100 for r in rows],label=policy,color=color,capsize=3)
        ax.set_xticks([0,1],['Before shift','After shift'])
        ax.set_title('Locality to '+scenario)
        ax.set_ylim(0,100)
    axs[0].set_ylabel('Hit ratio (%)'); axs[1].legend(ncol=2,fontsize=8)
    fig.tight_layout(); fig.savefig(OUT/'phase_hits.png',dpi=200); plt.close(fig)
    fig,axs = plt.subplots(1,2,figsize=(10,3.6),sharey=True)
    for ax,scenario in zip(axs,['random','bursty']):
        for policy,color in zip(POLICIES,colors):
            positions = sorted({r['midpoint'] for r in windows})
            values = [np.mean([r['hit_ratio'] for r in windows if r['scenario']==scenario
                              and r['policy']==policy and r['midpoint']==p])*100 for p in positions]
            ax.plot(positions,values,label=policy,color=color)
        ax.axvline(HALF,color='black',ls='--',lw=1)
        ax.set_title('Locality to '+scenario); ax.set_xlabel('Access index (250-access windows)')
    axs[0].set_ylabel('Mean hit ratio (%)'); axs[1].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(OUT/'timeline.png',dpi=200); plt.close(fig)
    fig,axs = plt.subplots(1,2,figsize=(10,3.6),sharey=True)
    for ax,scenario in zip(axs,['random','bursty']):
        for policy,color in zip(POLICIES,colors):
            values = [next(r['mean_hit']*100 for r in summary if
                           (r['scenario'],r['frames'],r['policy'],r['phase'])==(scenario,k,policy,'after'))
                      for k in CAPACITIES]
            ax.plot(CAPACITIES,values,'o-',color=color,label=policy)
        ax.set_title('After shift: '+scenario); ax.set_xlabel('Page frames'); ax.set_xticks(CAPACITIES)
    axs[0].set_ylabel('Mean hit ratio (%)'); axs[1].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(OUT/'capacity.png',dpi=200); plt.close(fig)


if __name__ == '__main__':
    main()
