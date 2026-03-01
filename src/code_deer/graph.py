import os
import pathlib
from typing import Annotated, List, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from .tools import (
    apply_editor_command,
    bash,
    grep_files,
    ls_files,
    text_editor,
    tree_files,
    update_plan,
)


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    editor_text: str
    plan: str


def build_graph(extra_tools=None):
    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    tools = [text_editor, bash, ls_files, tree_files, grep_files, update_plan]
    if extra_tools:
        tools.extend(extra_tools)

    llm = None
    if api_key:
        llm = ChatOpenAI(
            api_key=api_key, base_url=base_url, model=model_name, temperature=0
        ).bind_tools(tools)

    def run_agent(state: AgentState):
        messages = state["messages"]
        if not messages:
            return {}

        last_message = messages[-1]

        # Handle Slash Commands (Client-side logic)
        if isinstance(last_message, HumanMessage):
            content = str(last_message.content).strip()

            if content.startswith("/"):
                new_text, response = apply_editor_command(
                    state.get("editor_text", ""), content
                )
                return {
                    "editor_text": new_text,
                    "messages": [AIMessage(content=response)],
                }

        if llm is None:
            return {
                "messages": [AIMessage(content="未配置 DEEPSEEK_API_KEY，无法调用模型")]
            }

        try:
            response_message = llm.invoke(messages)
            return {"messages": [response_message]}
        except Exception as e:
            return {
                "messages": [
                    AIMessage(
                        content=f"Error invoking LLM: {str(e)}\n\nPlease check your network connection, API key, and base URL configuration."
                    )
                ]
            }

    def handle_tool_outputs(state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]

        # Handle ToolMessage
        if isinstance(last_message, ToolMessage):
            tool_call_id = last_message.tool_call_id
            tool_name = last_message.name
            
            # Handle plan update
            if tool_name == "update_plan":
                # Find the args
                for msg in reversed(messages[:-1]):
                    if isinstance(msg, AIMessage) and msg.tool_calls:
                        for tc in msg.tool_calls:
                            if tc["id"] == tool_call_id:
                                args = tc["args"]
                                plan_content = args.get("markdown_content")
                                if plan_content:
                                    return {"plan": plan_content}
                        else:
                            continue
                        break

            # If it's a file content viewing tool, update editor directly
            if tool_name == "text_editor":
                # We need to find the args to see what command was run and on what path
                # Search backwards for the AIMessage that called this tool
                for msg in reversed(messages[:-1]):
                    if isinstance(msg, AIMessage) and msg.tool_calls:
                        for tc in msg.tool_calls:
                            if tc["id"] == tool_call_id:
                                args = tc["args"]
                                command = args.get("command")
                                path = args.get("path")
                                
                                if command == "view":
                                    # If viewing full file, update editor. If partial, maybe also update?
                                    # The tool returns the content.
                                    return {"editor_text": last_message.content}
                                
                                if command in ["create", "str_replace", "insert"]:
                                    # File changed, read it back
                                    if path:
                                        try:
                                            # Import resolve_path from tools to handle relative paths correctly
                                            from .tools import resolve_path
                                            content = resolve_path(path).read_text(encoding="utf-8")
                                            return {"editor_text": content}
                                        except Exception as e:
                                            return {"editor_text": f"Error reading file: {e}"}
                                break
                        else:
                            continue
                        break
            
            # For other tools (bash, ls_files, etc.), no need to update editor unless we want to show output there?
            # Probably not, keep editor for file content.

        return {}

    graph = StateGraph(AgentState)
    graph.add_node("agent", run_agent)
    graph.add_node("tools", ToolNode(tools))
    graph.add_node("handle_tool_outputs", handle_tool_outputs)

    graph.set_entry_point("agent")

    graph.add_conditional_edges(
        "agent",
        tools_condition,
    )
    graph.add_edge("tools", "handle_tool_outputs")
    graph.add_edge("handle_tool_outputs", "agent")

    return graph.compile()
