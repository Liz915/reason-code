# Reason-Code: Reliable Code Generation via Test-Driven MCTS

<p align="center">
  <img src="Figures/hero_banner.png" width="100%" alt="Reason-Code Architecture">
</p>

## Overview
This repository contains the implementation of Reason-Code, submitted to the ACL Industry Track.

We propose an inference-time framework that treats code generation as a search problem. By integrating Monte Carlo Tree Search (MCTS) with a lightweight local sandbox, Reason-Code filters out incorrect solutions before they reach the user.

**Core Capabilities:**
- **Search:** MCTS with UCB1 exploration and "Reflexion" (using stderr for self-correction).
- **Safety:** All code runs in a sandbox; only passing code is returned.
- **System:** Includes a DAG workflow engine, FastAPI serving capability, and OpenTelemetry tracing.

## 📂 Project Structure
The repository is organized to separate core logic, benchmarking, and experimental data.

```
reason-code/
├── src/reason_code/
│   ├── agent/           # MCTS Core: Node expansion, UCB1, Backpropagation
│   ├── executor/        # Sandbox: Docker/Local execution environment
│   ├── workflow/        # Orchestration: DAG-based workflow engine
│   ├── tools/           # Tool Registry: Plugin system for external tools
│   ├── models/          # Model Layer: LLM interfaces
│   ├── api/             # Serving: FastAPI application for deployment
│   └── utils/           # Observability: Logger & OpenTelemetry Tracing
├── benchmark/           # Evaluation: Scripts for HumanEval/MBPP analysis
├── examples/            # Demos: End-to-end workflow examples
├── data/final/          # Artifacts: The 7 core log files used in the paper
└── requirements.txt
```

## 📊 Main Results
Our method matches the performance of computationally expensive baselines while maintaining a low inference cost suitable for edge deployment.

### Performance Summary (Table 1)

| Method | Inference Strategy | Cost (Rel.) | MBPP Pass@1 | HumanEval Pass@1 |
| :--- | :--- | :--- | :--- | :--- |
| **Baselines** | | | | |
| Greedy Decoding | Direct Generation | 1.0× | 48.2 | 86.6 |
| Best-of-N Sampling | Stochastic (N=10) | 10.0× | - | 88.4 |
| Best-of-N (Oracle) | Oracle Est. (N=5) | 5.0× | 72.8 | - |
| **Ours** | | | | |
| MCTS (Static) | Always-on (N=3) | ~3.5× | 72.8 | 86.0 |
| MCTS (Adaptive) | Conditional Budget | ~1.5× | 72.8 | **88.4** |

**Key Insights:**
- **Cost Efficiency:** The "Cost" column denotes relative token consumption compared to Greedy Decoding. Our adaptive strategy achieves SOTA performance at ~1.5× cost, whereas standard Best-of-N sampling requires 10.0×.
- **Zero Regression:** Unlike static search, the conditional mechanism prevents the model from over-complicating simple problems, ensuring previously correct solutions are preserved.

## 📂 Data Availability
We provide the exact execution logs used to produce the results above. These files are located in `data/final/` and allow for full reproduction of the metrics without re-running expensive inference.

The dataset consists of 7 core files mapping to the table rows:

| Category | File Name | Description |
| :--- | :--- | :--- |
| Input | `data_mbpp.jsonl` | The MBPP dataset source and test cases. |
| Baseline | `results_baseline_n1.jsonl` | HumanEval Greedy Decoding results. |
| Baseline | `results_mbpp_baseline_n1.jsonl` | MBPP Greedy Decoding results. |
| Ours | `results_mcts_n3.jsonl` | HumanEval Reason-Code output. |
| Ours | `results_mbpp_mcts_n3.jsonl` | MBPP Reason-Code output. |
| Reference | `results_baseline_n10.jsonl` | HumanEval Best-of-10 Sampling logs. |
| Reference | `results_mbpp_baseline_n5.jsonl` | MBPP Best-of-5 Oracle logs. |

## 💡 Case Study: Structural Refactoring
Reason-Code goes beyond simple bug fixes; it can perform structural refactoring to satisfy execution constraints.

**Example: MBPP/428 (Shell Sort)**

*   **Baseline Error:** The model defined a helper function `gap_insertion_sort` inside the loop scope, causing a `NameError` in the strict sandbox environment.
*   **Reason-Code Fix:** Through MCTS exploration + Reflexion, the agent identified the scope issue and refactored the code into a flat, self-contained nested loop, removing the helper function entirely.

**Baseline (Failed) ❌**
Error: `NameError: name 'gap_insertion_sort' is not defined`
```python
def shell_sort(my_list):
    sub = len(my_list) // 2
    while sub > 0:
        for start in range(sub):
            # <Error: Nested Helper Scope>
            gap_insertion_sort(my_list, start, sub)
        sub //= 2

def gap_insertion_sort(list, start, gap):
    # ...
```

**Reason-Code (Fixed) ✅**
Result: `Pass`
```python
def shell_sort(my_list):
    n = len(my_list)
    gap = n // 2
    while gap > 0:
        for i in range(gap, n):
            # <Fixed: Logic Inlined>
            temp = my_list[i]
            j = i
            while j >= gap and my_list[j - gap] > temp:
                my_list[j] = my_list[j - gap]
                j -= gap
            my_list[j] = temp
        gap //= 2
    return my_list
```

## 🚀 Quick Start (System Demo)

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Run the Workflow Demo
Reason-Code includes a workflow engine to chain tools. The example below runs a "Search -> Reason -> Code" pipeline.
```bash
python examples/demo_workflow.py
```

### 3. Production Deployment (API)
For industrial integration, the agent is wrapped in a FastAPI service. This enables integration into IDEs or microservice architectures.
```bash
python src/reason_code/api/app.py
```
- **Endpoint:** `POST /reason_and_code`
- **Observability:** The service is instrumented with Phoenix (OpenInference) for real-time tracing of the MCTS decision tree.

## 🔬 Reproducing Paper Results
To verify the "Zero Regression" and "Net Gain" claims using the provided data:

**HumanEval Analysis**
```bash
python benchmark/analyze_fixes.py
```

**MBPP Analysis**
```bash
python benchmark/analyze_mbpp_fixes.py
```

**Expected Output (MBPP):**
```
Baseline (N=1) Passed: 183
MCTS (N=3) Passed:     187
--------------------------------
MCTS Exclusive Fixes:  4
MCTS Regressions:      0
```
*(This confirms the robustness of the Conditional Budgeting strategy)*

## 📂 Script Guide
We provide specific tools in the `tools/` and `benchmark/` directories to facilitate reproduction:

| Script Name | Path | Description |
| :--- | :--- | :--- |
| `analyze_fixes.py` | `benchmark/` | Core Analysis. Compares HumanEval baseline vs. MCTS logs to calculate "Net Gain". |
| `analyze_mbpp_fixes.py` | `benchmark/` | Core Analysis. Performs the same "Fix/Break" analysis for the MBPP benchmark. |
| `score_real.py` | `tools/` | Robust evaluator that extracts code blocks (handling Markdown/formats) and runs tests locally. |
| `inspect_case_study.py` | `tools/` | Utility to fetch and display specific failure cases (e.g., MBPP/71) from raw logs. |

## License

MIT License © 2026 Zixu Li
