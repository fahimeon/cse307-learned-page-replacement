"""Create a cover and five pages of simple course-based content from measured results."""
import csv
from pathlib import Path
ROOT = Path(__file__).resolve().parent
with (ROOT/'results'/'summary.csv').open() as f:
    results = list(csv.DictReader(f))

def get(scenario, policy, phase, frames=16):
    return next(r for r in results if (r['scenario'],r['policy'],r['phase'],int(r['frames']))
                == (scenario,policy,phase,frames))

before, after = [], []
for policy in ['FIFO','LRU','OPT','Learned']:
    a,b,c = get('random',policy,'before'),get('random',policy,'after'),get('bursty',policy,'after')
    before.append(f"{policy} & {float(a['mean_faults']):.0f} & {100*float(a['mean_hit']):.1f} \\\\ \\hline")
    after.append(f"{policy} & {float(b['mean_faults']):.0f} & {100*float(b['mean_hit']):.1f} & "
                 f"{float(c['mean_faults']):.0f} & {100*float(c['mean_hit']):.1f} \\\\ \\hline")

plots=[]
for scenario in ['random','bursty']:
    commands=[]
    for policy,color,mark in [('FIFO','blue','square*'),('LRU','orange','triangle*'),
                              ('OPT','teal','diamond*'),('Learned','violet','*')]:
        coords=' '.join(f"({k},{100*float(get(scenario,policy,'after',k)['mean_hit']):.3f})"
                        for k in [8,12,16,24])
        commands.append(f'\\addplot[color={color},mark={mark},thick] coordinates {{{coords}}};'
                        f'\\addlegendentry{{{policy}}}')
    plots.append(r'\begin{minipage}{.48\textwidth}\centering'+
                 '\\begin{tikzpicture}\n\\begin{axis}[width=\\linewidth,height=4.5cm,'
                 'xlabel={Number of frames},ylabel={Hit ratio (\\%)},ymin=0,ymax=100,'
                 'xtick={8,12,16,24},axis background/.style={fill=white},'
                 'legend style={font=\\tiny,at={(0.02,0.98)},anchor=north west,fill=white,draw=black},'
                 'title={'+scenario.title()+' accesses},title style={font=\\small},tick label style={font=\\small}]\n'+
                 '\n'.join(commands)+'\n\\end{axis}\\end{tikzpicture}\\end{minipage}')

