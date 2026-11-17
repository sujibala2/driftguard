# DriftGuard

Detects compromised npm package releases by comparing each release
against the package's own historical publishing behavior.

## Modules
- collector.py: collects release metadata from the npm registry into SQLite
- baseline.py: first single-signal drift check
- scoring.py: multi-signal weighted scoring with Tier 1/2/3 output
- test_scenarios.py: validation with simulated releases

## Run
pip install -r requirements.txt
python collector.py
python scoring.py
python test_scenarios.py

## Status
About 40% complete. Next: GitHub API signals, real-incident backtest, weight tuning.
