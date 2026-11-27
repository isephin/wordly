from core.analyzer import (
    sequential_analysis,
    parallel_analysis,
    calculate_metrics,
    get_top_words
)


def main():
    with open("datasets/small.txt", encoding="utf-8") as file:
        lines = file.readlines()

    sequential_counts, sequential_time = sequential_analysis(lines)
    parallel_counts, parallel_time = parallel_analysis(lines)

    speedup, efficiency = calculate_metrics(
        sequential_time,
        parallel_time
    )

    print("=" * 48)
    print("     WORD FREQUENCY ANALYZER - PDC TEST")
    print("=" * 48)

    print(f"\nFeedback responses: {len(lines):,}")
    print("Worker processes: 2")

    print("\nTOP 10 MOST FREQUENT WORDS")
    print("-" * 48)

    for rank, (word, count) in enumerate(
        get_top_words(parallel_counts), start=1
    ):
        print(f"{rank:2}. {word:<20} {count:,}")

    print("\nPERFORMANCE COMPARISON")
    print("-" * 48)

    print(f"Sequential time : {sequential_time:.6f} seconds")
    print(f"Parallel time   : {parallel_time:.6f} seconds")
    print(f"Speedup         : {speedup:.4f}x")
    print(f"Efficiency      : {efficiency:.2f}%")

    print("\nCORRECTNESS VERIFICATION")
    print("-" * 48)

    if sequential_counts == parallel_counts:
        print("PASSED: Both methods produce identical results.")
    else:
        print("FAILED: Word frequencies do not match.")

    if sequential_time < parallel_time:
        print("Sequential processing is faster.")
    elif parallel_time < sequential_time:
        print("Parallel processing is faster.")
    else:
        print("Both methods have equal execution times.")


if __name__ == "__main__":
    main()
