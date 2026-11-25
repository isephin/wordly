# Supplementary worker scaling results

These CSV files reconstruct the November 25, 2026 v3.3 calibration experiment from the console log. Durations were printed to six decimal places, so derived means and speedups may differ slightly from the original full-precision CSV files on the test computer. The script completed all 256 measurements and saved its machine-specific profile; it raises an error if any frequency counter differs from the reference. No machine names, addresses, shared tokens or local filesystem paths are included here.

Four synthetic dataset sizes, eight configurations (sequential and 2, 4, 6, 8, 10, 12, 14 parallel processes), eight trials per configuration. Rotating execution order; fresh local process pools; default analysis filters. Original two-worker baseline results remain separate. Hardware: Apple M4 Pro, 14 logical CPUs, 24 GB RAM. Python 3.9.6 as reported for the project environment.

The preliminary loopback network tests are not included as formal distributed benchmark results. Physical multi-computer testing is outside the current research scope.
