from typing import TypedDict

# ---- STATE ----
class State(TypedDict):
    question: str
    answer: str
    critique: str
    score: int
    iteration: int


# ---- NODE 1: GENERATE ----
def generate(state: State):
    question = state["question"]

    answer = f"Initial answer to: {question}"  # replace with LLM later
    print("STATE IN:", state)
    return {
        "answer": answer,
        "iteration": state.get("iteration", 0) + 1
    }


# ---- NODE 2: CRITIQUE ----
def critique(state: State):
    answer = state["answer"]

    # dummy critique logic
    critique = "This answer is too vague."

    # fake score (simulate improvement over time)
    score = min(10, state["iteration"] * 3)
    print("STATE IN:", state)
    return {
        "critique": critique,
        "score": score
    }


# ---- NODE 3: IMPROVE ----
def improve(state: State):
    answer = state["answer"]
    critique = state["critique"]

    improved = f"{answer} | Improved based on critique: {critique}"
    print("STATE IN:", state)
    return {
        "answer": improved,
        "iteration": state["iteration"] + 1

    }


