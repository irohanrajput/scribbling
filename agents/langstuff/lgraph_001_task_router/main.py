from dotenv import load_dotenv
load_dotenv()

from graph_builder import graph
from langfuse import Langfuse

langfuse = Langfuse()

app = graph.compile(interrupt_before=[])


def run_router(user_input: str):
    with langfuse.start_as_current_span(
        name="task-router",
        input=user_input
    ) as span:
        result = app.invoke({
            "user_input": user_input,
            "task_type": "",
            "result": ""
        })
        span.update(output=result["result"])
        return result


output = run_router("Explain Docker vs VM simply")
print(output["result"])
