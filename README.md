# DRTS Analyzer (Python)

## 1) Project overview
This project provides a Python tool to analyze **periodic real-time task sets** scheduled on one **preemptive single CPU** under:

- **Deadline Monotonic (DM)**
- **Earliest Deadline First (EDF)**

For each task set, the tool computes **analytical worst-case response times (WCRTs)** and compares them with **simulation-based response times** from repeated stochastic runs.

## 2) Task model
Each task \(\tau_i\) is defined by:

- **C**: worst-case execution time (WCET)
- **BCET**: best-case execution time
- **D**: relative deadline
- **T**: period
- **utilization**: \(U_i = C/T\)

Assumptions used by the analyzer:

- single core CPU
- fully preemptive scheduling
- independent periodic tasks
- constrained deadlines: **\(C \le D \le T\)**
- no blocking, no resource sharing overhead, and no OS overhead

## 3) Installation
Use Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
.venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

## 4) Running the analyzer
Run from the repository root:

```bash
python -m drts_analyzer analyze --input examples/tasksets.json --runs 100 --seed 42
```

Arguments:

- `--input`: path to JSON task-set file
- `--runs`: number of stochastic simulation runs
- `--seed`: random seed for reproducibility
- `--horizon`: optional simulation horizon (time units). If omitted, defaults to one hyperperiod

## 5) Input format
Complete JSON example:

```json
{
  "task_sets": [
    {
      "name": "example_1",
      "tasks": [
        { "id": "tau1", "C": 1, "BCET": 1, "D": 3, "T": 4 },
        { "id": "tau2", "C": 1, "BCET": 1, "D": 4, "T": 5 }
      ]
    }
  ]
}
```

## 6) Output interpretation
Each result row includes:

- `task_id`: task name
- `C`: WCET
- `BCET`: best-case execution time
- `D`: relative deadline
- `T`: period
- `U_i`: task utilization \(C/T\)
- `DM_WCRT`: analytical WCRT under Deadline Monotonic
- `DM_schedulable`: `true` if `DM_WCRT <= D`
- `EDF_WCRT`: analytical WCRT under EDF
- `EDF_schedulable`: `true` if `EDF_WCRT <= D`
- `DM_max_sim`: maximum observed simulated response time under DM
- `EDF_max_sim`: maximum observed simulated response time under EDF
- `analytical_minus_sim_gap`: analytical WCRT minus maximum observed simulation response time
- `deadline_misses`: number of missed deadlines in simulation
- `preemptions`: number of preemptions during simulation

## 7) How to interpret results
- If `WCRT <= D`, that task is analytically schedulable.
- If any task has `WCRT > D`, the whole task set is not schedulable under that algorithm.
- Analytical WCRT is based on WCET assumptions and is the value to trust for schedulability decisions.
- Simulation results are empirical observations and can be smaller than analytical WCRT.
- A simulation with zero deadline misses does **not** prove schedulability.
- EDF can schedule some high-utilization task sets that DM (or RM) cannot.

## 8) Running tests
```bash
pytest
```

The tests verify:

- scheduling order behavior
- analytical response-time calculations
- deadline miss and preemption tracking
- deterministic behavior with fixed random seeds

## 9) Project structure

```text
drts_analyzer/
  __init__.py
  __main__.py
  analyzer.py
  models.py
  utils.py
  dm_analysis.py
  edf_analysis.py
  simulator.py
  cli.py
examples/
  tasksets.json
tests/
  test_dm.py
  test_edf.py
  test_simulator.py
README.md
requirements.txt
```

## 10) Common mistakes
- Do not confuse RM and DM when deadlines are smaller than periods (`D < T`).
- Do not treat utilization alone as an EDF WCRT result.
- Do not use stochastic simulation as a proof of schedulability.
- Do not ignore preemptions.
- Do not compare response time to period when `D < T`; compare to `D`.
