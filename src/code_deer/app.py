from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Input, Markdown, TabbedContent, TabPane, TextArea

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.messages.ai import AIMessageChunk

from .graph import build_graph
from .mcp_manager import MCPManager


class CodeDeerApp(App):
    BINDINGS = [("ctrl+c", "quit", "Quit")]
    CSS = """
    #main {
        height: 1fr;
    }
    #chat-container {
        height: 100%;
        width: 1fr;
        border: solid blue;
        padding: 1;
        overflow-y: scroll;
    }
    #right-panel {
        height: 100%;
        width: 1fr;
    }
    #editor {
        height: 70%;
        border: solid green;
    }
    #plan-view {
        height: 30%;
        border: solid yellow;
        padding: 1;
        overflow-y: scroll;
    }
    #bottom-tabs {
        height: 30%;
        border: solid yellow;
    }
    #plan-view-content {
        height: 100%;
        padding: 1;
        overflow-y: scroll;
    }
    #terminal-view {
        height: 100%;
        padding: 1;
        overflow-y: scroll;
    }
    .user-message {
        background: $primary;
        color: $text;
        padding: 1;
        margin: 1 0;
        text-align: right;
    }
    .ai-message {
        background: $surface;
        color: $text;
        padding: 1;
        margin: 1 0;
    }
    .tool-message {
        background: $error-darken-3;
        color: $text-muted;
        padding: 0 1;
        margin: 0 0;
        text-style: italic;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.mcp_manager = MCPManager()
        self.graph = None
        self.state = {"messages": [], "editor_text": "", "plan": ""}
        self.current_markdown = None
        self.terminal_content = ""

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            with Horizontal(id="main"):
                yield VerticalScroll(id="chat-container")
                with Vertical(id="right-panel"):
                    yield TextArea(id="editor")
                    with TabbedContent(id="bottom-tabs"):
                        with TabPane("Todo"):
                            yield Markdown(id="plan-view-content")
                        with TabPane("Terminal"):
                            yield Markdown(id="terminal-view")
            yield Input(id="input")
        yield Footer()

    async def on_mount(self) -> None:
        await self.mcp_manager.connect()
        mcp_tools = self.mcp_manager.get_tools()
        self.graph = build_graph(extra_tools=mcp_tools)
        self.query_one("#input", Input).focus()

    async def action_quit(self) -> None:
        await self.mcp_manager.disconnect()
        self.exit()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value
        event.input.value = ""

        if not value.strip():
            return

        chat_container = self.query_one("#chat-container", VerticalScroll)
        chat_container.mount(Markdown(f"**You**: {value}", classes="user-message"))
        chat_container.scroll_end(animate=False)

        if self.graph is None:
            chat_container.mount(Markdown("Initializing agent and tools, please wait...", classes="ai-message"))
            chat_container.scroll_end(animate=False)
            return

        self.process_chat(value)

    @work
    async def process_chat(self, value: str) -> None:
        import time

        # Add user message to state
        self.state["messages"].append(HumanMessage(content=value))

        # Stream the graph execution
        current_message_content = ""
        last_update_time = 0
        update_interval = 0.1  # Update UI at most every 100ms
        
        # Start a new AI message block
        self.mount_ai_message_placeholder()

        async for event in self.graph.astream(self.state, stream_mode=["messages", "values"]):
            mode, payload = event
            
            if mode == "messages":
                chunk, _ = payload
                
                if isinstance(chunk, AIMessageChunk):
                    content = chunk.content
                    if content:
                        current_message_content += str(content)
                        current_time = time.time()
                        if current_time - last_update_time > update_interval:
                            self.update_ai_message(current_message_content)
                            last_update_time = current_time
                
                elif isinstance(chunk, ToolMessage):
                    # Ensure any pending content is flushed before tool message
                    if current_message_content:
                        self.update_ai_message(current_message_content)
                    
                    # Show tool output
                    self.mount_tool_message(f"🛠️ {chunk.name}: {chunk.content}")
                    
                    # Update terminal view if it's a bash command
                    if chunk.name == "bash":
                        self.update_terminal_view(f"$ bash\n{chunk.content}\n")
                        
                    # After tool message, we expect a new AI message (if any)
                    # Reset the content buffer and force a new placeholder creation on next AI chunk
                    current_message_content = ""
                    self.reset_current_markdown()
            
            elif mode == "values":
                final_state = payload
                if "editor_text" in final_state:
                     self.update_editor(final_state["editor_text"])
                if "plan" in final_state:
                     self.update_plan_view(final_state["plan"])
                # Also update our local state to keep in sync
                self.state = final_state
        
        # Final flush for any remaining content
        if current_message_content:
            self.update_ai_message(current_message_content)

    def reset_current_markdown(self) -> None:
        self.current_markdown = None

    def mount_ai_message_placeholder(self) -> None:
        chat_container = self.query_one("#chat-container", VerticalScroll)
        self.current_markdown = Markdown("", classes="ai-message")
        chat_container.mount(self.current_markdown)
        chat_container.scroll_end(animate=False)

    def update_ai_message(self, content: str) -> None:
        if self.current_markdown is None:
             self.mount_ai_message_placeholder()
        
        if self.current_markdown:
            self.current_markdown.update(content)

    def mount_tool_message(self, content: str) -> None:
        chat_container = self.query_one("#chat-container", VerticalScroll)
        chat_container.mount(Markdown(content, classes="tool-message"))
        chat_container.scroll_end(animate=False)
        self.current_markdown = None
        
    def update_editor(self, text: str) -> None:
        editor = self.query_one("#editor", TextArea)
        if editor.text != text:
            editor.text = text

    def update_plan_view(self, text: str) -> None:
        plan_view = self.query_one("#plan-view-content", Markdown)
        # Markdown.update only updates content, doesn't re-render fully if syntax changes significantly sometimes
        # But for plan updates it should be fine.
        plan_view.update(text)

    def update_terminal_view(self, text: str) -> None:
        self.terminal_content += text + "\n"
        terminal_view = self.query_one("#terminal-view", Markdown)
        terminal_view.update(f"```bash\n{self.terminal_content}\n```")
