# Local acceptance evidence

Measured on 2026-10-01 on this Windows machine, CPU only, Python 3.12.10. No network calls were made by the project or installation.

- `python -m pytest -q`: 47 tests passed in 0.70 seconds.
- Installed CLI demo: `ldm fixtures --out demo`, `ldm run --input demo`, `ldm report --format md` completed in 0.812627 seconds combined, including three process startups and report rendering. This is a measured local execution time, not time saved against a human baseline.
- The Markdown report carries DATA PROVENANCE and shows 200 synthetic illustrative records, 70 active, 70 cooling, 60 cold. Supplied input amounts reconcile to 2000000 GBP minor units, split 700000/700000/600000.
- Exact cold-ID equality against the independent planted labels proves all 60 planted cold cases found, zero missed planted cold cases, and zero false positives on this synthetic fixture. No real-world predictive accuracy is measured.
- Mutation test changes one cold contact to the snapshot date and its amount to 17: counts become 71/70/59 and total amount becomes 1990017. A corrupted expectations file has no effect on calculations.
- The hand-written five-record example yields 2 active, 1 cooling, 2 cold and 1500 total minor units.
- Repeated saved JSON and rendered Markdown outputs are byte-identical. Empty input renders zero totals. Parse errors preserve line numbers and name their files. Failed report replacement leaves no temporary files.

Fixture ground truth is hand-derived: ten repeated cycles of days 0..19, with inclusive thresholds 7 and 14, and 10000 illustrative minor units per record. Tests compare the full cold-ID set as well as totals. These are software acceptance measurements only. No real trial, baseline savings, demand, revenue, or two-week operational verdict is claimed.
