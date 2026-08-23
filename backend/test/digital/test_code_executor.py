from langsmith import Client
from langsmith.evaluation import evaluate
from test.digital.llm_as_judge import exact_match_evaluator
from actions.digital.langchain import code_executor
DATASET_NAME = "code_executor_Edge_Cases"


def ensure_dataset_exists():
    """Programmatically creates the tracking dataset inside your LangSmith web panel."""
    client = Client()
    if client.has_dataset(dataset_name=DATASET_NAME):
        print(f"Removing outdated '{DATASET_NAME}' from LangSmith panel...")
        client.delete_dataset(dataset_name=DATASET_NAME)
    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description="Validation suite for code executor Sub-Agent structural loop execution rules."
    )

    dataset_inputs = [
        # -------------------------
        # Numerical Computation
        # -------------------------
        {
            "request": "What is the square root of 144 multiplied by 5?",
            "expected": "60"
        },
        {
            "request": "Calculate the area of a circle with a radius of 7. Use pi = 3.14159.",
            "expected": "153.94"
        },
        {
            "request": "If an object moves 15 cm and each wheel rotation covers 2.75 cm, how many wheel rotations are required?",
            "expected": "5.4545454545"
        },
        {
            "request": "Calculate 18.75% of 2480.",
            "expected": "465"
        },
        {
            "request": "Convert 12.5 miles to kilometers using 1 mile = 1.60934 km.",
            "expected": "20.11675"
        },

        # -------------------------
        # Dates & Time
        # -------------------------
        {
            "request": "How many days are there between 2026-07-18 and 2026-10-12?",
            "expected": "86"
        },
        {
            "request": "What day of the week was 2024-02-29?",
            "expected": "Thursday"
        },
        {
            "request": "Add 137 days to 2025-09-15.",
            "expected": "2026-01-30"
        },

        # -------------------------
        # Lists & Data Processing
        # -------------------------
        {
            "request": "Take this array [45, 12, 89, 4, 27], sort it, and tell me the second value.",
            "expected": "12"
        },
        {
            "request": "Remove duplicate values from [5,2,5,8,2,1,8,9] and return the sorted list.",
            "expected": "[1, 2, 5, 8, 9]"
        },
        {
            "request": "Find the average of [18, 25, 30, 12, 15].",
            "expected": "20"
        },
        {
            "request": "Count how many times the word 'apple' appears in ['apple','pear','apple','orange','banana','apple'].",
            "expected": "3"
        },

        # -------------------------
        # String Processing
        # -------------------------
        {
            "request": "Count the number of vowels in the string 'Computational Reasoning'.",
            "expected": "10"
        },
        {
            "request": "Reverse the string 'LangChain'.",
            "expected": "niahCgnaL"
        },
        {
            "request": "Extract all numbers from 'Order A12 contains 45 widgets and 8 spare parts.'",
            "expected": "['12', '45', '8']"
        },

        # -------------------------
        # Logic / Verification
        # -------------------------
        {
            "request": "Starting at position (0,0), execute: Up 2, Right 5, Down 1, Left 3. What is the final position?",
            "expected": "(2, 1)"
        },
        {
            "request": "A robot starts with a battery level of 100. It performs actions consuming [15, 22, 18, 9]. What battery level remains?",
            "expected": "36"
        },
        {
            "request": "Verify whether the parentheses in '((a+b)*(c-d))/((e+f))' are balanced.",
            "expected": "True"
        },
        {
            "request": "Given movement commands ['N','N','E','E','S','W'], starting at (0,0), what is the final coordinate?",
            "expected": "(1, 1)"
        },

        # -------------------------
        # Rule Checking
        # -------------------------
        {
            "request": "A password must contain at least 8 characters, one uppercase letter, one lowercase letter, and one digit. Does 'Robot2026' satisfy the rules?",
            "expected": "True"
        },
        {
            "request": "Determine whether [3, 5, 7, 9, 11] is strictly increasing.",
            "expected": "True"
        }
    ]

    for item in dataset_inputs:
        client.create_example(
            inputs={"message": item["request"]},
            outputs={"expected": item["expected"]},
            dataset_id=dataset.id
        )

def evaluation_predictor(inputs: dict) -> dict:
    user_message = inputs["message"]
    executor_output = code_executor(user_message)
    return {"output": executor_output}


if __name__ == "__main__":
    print("Synching dataset targets with LangSmith...")
    ensure_dataset_exists()
    print("Launching targeted trace matrix execution...")
    client = Client()
    all_examples = list(client.list_examples(dataset_name=DATASET_NAME))

    evaluate(
        evaluation_predictor,
        data=all_examples,
        evaluators=[exact_match_evaluator]
    )