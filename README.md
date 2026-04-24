# Reason-Code: Reliable Code Generation via Test-Driven Monte Carlo Tree Search

This repository contains the code, prompts, and curated reproduction artifacts for the ACL 2026 Industry Track paper **Reason-Code: Reliable Code Generation via Test-Driven Monte Carlo Tree Search**.

Reason-Code is an inference-time framework for reliable code generation under deployment constraints. It combines execution-guided repair, conditional budgeting, and lightweight tree search to improve reliability without the linear cost growth of large-sample Best-of-$N$ sampling.

## Paper

- OpenReview: [Reason-Code: Reliable Code Generation via Test-Driven Monte Carlo Tree Search](https://openreview.net/forum?id=rDbAfnKfhq)

## Scope of This Release

This is a **minimal public reproducibility release**. It focuses on:

- the core inference-time search and repair logic;
- sandboxed execution and evaluation;
- benchmark runners for MBPP and HumanEval;
- analysis scripts used for the camera-ready revision;
- curated result files required to reproduce the tables and claims in the paper.

This release does **not** include every intermediate log, draft rebuttal artifact, local cache, or experimental byproduct generated during development.

## Repository Layout

```text
src/reason_code/           core search, repair, model, and execution modules
benchmarks/                experiment entry points
tools/                     analysis and plotting scripts
data/final/                canonical MBPP input and original main-result logs
Figures/                   figures referenced by the paper
released_results/          curated paper-required result artifacts
```

## Environment

- Python 3.10+
- Install dependencies with:

```bash
pip install -r requirements.txt
```

Some end-to-end runs require a local model backend and environment-specific model configuration. The curated outputs in `released_results/` are therefore the canonical paper artifacts and the most direct starting point for verification.

## Comparison Families in the Paper

The camera-ready paper reports **two different comparison families**:

1. **Deployment-oriented main comparison**
   - used for the main cost/accuracy story;
   - includes Greedy, Best-of-$N$ sampling references, and adaptive/static Reason-Code.

2. **Matched-budget controlled comparison**
   - used to isolate what is gained from execution-guided adaptive inference versus the specific choice of search controller;
   - aligns temperature, token caps, evaluator, task IDs, and call budgets across methods.

For HumanEval, the matched-budget controlled comparison in the paper uses the **canonical seed42 run** for internal consistency with paired significance analysis.

## Curated Reproduction Artifacts

The directory `released_results/` contains the canonical files needed for the paper:

- `deployment_main/`
  - original main-result logs used for the deployment-oriented comparison.
- `controlled_analyses/matched_budget/`
  - canonical seed42 matched-budget summaries, manifests, and paired statistics.
- `controlled_analyses/mechanism_ablation/`
  - independent filtering vs. random tree search vs. UCB-MCTS summaries and paired statistics.
- `controlled_analyses/test_sensitivity/`
  - full-test vs. reduced-assert summaries.
- `controlled_analyses/timing/`
  - timing decomposition summaries for the canonical matched-budget runs.

## Core Entry Points

Main benchmark runners:

- `benchmarks/run_paper_experiments.py`
- `benchmarks/run_mbpp.py`
- `benchmarks/run_fairness_experiment.py`

Main analysis scripts:

- `tools/analyze_rebuttal_stats.py`
- `tools/compare_test_sensitivity.py`
- `tools/calc_latency.py`
- `tools/score_real.py`

## Notes on Public Results

- The repository intentionally exposes **curated canonical artifacts**, not every intermediate development log.
- The matched-budget HumanEval results in the paper use the canonical seed42 run, not the earlier formal batch with the alternate `best_of_n` outcome.
- Repeated seed42/43/44 reruns are treated as reproducibility checks under the current backend path rather than independent variance estimates.

## Citation

If you use this repository, please cite the ACL 2026 Industry Track paper.
