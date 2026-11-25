import csv
import platform
import os
import sys
from datetime import datetime
from pathlib import Path
from statistics import mean, median, stdev

from analyzer import (
    sequential_analysis,
    parallel_analysis,
    calculate_metrics,
    get_top_words
)

BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

DATASETS = [
    "small.txt",
    "medium.txt",
    "large.txt",
    "extra_large.txt"
]

TRIALS = 10


def main():
    RESULTS_DIR = BASE_DIR / "results" / "runs" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    RESULTS_DIR.mkdir(parents=True, exist_ok=False)
    raw_results = []
    summary_results = []
    word_results = []

    print("=" * 65)
    print("WORD FREQUENCY ANALYZER - FORMAL BENCHMARK")
    print("=" * 65)

    print(f"Python version : {platform.python_version()}")
    print(f"Operating system: {platform.platform()}")
    print(f"Architecture   : {platform.machine()}")
    print(f"Logical CPUs   : {os.cpu_count()}")
    print("Workers        : 2")
    print(f"Trials         : {TRIALS} per dataset")

    for filename in DATASETS:
        path = BASE_DIR / "datasets" / filename

        with path.open(encoding="utf-8") as file:
            lines = file.readlines()

        responses = len(lines)
        sequential_times = []
        parallel_times = []
        all_identical = True

        print("\n" + "=" * 65)
        print(f"DATASET: {filename}")
        print(f"Responses: {responses:,}")
        print("=" * 65)

        for trial in range(1, TRIALS + 1):

            # Alternate execution order to reduce order bias.
            if trial % 2 == 1:
                seq_counts, seq_time = sequential_analysis(lines)
                par_counts, par_time = parallel_analysis(lines)
                order = "Sequential First"
            else:
                par_counts, par_time = parallel_analysis(lines)
                seq_counts, seq_time = sequential_analysis(lines)
                order = "Parallel First"

            identical = seq_counts == par_counts
            all_identical = all_identical and identical

            speedup, efficiency = calculate_metrics(
                seq_time, par_time
            )

            sequential_times.append(seq_time)
            parallel_times.append(par_time)

            raw_results.append([
                filename,
                responses,
                trial,
                order,
                seq_time,
                par_time,
                speedup,
                efficiency,
                identical
            ])

            print(
                f"Trial {trial:02d} | "
                f"Seq: {seq_time:.6f}s | "
                f"Par: {par_time:.6f}s | "
                f"Speedup: {speedup:.4f}x | "
                f"Match: {identical}"
            )

        seq_mean = mean(sequential_times)
        par_mean = mean(parallel_times)

        speedup, efficiency = calculate_metrics(
            seq_mean, par_mean
        )

        faster = (
            "Parallel" if par_mean < seq_mean
            else "Sequential" if seq_mean < par_mean
            else "Equal"
        )

        summary_results.append([
            filename,
            responses,
            TRIALS,
            seq_mean,
            par_mean,
            median(sequential_times),
            median(parallel_times),
            stdev(sequential_times),
            stdev(parallel_times),
            speedup,
            efficiency,
            all_identical,
            faster
        ])

        for rank, (word, count) in enumerate(
            get_top_words(seq_counts), start=1
        ):
            word_results.append([
                filename, responses, rank, word, count
            ])

        print("\nSUMMARY")
        print(f"Mean sequential time: {seq_mean:.6f}s")
        print(f"Mean parallel time  : {par_mean:.6f}s")
        print(f"Speedup             : {speedup:.4f}x")
        print(f"Efficiency          : {efficiency:.2f}%")
        print(f"Identical results   : {all_identical}")
        print(f"Faster method       : {faster}")

    files = [
        (
            "benchmark_raw.csv",
            [
                "Dataset", "Responses", "Trial",
                "Execution Order",
                "Sequential Time (s)",
                "Parallel Time (s)",
                "Speedup", "Efficiency (%)",
                "Identical Results"
            ],
            raw_results
        ),
        (
            "benchmark_summary.csv",
            [
                "Dataset", "Responses", "Trials",
                "Mean Sequential (s)",
                "Mean Parallel (s)",
                "Median Sequential (s)",
                "Median Parallel (s)",
                "SD Sequential (s)",
                "SD Parallel (s)",
                "Speedup", "Efficiency (%)",
                "Identical Results", "Faster Method"
            ],
            summary_results
        ),
        (
            "benchmark_word_counts.csv",
            ["Dataset", "Responses", "Rank",
             "Word", "Frequency"],
            word_results
        )
    ]

    for filename, headers, rows in files:
        with (RESULTS_DIR / filename).open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            writer.writerows(rows)

    with (RESULTS_DIR / "system_info.txt").open(
        "w", encoding="utf-8"
    ) as file:
        file.write(
            f"Python: {sys.version}\n"
            f"OS: {platform.platform()}\n"
            f"Architecture: {platform.machine()}\n"
            f"Logical CPUs: {os.cpu_count()}\n"
            f"Parallel workers: 2\n"
            f"Trials per dataset: {TRIALS}\n"
        )

    print("\nBenchmark completed.")
    print(f"Results saved in: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
