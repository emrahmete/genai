import time, json
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import (
    RequiredFunctionToolCall,
    SubmitToolOutputsAction,
    ToolOutput,
    ListSortOrder
)
from .graph_tools import graph_api_tools, execute_tool_call

def get_agents_client(endpoint: str):
    credential = DefaultAzureCredential()
    return AgentsClient(endpoint=endpoint, credential=credential)

def run_agent(session_id: str, prompt: str, endpoint: str, model: str = "gpt-4.1") -> dict:
    client = get_agents_client(endpoint)
    agent = client.create_agent(
        model=model,
        name="delegated-graph-agent",
        instructions=(
            "You can  call functions to fetch user info from Microsoft Graph. Then you use that info to answer the user's question. Your output should be human-friendly. "
            "Never request the raw token. If a function returns an error, explain it clearly."
        ),
        tools=graph_api_tools,
        description="Agent  using delegated Graph permissions securely."
    )

    thread = client.threads.create()
    client.messages.create(thread_id=thread.id, role="user", content=prompt)
    run = client.runs.create(thread_id=thread.id, agent_id=agent.id)

    while run.status in ["queued", "in_progress", "requires_action"]:
        time.sleep(1)
        run = client.runs.get(thread_id=thread.id, run_id=run.id)
        if run.status == "requires_action" and isinstance(run.required_action, SubmitToolOutputsAction):
            tool_calls = run.required_action.submit_tool_outputs.tool_calls
            outputs = []
            for tc in tool_calls:
                if isinstance(tc, RequiredFunctionToolCall):
                    try:
                        output = execute_tool_call(tc, session_id)
                    except Exception as e:
                        output = json.dumps({"error": str(e)})
                    outputs.append(ToolOutput(tool_call_id=tc.id, output=output))
            if outputs:
                client.runs.submit_tool_outputs(thread_id=thread.id, run_id=run.id, tool_outputs=outputs)

    # Collect messages
    msgs = client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
    assistant_response = ""
    for m in msgs:
        if m.text_messages and m.role == "assistant":
            assistant_response = m.text_messages[-1].text.value
    
    # Return only the assistant's response text
    return {
        "response": assistant_response
    }