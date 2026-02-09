from dotenv import load_dotenv
load_dotenv()

from graph_builder import graph
from langfuse.decorators import observe, langfuse_context

app = graph.compile(interrupt_before=[])


@observe(name="task-router")
def run_router(user_input: str):
    result = app.invoke({
        "user_input": user_input,
        "task_type": "",
        "result": ""
    })
    langfuse_context.update_current_observation(output=result["result"])
    return result


output = run_router("teri maa ka bhosda")
print(output["result"])
