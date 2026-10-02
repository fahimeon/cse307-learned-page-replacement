"""Check saved experimental outcomes independently of summary generation."""
import csv
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path

root = Path(__file__).resolve().parent / 'results'
meta = json.loads((root/'metadata.json').read_text())
for name, digest in meta['trace_sha256'].items():
    assert hashlib.sha256((root/'traces'/name).read_bytes()).hexdigest() == digest
counts = defaultdict(lambda: [0,0])
with gzip.open(root/'access_results.csv.gz','rt') as f:
    for r in csv.DictReader(f):
        phase = 'before' if int(r['index']) < 3000 else 'after'
        key = (r['scenario'],r['seed'],r['frames'],r['policy'],phase)
        counts[key][0] += 1
        counts[key][1] += int(r['fault'])
assert sum(n for n, _ in counts.values()) == 1920000
raw = list(csv.DictReader((root/'raw_metrics.csv').open()))
assert len(raw) == 640
for r in raw:
    key = tuple(r[k] for k in ['scenario','seed','frames','policy','phase'])
    assert counts[key] == [3000,int(r['faults'])]
    assert abs(float(r['hit_ratio']) - (1-int(r['faults'])/3000)) < 1e-12
for scenario in ['random','bursty']:
    for seed in map(str,range(100,110)):
        for frames in map(str,[8,12,16,24]):
            totals = {policy: sum(counts[(scenario,seed,frames,policy,phase)][1]
                                 for phase in ['before','after'])
                      for policy in ['FIFO','LRU','OPT','Learned']}
            assert all(totals['OPT'] <= x for x in totals.values())
(root/'validation.txt').write_text(
    'All 20 evaluation trace hashes match.\n'
    'All 1,920,000 outcomes agree with 640 saved phase-level records.\n'
    'Every hit ratio equals 1 - faults / 3000.\n'
    'OPT total faults are no greater than any other policy in all 80 trace/capacity pairs.\n',
    encoding='utf-8')
print((root/'validation.txt').read_text())
