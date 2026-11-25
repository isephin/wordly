# Optional distributed computing setup (future work)

This procedure is not required for the current project submission. The submitted research evaluates sequential and local parallel computing; only loopback network tests were performed.

Use three computers on a trusted private LAN: one coordinator, two remote workers. Use the same v3.3 worker source and dependencies on all machines. Generate a new shared token (at least 24 characters) privately; never commit it. The worker protocol uses unencrypted HTTP. Do not forward ports or use sensitive text.

## Worker setup

Install Python 3.9 or later and the project dependencies in a virtual environment. On each worker, set `WORDLY_TOKEN` to the shared token in its terminal environment. Then run `python worker.py --host 0.0.0.0 --port 8765`. Allow connections only on the trusted private network. Record each worker's LAN IPv4 address privately.

## Coordinator setup

Set the same `WORDLY_TOKEN` and set `WORDLY_WORKERS` to the two actual HTTP worker addresses, comma-separated (example format: `http://192.168.1.101:8765,http://192.168.1.102:8765`). Start `python app.py` and open `/distributed` on the coordinator. Check both workers are online and have different physical hosts. Test all four generated datasets with two local processes selected and verify exact count agreement.

## Formal experiment

Stop other heavy work on all devices. Use default filters and document hardware, Python version, network type, and date. With the same environment variables and the worker servers still running, run:

```sh
python benchmark_scaling.py --workers 2 --trials 9 --network
```

This tests sequential, local parallel (two processes), and distributed (two network workers), rotating execution order. Each dataset has nine measurements per method. Record mean time and speedup; do not equate distributed speedup per worker with CPU utilization. The local process pool starts for every trial, while network servers are already running; this asymmetry must be disclosed. Compare complete counters, not only top words. Archive the original CSVs privately, then remove network addresses and machine identifiers from public copies. Do not substitute loopback timings for physical distributed benchmarks. Stop the worker services after the experiment.
