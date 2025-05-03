import json
import os
import matplotlib.pyplot as plt
from collections import Counter


# Count the number of helpful and unhelpful responses
def count_helpfulness_votes(json_file):
    counts = Counter()

    with open(json_file, encoding="utf-8") as f:
        data = json.load(f)
        for entry in data:
            vote = entry.get("Helpfulness (Yes/No)", "").strip()
            if vote in ["Yes", "No"]:
                counts[vote] += 1

    return counts


# Plot the counts of helpful and unhelpful responses
def plot_counts(counts):
    labels = list(counts.keys())
    values = list(counts.values())

    plt.figure(figsize=(6, 4))
    plt.bar(
        labels, values, color=["green" if label == "Yes" else "red" for label in labels]
    )
    plt.title("TravelGenie Helpfulness Evaluation")
    plt.ylabel("Number of Responses")
    plt.xlabel("Helpfulness")
    plt.grid(axis="y", linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.show()


def print_unhelpful_responses(json_file):
    with open(json_file, encoding="utf-8") as f:
        data = json.load(f)
        print("\nUnhelpful ('No') Responses:\n")
        found = False
        for entry in data:
            if entry.get("Helpfulness (Yes/No)", "").strip() == "No":
                found = True
                print(f"Q: {entry['Question'].strip()}")
                print(f"A: {entry['Answer'].strip()}")
                print(f"Comment: {entry['Comment'].strip()}\n" + "-" * 60)
        if not found:
            print("No unhelpful responses found!")


def save_unhelpful_responses(json_file, output_file="unhelpful_results.json"):
    with open(json_file, encoding="utf-8") as f_in:
        data = json.load(f_in)

    unhelpful_responses = [
        entry for entry in data if entry.get("Helpfulness (Yes/No)", "").strip() == "No"
    ]

    if unhelpful_responses:
        with open(output_file, "w", encoding="utf-8") as f_out:
            json.dump(unhelpful_responses, f_out, indent=4, ensure_ascii=False)
        print(f"\nSaved all 'No' responses to: {output_file}")
    else:
        print("No unhelpful responses to save.")


if __name__ == "__main__":
    json_file = "evaluation_results.json"

    if not os.path.isfile(json_file):
        print(f"JSON file not found: {json_file}")
        exit(1)

    counts = count_helpfulness_votes(json_file)
    print("Helpfulness counts:", counts)

    plot_counts(counts)

    # Print and save all no responses
    print_unhelpful_responses(json_file)
    save_unhelpful_responses(json_file)
