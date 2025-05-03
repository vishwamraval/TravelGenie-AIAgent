# batch_evals.py

import os
import json
import matplotlib.pyplot as plt
from collections import Counter
from time import sleep
from agent import run_agent, helpfulness_eval


# Load questions from the benchmark file
def load_questions(filename):
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
        return [item["question"].strip() for item in data if item["question"].strip()]


# Load questions from the benchmark file and run the agent on each question
def run_benchmark(
    input_file="evaluation_benchmark.json", output_file="evaluation_results.json"
):
    questions = load_questions(input_file)
    print(f"Loaded {len(questions)} questions from benchmark.")

    results = []
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            results = json.load(f)

    for idx, question in enumerate(questions):
        print(f"\n[{idx + 1}/{len(questions)}] Evaluating: {question}")
        try:
            thread_id = f"thread_{idx + 1}"
            query, agent_reply, messages = run_agent(question, thread_id=thread_id)
            eval_result = helpfulness_eval(
                inputs={"question": query}, outputs={"answer": agent_reply}
            )
            result = {
                "Question": query,
                "Answer": agent_reply,
                "Helpfulness (Yes/No)": "Yes" if eval_result.get("score") else "No",
                "Comment": eval_result.get("comment", ""),
            }
            results.append(result)
            print("Saved result.")

            # Save JSON after every run
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=4)

        except Exception as e:
            print(f"Error processing question: {e}")

        sleep(10)


# Count the number of helpfulness votes in the JSON file
def count_helpfulness_votes(json_file):
    counts = Counter()

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        for item in data:
            vote = item.get("Helpfulness (Yes/No)", "")
            if vote is not None:
                vote = vote.strip()
            if vote in ["Yes", "No"]:
                counts[vote] += 1

    return counts


def plot_counts(counts, output_file="helpfulness_plot.png"):
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
    plt.savefig(output_file)
    plt.show()
    print(f"💾 Plot saved to: {output_file}")


def print_unhelpful_responses_from_json(json_file):
    with open(json_file, encoding="utf-8") as f:
        data = json.load(f)

    print("\nUnhelpful Responses (JSON):\n")
    found = False

    for entry in data:
        vote = entry.get("Helpfulness (Yes/No)")
        if vote and vote.strip().lower() == "no":
            found = True
            question = entry.get("Question", "").strip()
            answer = entry.get("Answer", "").strip()
            comment = entry.get("Comment", "").strip()

            print(f"Q: {question}")
            print(f"A: {answer}")
            print(f"Comment: {comment}\n" + "-" * 60)

    if not found:
        print("No unhelpful responses found in JSON file!")


def save_unhelpful_responses(json_file, output_file="unhelpful_results.json"):
    with open(json_file, "r", encoding="utf-8") as f_in:
        data = json.load(f_in)

    unhelpful = []
    for item in data:
        vote = item.get("Helpfulness (Yes/No)")
        if isinstance(vote, str) and vote.strip() == "No":
            unhelpful.append(item)

    with open(output_file, "w", encoding="utf-8") as f_out:
        json.dump(unhelpful, f_out, indent=4)

    if unhelpful:
        print(f"\nSaved all 'No' responses to: {output_file}")
    else:
        print("No unhelpful responses to save.")


if __name__ == "__main__":
    input_file = "evaluation_benchmark.json"
    output_file = "evaluation_results.json"

    run_benchmark(input_file, output_file)

    if not os.path.isfile(output_file):
        print(f"Output file not found: {output_file}")
        exit(1)

    counts = count_helpfulness_votes(output_file)
    print("\nHelpfulness counts:", counts)

    print_unhelpful_responses_from_json(output_file)
    save_unhelpful_responses(output_file)
    plot_counts(counts)