paper=r'''\documentclass[11pt,a4paper]{article}
\usepackage[margin=0.85in]{geometry}
\usepackage{amsmath,array,hyperref,pgfplots,graphicx}
\pgfplotsset{compat=1.18}
\hypersetup{colorlinks=true,urlcolor=black,citecolor=black,linkcolor=black}
\setlength{\parindent}{0pt}
\setlength{\parskip}{7pt}
\renewcommand{\arraystretch}{1.25}
\setlength{\arrayrulewidth}{0.5pt}
\linespread{1.06}
\begin{document}
\thispagestyle{empty}
\begin{center}
\vspace*{1cm}
\includegraphics[width=2.6cm]{assets/mist-logo.png}\\[10pt]
{\Large\bfseries Military Institute of Science and Technology}\\[5pt]
Department of Computer Science and Engineering\\[1.2cm]
{\large CSE-307: Operating Systems}\\[6pt]
{\large Term Paper --- Part B, Track 1}\\[1.2cm]
{\LARGE\bfseries Page Replacement under a Changing Access Pattern}\\[12pt]
{\large A Comparison of FIFO, LRU, Optimal, and a Simple Learned Policy}\\[1.5cm]
\begin{tabular}{|p{3cm}|p{9cm}|}\hline
Submitted by & Fahim Azmul Hasan \\ \hline
Student ID & 202414014 \\ \hline
Section & A \\ \hline
Level and term & Level 3, Term 1 \\ \hline
Submitted to & Lecturer Khaled Hasan Irfan \\ \hline
Submission date & 3 October 2026 \\ \hline
\end{tabular}
\end{center}

\newpage
\setcounter{page}{1}
\begin{abstract}
Page replacement policies decide which page to remove when memory is full and
a requested page is missing. This paper uses a Python simulation to compare
FIFO, LRU, Optimal, and a simple learned policy under a changing access pattern.
Each policy receives the same reference strings, allowing a fair comparison.
The study examines page faults and hit ratios as repeated accesses change to
random accesses or changing groups of frequently used pages. It explores how
locality and the number of available frames affect replacement decisions, and
whether a policy learned from one pattern remains useful when that pattern
changes. The discussion connects the observed behavior to familiar memory
management concepts and explains the limits of the learned approach.
\end{abstract}

\section{Introduction and Background}
\subsection{Pages, frames, and page faults}
Paging divides a process into equal-size pages
and physical memory into equal-size frames. A page fits into one frame. Virtual
memory allows some pages to remain outside RAM until they are needed
\cite{osc}. This is the background for the present experiment.

If a requested page is already in a frame, the access is a hit. If it is absent,
the access causes a page fault. When a free frame exists, the page can be loaded
without replacing another page. When all available frames are occupied, the OS
must choose a page to remove. FIFO, LRU, and Optimal
are different ways of making that choice \cite{ostep}.

\begin{center}
\begin{tabular}{|p{3cm}|p{10cm}|}\hline
Term & Meaning in this paper \\ \hline
Reference string & The ordered list of page numbers requested by the workload. \\ \hline
Hit & The requested page is already in a frame. \\ \hline
Page fault & The requested page is not in any available frame. \\ \hline
Locality & A program repeatedly uses a small group of pages over a period of time. \\ \hline
Working set & The group of pages that a program is actively using at a particular time. \\ \hline
\end{tabular}
\end{center}

\subsection{Purpose of the study}
The main question is simple: what happens to page faults when the access pattern
changes? A second question is whether a small learned policy can make better
replacement decisions than FIFO or LRU. The experiment uses the concepts
of locality, working sets, and hit and fault ratios \cite{osc,ostep}.
Standard memory-management texts also explain why avoiding unnecessary page
faults is important \cite{ostep,osc}.

The program simulates page replacement on Windows using Python. It does not
measure real Windows page faults, disk activity, or VMware performance.

\newpage
\section{Implementation of the Four Policies}
\subsection{FIFO, LRU, and Optimal}
The simulator starts with empty frames. Each page number in the reference string
is processed in order. On a hit, no page is loaded. On a fault, the page is loaded
into a free frame if one exists. Otherwise, the selected policy chooses a page to
replace. These steps follow the standard page replacement process \cite{ostep}.

\begin{center}
\begin{tabular}{|p{2cm}|p{10.8cm}|}\hline
Policy & Rule used when a replacement is needed \\ \hline
FIFO & Replace the page that entered the frames earliest. A hit does not change its arrival order. \\ \hline
LRU & Replace the page that has not been accessed for the longest time. Update its last-use record on every access. \\ \hline
Optimal & Replace the page whose next access is furthest in the future. Prefer a page that is never accessed again. \\ \hline
\end{tabular}
\end{center}

FIFO is easy to understand, but it may remove a page that is still used often.
LRU uses recent access history. Optimal is included as a comparison because it
has the lowest total fault count for the complete reference string. It needs
future knowledge, so it cannot be used in the same way in a real running program
\cite{cornell}. Its future knowledge includes both halves of the string.

\subsection{The simple learned policy}
The Track 1 brief requires a learned component. This study uses a decision tree:
a small model that learns a sequence of if-then decisions from examples
\cite{sklearn}. It is the main addition beyond the lecture algorithms.

Each possible page to replace is described by three values: how long ago it was
last used, how many times it was used in the previous 64 references, and how many
times it was used since the reference string began. These values represent recent use and
access frequency. The model does not receive the page's future accesses.

For training, eight separate reference strings are generated using the repeating
access pattern. LRU is run on these strings to create examples of pages present
when replacement is needed. The future of each training string is checked to mark
which pages would be good choices under the Optimal rule. The tree learns from
these examples. Its depth is limited to five decisions along any path to keep it
small. None of the strings used in the final experiments is used for training.

During the experiments, the model scores the pages currently in frames. The page
with the highest replacement score is removed. When scores are equal, the LRU
rule is used. Access-history values continue to update, but the model is not
trained again after the access pattern changes. Earlier research also studies
using learned predictions to help caching decisions \cite{lykouris}; this paper
uses only a small classroom example of that idea.

\subsection{Basic correctness checks}
The program was checked on short reference strings. It reproduces a standard
Belady example: FIFO gives 9 faults with three frames and 10 faults with four
frames \cite{cornell}. Additional checks cover LRU, Optimal, repeated accesses,
and the learned policy's tie rule. All six automated test methods passed.

\newpage
\section{Experimental Setup and Results}
\subsection{The same workload for every policy}
Each reference string contains 6,000 accesses to 64 possible pages. The pattern
changes after 3,000 accesses. Before the change, 90\% of accesses follow a repeating
sequence through pages 0--7; the rest access other pages. This creates a small
frequently used group, similar to a program repeatedly executing a loop.

Two second-half patterns are tested. In the random pattern, every page is equally
likely to be requested. In the bursty pattern, 80\% of accesses use one eight-page
group and 20\% can use any page. The group changes every 128 accesses. This represents a program moving
from one active group of pages to another.

\begin{center}
\begin{tabular}{|p{5cm}|p{7.8cm}|}\hline
Setting & Value \\ \hline
Accesses before / after the change & 3,000 / 3,000 \\ \hline
Possible page numbers & 0--63 \\ \hline
Frame counts tested & 8, 12, 16, and 24 \\ \hline
Repeated trials & Ten reference strings per second-half pattern \\ \hline
Main comparison in the tables & 16 frames \\ \hline
\end{tabular}
\end{center}

Every policy uses exactly the same generated reference strings. The frames are
not cleared when the pattern changes. This makes the comparison fair and lets
the experiment show what happens when old pages remain in memory.

The hit ratio is calculated from the number of successful accesses \cite{ostep}:
\begin{center}
Hit ratio = (Number of hits / Number of references) $\times$ 100\%
\end{center}
For example, 2,700 hits in 3,000 references give a 90\% hit ratio and 300 faults.
Hit ratio plus fault ratio equals 100\%.

\subsection{Measured results with 16 frames}
The following tables show averages across ten trials. Average faults are rounded
to whole numbers, and hit ratios to one decimal place. Exact values are available
in the repository's result files. Both scenarios use the same first-half pattern.

\begin{table}[h]
\centering\small
\caption{Before the change: repeating access pattern, 3,000 accesses per trial.}
\begin{tabular}{|l|r|r|}\hline
Policy & Average faults & Hit ratio (\%) \\ \hline
__BEFORE__
\end{tabular}
\end{table}

\begin{table}[h]
\centering\small
\caption{After the change: 3,000 accesses per trial under each pattern.}
\begin{tabular}{|l|r|r|r|r|}\hline
Policy & Random faults & Random hit (\%) & Bursty faults & Bursty hit (\%) \\ \hline
__AFTER__
\end{tabular}
\end{table}

\newpage
\section{Discussion of Results}
\subsection{Before the change: locality helps}
Before the change, pages 0--7 are used repeatedly. LRU and the learned policy both
keep many of these useful pages in frames and achieve about 91\% hits. FIFO gives
about 84\% hits because its rule considers arrival order rather than recent use.
This difference is consistent with temporal locality:
a page used recently is often used again soon \cite{ostep}.

The learned policy and LRU are almost equal before the change. Their small
difference does not show a clear advantage for learning. Optimal reaches about
94\% because it can check future requests before selecting a replacement.

\subsection{After the change: random and bursty accesses differ}
With random accesses, recent use no longer tells the policies which page will
be requested next. Sixteen frames hold only one quarter of the 64 possible pages,
so FIFO, LRU, and the learned policy achieve roughly 25\% hits. Optimal performs
better because it can see the future. This is why it is useful as a comparison,
but is not a realistic replacement rule for an unknown future string.

With bursty accesses, a small working set still exists, but it moves between
different groups of pages. LRU follows recent use and achieves about 79\% hits.
The learned policy achieves about 70\%. It was trained on a pattern where the
same group stays useful, so it does not follow changing groups as effectively.
The old access counts can also favor pages that are no longer useful. This is a
reasonable explanation of the result, rather than a separate test of each feature.

At 16 frames, the learned policy shows the largest hit-ratio drop in both tested
changes. In the bursty case, its drop is about 21 percentage points, compared
with about 12 for LRU. Learning from one pattern does not guarantee good decisions
under a different pattern.

\subsection{What happens when more frames are available?}
\begin{figure}[h]
\centering
__PLOTS__
\caption{Average hit ratios after the change at four frame counts.}
\end{figure}

In these experiments, more frames generally allow more useful pages to remain
in memory. The working-set idea explains why this helps \cite{osc}.
The separate FIFO test also reminds us that more frames do not improve every
possible FIFO reference string: Belady's anomaly is an exception \cite{cornell}.

\newpage
\section{Conclusion and References}
\subsection{Main findings and limits}
This experiment connects the page-replacement algorithms to a changing
reference string. The main findings are that locality helps LRU, random accesses
make past history less useful, and a changing working set requires the policy to
keep track of currently useful pages. The simple learned policy almost matches
LRU before the change but performs worse after the change to bursts. For the
main 16-frame comparison, LRU is the better simple choice after that change.

Frequent page faults can slow execution because
missing pages need to be brought into memory \cite{ostep,osc}. This simulation
counts faults; it does not measure disk delay or effective access time. It also
does not establish real system thrashing, which involves time spent servicing
faults. The tested strings are generated examples, so the conclusions apply to
these patterns rather than to every application.

The GitHub repository contains the scripts, raw results, and figures. The
experiment can be repeated using \texttt{python experiment.py}. AI assistance
was used for implementation, running the experiments, and drafting the report.
The numbers come from executed simulations. The student should review and
understand the work before submission.

\subsection{References}
The following sources support the memory-management explanations, classical
replacement policies, and simple learned component.

\begin{thebibliography}{9}\small
\bibitem{ostep} R. H. Arpaci-Dusseau and A. C. Arpaci-Dusseau,
\emph{Operating Systems: Three Easy Pieces}, Chapter 22, ``Beyond Physical Memory:
Policies.'' \url{https://pages.cs.wisc.edu/~remzi/OSTEP/vm-beyondphys-policy.pdf}.
\bibitem{cornell} Cornell University, CS 4410, ``Lecture 15: Page replacement,''
Summer 2015. \url{https://www.cs.cornell.edu/courses/cs4410/2015su/lectures/lec15-replacement.html}.
\bibitem{osc} A. Silberschatz, P. B. Galvin, and G. Gagne,
\emph{Operating System Concepts}, 10th ed., Wiley, 2018, Chapter 10, ``Virtual
Memory.'' Author's companion site: \url{https://www.os-book.com/OS10/}.
\bibitem{sklearn} scikit-learn developers, ``Decision Trees,'' documentation.
\url{https://scikit-learn.org/stable/modules/tree.html}. Accessed 3 October 2026.
\bibitem{lykouris} T. Lykouris and S. Vassilvitskii, ``Competitive caching with
machine learned advice,'' arXiv:1802.05399, 2018, revised 2020.
\url{https://arxiv.org/abs/1802.05399}.
\end{thebibliography}
\end{document}
'''
paper=paper.replace('__BEFORE__','\n'.join(before)).replace('__AFTER__','\n'.join(after))
paper=paper.replace('__PLOTS__','\n\\hfill\n'.join(plots))
(ROOT/'paper.tex').write_text(paper,encoding='utf-8')
print('Updated paper.tex: logo cover, high-level abstract, five external references')
