from core.routing.llm_factory import get_llm

def exact_match_evaluator(run, example) -> dict:
    prediction = run.outputs.get("output", "")
    reference = example.outputs.get("expected", "")

    if reference.lower() in prediction.lower():
        return {"key": "rule_adherence", "score": 1.0}

    # Connect directly to your local Ollama instance
    judge_llm = get_llm("JUDGE_LLM_MODEL", "llama3.1", temperature=0)

    prompt = prompt = f"""
You are an impartial evaluator for a Google Calendar assistant.

Your job is ONLY to evaluate whether the assistant's final response satisfies the expected outcome.

Expected Outcome:
{reference}

Assistant Response:
{prediction}

Evaluation Rules:

1. Compare the RESPONSE to the EXPECTED OUTCOME.
2. Ignore differences in wording, grammar, punctuation and capitalization.
3. Accept paraphrases if they communicate the same meaning.
4. Do NOT reward extra politeness or conversational filler.
5. Penalize missing information, incorrect information, or contradictory information.
6. If the response claims an action different from the expected outcome, score very low.
7. If the expected outcome says the assistant should refuse or ask for clarification, then confirming an action is incorrect.
8. If the assistant invents facts not present in the expected outcome, deduct points.
9. Focus ONLY on whether the user's intent was correctly fulfilled.

Scoring Rubric:

100
- Meaning is identical to the expected outcome.
- No important information is missing.
- No incorrect information.

90
- Same meaning with only insignificant wording differences.

75
- Mostly correct but missing one important detail.

50
- Partially correct.
- Some important information is incorrect or missing.

25
- Mostly incorrect.
- Wrong action or misleading response.

0
- Completely incorrect.
- Hallucinated.
- Contradicts the expected outcome.

Output Requirements:

Return ONLY one integer.
Do NOT explain.
Do NOT output markdown.
Do NOT output any text besides the number.

Score:
"""

    try:
        judge_response = judge_llm.invoke(prompt).content.strip()
        # Clean out any accidental text characters to extract only the digits
        numeric_score = int(''.join(filter(str.isdigit, judge_response)))
        scaled_score = numeric_score / 100.0
    except Exception as e:
        print(f"Ollama Judge Parsing Error: {e}")
        scaled_score = 0.0

    return {"key": "rule_adherence", "score": scaled_score}
