# Learned Page Replacement under a Workload Shift

CSE-307 Operating Systems, Part B, **Track 1**.

**Student:** Fahim Azmul Hasan, ID 2024-14014, Section A, Level 3 Term 1.

**Submitted to:** Lecturer Khaled Hasan Irfan.

This project compares FIFO, LRU, Belady's Optimal (OPT), and a learned eviction
policy on identical synthetic page-reference traces. All experiments were executed
in Python on Windows. Ubuntu and VMware are not required for the attached Track 1
assignment. The reported page faults are **simulated cache misses**, not Windows
kernel faults or measurements of virtual-machine performance.

## Reproduce the experiments

Python 3.12 is recommended. From this repository in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest -v test_algorithms
.\.venv\Scripts\python.exe experiment.py
.\.venv\Scripts\python.exe audit_results.py
.\.venv\Scripts\python.exe build_paper.py
```

On Linux/macOS, use `.venv/bin/python` in place of the Windows executable path.
The experiment regenerates its files in `results/`. It needs no downloaded
dataset, network access, or model API. Reproduction with the pinned package
versions and seeds reproduces the trace and metric values; timing and image-file
bytes can vary with the environment.

## Design

- Universe: 64 equal-size pages; capacities: 8, 12, 16, and 24 frames.
- Every trace has 6,000 references and changes pattern at zero-based index 3,000.
- First half: probability 0.9 of the next page in a repeating sequence through
  pages 0–7; otherwise a uniform page from 8–63. The sequence advances only on a
  hot-set access.
- Random second half: independent uniform access to any of the 64 pages.
- Bursty second half: an eight-page block rotates every 128 accesses; probability
  0.8 of a uniform page in that block and 0.2 of a uniform page in the whole universe.
- Evaluation seeds: 100–109, for both scenarios. For each scenario and seed,
  every policy and capacity uses the exact same saved trace. Paired scenarios also
  have identical first halves. State is retained across the shift.
- Total: 20 evaluation traces, 320 policy runs, 1,920,000 per-access outcomes,
  and 640 phase-level metric records.

### Learned component

A depth-5 `DecisionTreeClassifier` (minimum leaf size 30, balanced class weights,
random state 307) is trained on **separate locality-only traces**, seeds 0–7.
The training generator uses only the first 3,000 references. LRU is replayed at
8, 16, and 24 frames to collect eviction candidates. Resident candidates whose
next use is furthest in the training trace receive class 1; other candidates
receive class 0. All tied oracle candidates are positive. Finite training-trace
endpoints can create multiple positives for pages never accessed again.

Features are recency, access frequency in the preceding 64 references, and total
historical frequency. No page ID, future-use position, scenario label, or phase
label enters the model. At a full-cache fault, the learned policy evicts the
resident candidate with the largest class-1 score; ties use LRU, then page ID.
The classifier is frozen during evaluation. Statistics update online, but there
is no online retraining. Balanced-class leaf scores are ranking scores, not
calibrated correctness probabilities.

The trained tree contains 31 leaves, from 189,312 candidate rows (25,183 positive).
Hyperparameters were fixed before interpreting the evaluation results. Evaluation
traces do not enter training. OPT alone has full evaluation-trace future access;
it is an offline benchmark, not a deployable online policy. Its total faults are
a lower bound for the full trace; phase counts need not separately be minima.

## Measured results

Mean results at **16 frames**, ten evaluation seeds and 3,000 accesses per phase:

| Policy | Before shift hit % | After random hit % | After bursty hit % |
|---|---:|---:|---:|
| FIFO | 84.16 | 24.85 | 72.50 |
| LRU | 91.11 | 25.07 | 78.65 |
| OPT | 93.65 | 56.46 | 85.97 |
| Learned | 91.14 | 24.53 | 70.06 |

The learned policy nearly matches LRU before the shift. It does not produce a
reliable improvement, and it performs worse than LRU and FIFO after the bursty
shift at 16 frames. This negative result is retained and analyzed. Under uniform
random references, online hit ratios approach frames / 64 because access history
does not predict the next independently selected page. Larger capacities reduce
fault pressure. Full per-seed values, means, and sample standard deviations are
saved rather than only a selected run.

![Phase hit ratios; error bars show between-seed standard deviation](results/phase_hits.png)
![Mean hit ratios over 250-reference windows; dashed line marks the shift](results/timeline.png)
![After-shift hit ratios versus capacity](results/capacity.png)

## Files

| File | Purpose |
|---|---|
| `experiment.py` | Workload generator, four policies, training, raw export, and figures |
| `test_algorithms.py` | Known FIFO/LRU examples and independent exhaustive OPT checks |
| `audit_results.py` | Trace hashes, per-access/summary consistency, OPT total-fault check |
| `results/traces/` | Eight training traces and twenty evaluation traces |
| `results/training_candidates.csv.gz` | Training features and future-based labels |
| `results/access_results.csv.gz` | All 1,920,000 simulated access outcomes |
| `results/raw_metrics.csv` | Per-seed before/after fault counts and hit ratios |
| `results/summary.csv` | Means and sample SD across ten seeds |
| `results/window_metrics.csv` | Per-seed 250-reference-window hit ratios at 16 frames |
| `results/metadata.json` | Versions, seeds, model details, timing, and evaluation trace hashes |
| `results/tree.txt` | Readable decision-tree rules |
| `results/validation.txt` | Saved experimental consistency audit |
| `paper.tex` | Standalone LaTeX paper with tables and inline vector-plot data |
| `build_paper.py` | Regenerate the LaTeX source from measured results |
| `build_pdf.py` | Render the same paper text and measured chart using ReportLab |
| `output/pdf/CSE307_Track1_Term_Paper.pdf` | Visually checked six-page report |

## Paper and PDF generation

The requested six-page report is included. It exceeds the attached brief's 2–3
pages and the announcement's 3–4 pages; use a shorter version if the lecturer
requires those limits. No six-page requirement appears in the supplied brief.

`paper.tex` is self-contained, including bibliography entries and chart
coordinates. It can be uploaded to a LaTeX editor such as Overleaf as a single
file. Compile using a normal pdfLaTeX workflow with `pgfplots` available. The native
editor was opened, but its compiler failed with **“Unable to find standard
directories for platform.”** Consequently, this environment has **not verified
LaTeX compilation or the compiled LaTeX page count**. No local TeX distribution
was installed. The included PDF was rendered with Python/ReportLab from the same
source content and visually inspected on all six pages. It is not represented as
a successfully compiled LaTeX PDF.

To regenerate the included PDF without a TeX compiler:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-pdf.txt
.\.venv\Scripts\python.exe build_paper.py
.\.venv\Scripts\python.exe build_pdf.py
```

