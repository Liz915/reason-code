# Released Results

This directory contains the **curated result artifacts** needed to support the camera-ready paper.

## Contents

- `deployment_main/`
  - original logs for the deployment-oriented main comparison.
- `controlled_analyses/matched_budget/`
  - canonical matched-budget summaries, manifests, and paired statistics.
- `controlled_analyses/mechanism_ablation/`
  - summaries and paired statistics for independent filtering, random tree search, and UCB-MCTS.
- `controlled_analyses/test_sensitivity/`
  - full-test and reduced-assert summaries used for sensitivity analysis.
- `controlled_analyses/timing/`
  - timing decomposition summaries for the canonical matched-budget runs.

## Notes

- HumanEval matched-budget results use the **canonical seed42 run**.
- MBPP matched-budget paired statistics use the **single-run 257-task** analysis rather than the 3-seed aggregate.
- These files are intentionally curated. Full development logs, caches, and internal rebuttal packaging artifacts are not included here.
