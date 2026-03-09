@echo off
echo Starting MT5 Monitor V1...
start "MT5 Monitor V1" python mt5_monitor.py

echo Starting MT5 Monitor V2...
start "MT5 Monitor V2" python mt5_monitor_v2.py

echo Starting MT5 Monitor V3 (Discord)...
start "MT5 Monitor V3" python mt5_monitor_v3.py

echo All monitors started.
