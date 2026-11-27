import csv
from pathlib import Path
from datetime import datetime

from core.analyzer import (
    sequential_analysis,
    parallel_analysis,
    calculate_metrics,
    get_top_words
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "datasets"
RESULTS_DIR = BASE_DIR / "results"

RESULTS_DIR.mkdir(exist_ok=True)

DATASETS = {
    "1": ("Small", "small.txt"),
    "2": ("Medium", "medium.txt"),
    "3": ("Large", "large.txt"),
    "4": ("Extra Large", "extra_large.txt")
}


def print_header(title):
    print("\n" + "=" * 58)
    print(title.center(58))
    print("=" * 58)


def save_results(path, responses, seq_time, par_time,
                 speedup, efficiency, identical, frequencies):

    output = RESULTS_DIR / "analysis_results.csv"
    new_file = not output.exists() or output.stat().st_size == 0

    with output.open("a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        if new_file:
            writer.writerow([
                "Timestamp",
                "Dataset",
                "Responses",
                "Sequential Time (s)",
                "Parallel Time (s)",
                "Speedup",
                "Efficiency (%)",
                "Identical Results"
            ])

        writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            path.name,
            responses,
            f"{seq_time:.9f}",
            f"{par_time:.9f}",
            f"{speedup:.6f}",
            f"{efficiency:.4f}",
            identical
        ])

    word_output = RESULTS_DIR / f"{path.stem}_word_counts.csv"

    with word_output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Rank", "Word", "Frequency"])

        for rank, (word, count) in enumerate(
            get_top_words(frequencies), start=1
        ):
            writer.writerow([rank, word, count])

    print("\nResults saved successfully:")
    print(f"  {output}")
    print(f"  {word_output}")


def analyze_file(path):
    if not path.is_file():
        print("\nError: File not found.")
        return

    try:
        with path.open("r", encoding="utf-8") as file:
            lines = file.readlines()
    except (OSError, UnicodeError) as error:
        print(f"\nUnable to read file: {error}")
        return

    if not lines or not any(line.strip() for line in lines):
        print("\nError: The selected file is empty.")
        return

    print_header("DATASET INFORMATION")

    print(f"Dataset          : {path.name}")
    print(f"Feedback lines   : {len(lines):,}")
    print(f"File size        : {path.stat().st_size / 1024:,.2f} KB")
    print("Parallel workers : 2")

    print("\nRunning sequential analysis...")
    seq_counts, seq_time = sequential_analysis(lines)

    print("Running parallel analysis...")
    par_counts, par_time = parallel_analysis(lines)

    speedup, efficiency = calculate_metrics(
        seq_time, par_time
    )

    identical = seq_counts == par_counts

    print_header("TOP 10 MOST FREQUENT WORDS")

    top_words = get_top_words(seq_counts)

    print(f"{'Rank':<6}{'Word':<22}{'Frequency':>12}")
    print("-" * 58)

    maximum = top_words[0][1] if top_words else 1

    for rank, (word, count) in enumerate(top_words, start=1):
        bar = "#" * max(1, round(count / maximum * 15))
        print(f"{rank:<6}{word:<22}{count:>12,}  {bar}")

    print(f"\nTotal filtered words : {sum(seq_counts.values()):,}")
    print(f"Unique words         : {len(seq_counts):,}")

    print_header("PERFORMANCE COMPARISON")

    print(f"Sequential time : {seq_time:.6f} seconds")
    print(f"Parallel time   : {par_time:.6f} seconds")
    print(f"Speedup         : {speedup:.4f}x")
    print(f"Efficiency      : {efficiency:.2f}%")

    if speedup > 1:
        print("\nResult: Parallel processing is faster.")
    elif speedup < 1:
        print("\nResult: Sequential processing is faster.")
    else:
        print("\nResult: Both methods are equally fast.")

    print_header("CORRECTNESS VERIFICATION")

    if identical:
        print("PASSED: Both methods produce identical word counts.")
    else:
        print("FAILED: Word frequencies do not match.")

    choice = input("\nSave results to CSV? [Y/N]: ").strip().lower()

    if choice == "y":
        save_results(
            path,
            len(lines),
            seq_time,
            par_time,
            speedup,
            efficiency,
            identical,
            seq_counts
        )


def main():
    while True:
        print_header("WORD FREQUENCY ANALYZER")
        print("Parallel and Distributed Computing".center(58))

        print("\nSELECT DATASET\n")
        print("[1] Small          - 1,000 responses")
        print("[2] Medium         - 10,000 responses")
        print("[3] Large          - 100,000 responses")
        print("[4] Extra Large    - 1,000,000 responses")
        print("[5] Custom text file")
        print("[0] Exit")

        choice = input("\nEnter your choice: ").strip()

        if choice == "0":
            print("\nThank you for using Word Frequency Analyzer.")
            break

        elif choice in DATASETS:
            _, filename = DATASETS[choice]
            analyze_file(DATASET_DIR / filename)

        elif choice == "5":
            custom_path = input("Enter text file path: ").strip()
            custom_path = custom_path.strip("\"'")
            path = Path(custom_path).expanduser()

            if path.suffix.lower() != ".txt":
                print("\nError: Please select a .txt file.")
                continue

            analyze_file(path)

        else:
            print("\nInvalid choice. Please try again.")
            continue

        input("\nPress Enter to return to the main menu...")


if __name__ == "__main__":
    main()
