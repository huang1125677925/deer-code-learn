
import asyncio
import json
import os
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional, Type

from langchain_core.tools import StructuredTool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel, Field, create_model

class MCPManager:
    def __init__(self, config_path: str = "mcp_server_config.json"):
        self.config_path = config_path
        self.sessions: Dict[str, ClientSession] = {}
        self._exit_stack = AsyncExitStack()
        self.tools: List[StructuredTool] = []

    async def load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            return {}
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading MCP config: {e}")
            return {}

    async def connect(self):
        config = await self.load_config()
        servers = config.get("mcpServers", {})

        for server_name, server_config in servers.items():
            command = server_config.get("command")
            args = server_config.get("args", [])
            env = server_config.get("env", {})
            
            # Merge with current environment
            current_env = os.environ.copy()
            current_env.update(env)

            params = StdioServerParameters(
                command=command,
                args=args,
                env=current_env
            )

            try:
                # Use exit stack to manage context
                transport = await self._exit_stack.enter_async_context(stdio_client(params))
                read, write = transport
                session = await self._exit_stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                
                self.sessions[server_name] = session
                print(f"Connected to MCP server: {server_name}")
                
                # Load tools from this session
                await self._load_tools_from_session(server_name, session)
                
            except Exception as e:
                print(f"Failed to connect to MCP server {server_name}: {e}")

    def _json_schema_to_pydantic(self, schema: Dict[str, Any], model_name: str) -> Type[BaseModel]:
        fields = {}
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        for field_name, field_schema in properties.items():
            field_type = field_schema.get("type", "string")
            description = field_schema.get("description", "")
            
            python_type = str
            if field_type == "integer":
                python_type = int
            elif field_type == "number":
                python_type = float
            elif field_type == "boolean":
                python_type = bool
            elif field_type == "array":
                python_type = List[Any] # Simplified
            elif field_type == "object":
                python_type = Dict[str, Any] # Simplified
            
            default = ... if field_name in required else None
            fields[field_name] = (python_type, Field(default=default, description=description))

        return create_model(model_name, **fields)

    async def _load_tools_from_session(self, server_name: str, session: ClientSession):
        try:
            result = await session.list_tools()
            for tool in result.tools:
                tool_name = f"{server_name}_{tool.name}"
                
                # Create wrapper function
                async def _create_tool_func(session=session, tool_name=tool.name, **kwargs):
                    return await session.call_tool(tool_name, arguments=kwargs)

                # Convert schema
                args_schema = None
                if tool.inputSchema:
                    try:
                        args_schema = self._json_schema_to_pydantic(tool.inputSchema, f"{tool_name}Input")
                    except Exception as e:
                        print(f"Warning: Failed to convert schema for tool {tool_name}: {e}")

                langchain_tool = StructuredTool.from_function(
                    func=None,
                    coroutine=_create_tool_func,
                    name=tool_name,
                    description=tool.description or "",
                    args_schema=args_schema
                )
                self.tools.append(langchain_tool)
        except Exception as e:
            print(f"Error loading tools from session {server_name}: {e}")

    async def disconnect(self):
        await self._exit_stack.aclose()
        self.sessions.clear()
        self.tools.clear()

    def get_tools(self) -> List[StructuredTool]:
        return self.tools
