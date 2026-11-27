import random
from pathlib import Path

random.seed(42)

DATASET_DIR = Path(__file__).resolve().parent.parent / "datasets"
DATASET_DIR.mkdir(exist_ok=True)

positive = [
    "The speaker explained the topic clearly.",
    "The seminar was informative and engaging.",
    "The registration process was smooth and organized.",
    "The venue was comfortable and spacious.",
    "The organizers were approachable and helpful.",
    "The activities encouraged student participation.",
    "The workshop provided useful practical knowledge.",
    "The presentation materials were easy to understand.",
    "The event was well organized.",
    "The speakers shared relevant experiences.",
    "The discussion was interesting and educational.",
    "The event schedule was followed properly.",
    "The technical team handled the equipment well.",
    "The workshop helped me develop new skills.",
    "The question and answer session was helpful."
]

negative = [
    "The registration process took too long.",
    "The venue was too crowded.",
    "The microphone was difficult to hear.",
    "The seminar started later than expected.",
    "The presentation was difficult to follow.",
    "The internet connection was unstable.",
    "The room temperature was uncomfortable.",
    "The speakers had limited time for discussion.",
    "The instructions were unclear.",
    "The activities felt rushed.",
    "The seating arrangement was inconvenient.",
    "The event schedule was confusing.",
    "The sound system needs improvement.",
    "The workshop lacked practical examples.",
    "The waiting time was too long."
]

suggestions = [
    "Please provide more interactive activities.",
    "The organizers should improve the registration system.",
    "A larger venue would be better.",
    "More time should be given for questions.",
    "Please invite more industry professionals.",
    "The event should include more practical demonstrations.",
    "Provide clearer instructions before the seminar.",
    "Improve the sound system for future events.",
    "Please distribute the presentation materials.",
    "The organizers should announce the schedule earlier.",
    "Include more activities for student participation.",
    "Provide longer breaks between sessions.",
    "Improve communication with the participants.",
    "More workshops should be conducted in the future.",
    "Please consider providing additional seating."
]

def generate_feedback():
    category = random.choices(
        ["positive", "negative", "suggestion", "mixed"],
        weights=[40, 20, 20, 20],
        k=1
    )[0]

    if category == "positive":
        return random.choice(positive)
    elif category == "negative":
        return random.choice(negative)
    elif category == "suggestion":
        return random.choice(suggestions)
    else:
        return (
            random.choice(positive) + " " +
            random.choice(suggestions)
        )

def main():
    sizes = {
        "small": 1_000,
        "medium": 10_000,
        "large": 100_000,
        "extra_large": 1_000_000
    }

    print("Generating synthetic campus event feedback...\n")

    for name, size in sizes.items():
        path = DATASET_DIR / f"{name}.txt"

        with path.open("w", encoding="utf-8") as file:
            for _ in range(size):
                file.write(generate_feedback() + "\n")

        print(f"{path.name}: {size:,} responses")

    print("\nDataset generation completed.")

if __name__ == "__main__":
    main()
