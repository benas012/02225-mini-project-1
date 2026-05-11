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
python -m drts_analyzer analyze-csv-folder --input tasksets --output results --runs 100 --seed 42
```

Arguments:

- `--input`: path to the course-provided CSV task-set folder
- `--output`: folder where result CSV files are written
- `--runs`: number of stochastic simulation runs
- `--seed`: random seed for reproducibility
- `--max-hyperperiod`: maximum hyperperiod for exact EDF analytical analysis
- `--simulation-horizon`: optional simulation horizon. If omitted, simulation uses `min(hyperperiod, max_hyperperiod)`

## 5) Input format
The project uses the course-provided CSV task sets. Each CSV row describes one task with columns:

- `TaskID`: task identifier
- `Jitter`: release jitter; must be `0` for this implementation
- `BCET`: best-case execution time
- `WCET`: worst-case execution time
- `Period`: task period
- `Deadline`: relative deadline
- `PE`: processing element/core; must be `0` for this single-core project

## 6) Output interpretation
`results/taskset_summary.csv` contains one row per task set. `results/task_details.csv` contains one row per task. Each task-detail row includes:

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
- `DM_analytical_minus_sim_gap`: DM analytical WCRT minus maximum observed DM simulation response time
- `EDF_analytical_minus_sim_gap`: EDF analytical WCRT minus maximum observed EDF simulation response time
- `DM_deadline_misses` and `EDF_deadline_misses`: missed deadlines in simulation
- `DM_preemptions` and `EDF_preemptions`: preemptions during simulation

## 7) How to interpret results
- If `WCRT <= D`, that task is analytically schedulable.
- If any task has `WCRT > D`, the whole task set is not schedulable under that algorithm.
- Analytical WCRT is based on WCET assumptions and is the value to trust for schedulability decisions.
- Simulation results are empirical observations and can be smaller than analytical WCRT.
- A simulation with zero deadline misses does **not** prove schedulability.
- EDF can schedule some high-utilization task sets that DM (or RM) cannot.

## 8) Running tests
```bash
python -m pytest
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
tests/
  test_analyzer.py
  test_dm.py
  test_edf.py
  test_csv_loader.py
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

## Using the course-provided CSV task sets

The `tasksets/` folder is intentionally not committed to GitHub because it can be large. Download and unzip the provided task sets locally, then place them at:

- `tasksets/`

Run batch CSV analysis with:

```bash
python -m drts_analyzer analyze-csv-folder --input tasksets --output results --runs 100 --seed 42 --verbose
```

Results will be written to:

- `results/taskset_summary.csv`
- `results/task_details.csv`

### Folder naming convention

- `automotive-utilDist`: automotive-like generated task sets
- `unifast-utilDist`: task sets generated using utilization distribution
- `uniform-discrete-perDist`: task sets with uniformly/discretely generated periods
- `1-core`: single-core task sets
- `25-task`: number of tasks
- `0-jitter`: no release jitter
- `0.60-util`: intended utilization group
- final CSV index such as `_0`, `_1`, `_2`: different randomly generated instances in the same group

## Performance and sampling

The provided task-set folders may contain many CSV files, and some task sets can produce very large hyperperiods (`H = lcm(periods)`). Since EDF analytical WCRT in this project is tied to hyperperiod-based analysis, this can become computationally expensive.

To keep analysis practical while preserving an academically valid methodology, the tool supports representative sampling, utilization/distribution filtering, and hyperperiod limits.

Recommended command:

```bash
python -m drts_analyzer analyze-csv-folder \
  --input tasksets \
  --output results \
  --runs 20 \
  --seed 42 \
  --samples-per-util 5 \
  --util-levels 0.30 0.50 0.70 0.90 \
  --max-hyperperiod 10000000 \
  --simulation-horizon 1000000
```

Interpretation notes:

- DM analytical results are still valid even when EDF analytical analysis is skipped.
- Skipped EDF analytical results indicate the exact hyperperiod method was too expensive for that task set.
- Simulation outputs are bounded empirical observations, not schedulability proofs.
- If `--simulation-horizon` is omitted, simulation uses `min(hyperperiod, max_hyperperiod)`.
- Use `--runs 0` to disable simulation.

## Sanity checks for results

- If EDF appears much worse than DM on this single-core preemptive constrained-deadline model, treat it as an implementation bug and inspect EDF schedule construction.
- If analytical schedulability is true but simulation reports misses, verify deadline comparison (`finish_time > absolute_deadline`), execution-time sampling bounds, and bounded-horizon handling for unfinished jobs.
- `target_utilization` is parsed from folder components such as `0.60-util`.
- CSV numeric fields may appear as float strings (for example `10000.0`) while still representing integer task parameters.

## Troubleshooting consistency issues

- If EDF is worse than DM, inspect EDF analytical scheduling with `python -m drts_analyzer debug-taskset --input path/to/taskset.csv --trace-edf`.
- If simulation misses deadlines while analytical analysis says schedulable, check execution-time sampling bounds, deadline comparison (`finish_time > absolute_deadline`), and horizon handling.
- Analytical EDF must continue after hyperperiod `H` until all jobs released before `H` complete.
- Deadline misses are only decided at job completion with `finish_time > absolute_deadline` (not `>=`).
