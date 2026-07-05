# EFX counterexample valuation data

The three files `Val{0,1,2}ByCard.txt` are the valuation tables of the EFX-nonexistence counterexample
(3 agents, 8 goods) of Akrami, Mayorov, Mehlhorn, Srinivas & Weidenbach, *A Counterexample to EFX: n≥3
Agents, m≥n+5 Items, Submodular Valuations via SAT-Solving* (arXiv:2604.18216, 2026).

Each line is `<8-bit bitstring> <rank>`: for agent i, the rank (0..255, a linear order / ordinal valuation)
of the subset of the 8 goods encoded by the bitstring. The full set `11111111` (rank 255) is implicit.

Retrieved verbatim from the paper's companion artifact (`nextcloud.mpi-klsb.mpg.de/index.php/s/25x4Q8eQErYsZE4`,
files `Val0ByCard.txt` / `Val1ByCard.txt` / `Val2ByCard.txt`); blank lines stripped, values unchanged.