PDF layout uses the same six content sections, citations, and measured table,
with the equivalent Matplotlib capacity chart in place of the inline LaTeX plot.

## Validation

Six unit-test methods passed, including learned tie-breaking and prefix-causality
checks. OPT also matched an independent exhaustive solver
on 80 short traces at three capacities, or 240 comparisons. The saved audit
verified all twenty evaluation-trace hashes, checked all per-access fault totals
against 640 phase-level metric records, and confirmed OPT's total faults were no
greater than any other policy for all eighty trace/capacity pairs.

The experiment does not measure CPU load, kernel paging, fault-service time,
classifier confidence calibration, or production inference overhead. It does
not claim a deployment speedup or causal feature attribution.

## AI assistance disclosure and author review

An AI coding assistant was used to generate the implementation, construct and
execute the experimental workflow, analyze the output, and draft the README and
paper. The reported values are from actual executed simulations; no result was
invented. The student must review, understand, and take responsibility for the
experimental design, results, and analysis, as required by the course brief.
The generated paper should be reviewed before submission. Do not describe the
design, code, or prose as produced without AI assistance.

For a 3–5 minute demo, explain the four policies, point out the shift in the saved
trace, show the summary table and timeline chart, explain why the random phase
limits historical prediction, and discuss why the learned model performs worse
on moving hot sets. The experiment can be rerun live after installing dependencies.

## References

1. R. H. Arpaci-Dusseau and A. C. Arpaci-Dusseau, *Operating Systems: Three Easy
   Pieces*, Chapter 22, [Beyond Physical Memory: Policies](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-beyondphys-policy.pdf).
2. Cornell University CS 4410, [Lecture 15: Page replacement](https://www.cs.cornell.edu/courses/cs4410/2015su/lectures/lec15-replacement.html), Summer 2015.
3. scikit-learn developers, [Decision Trees](https://scikit-learn.org/stable/modules/tree.html), accessed 3 October 2026.
4. T. Lykouris and S. Vassilvitskii, [Competitive caching with machine learned advice](https://arxiv.org/abs/1802.05399), 2018, revised 2020.
