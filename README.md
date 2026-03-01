# Code Deer

Code Deer 是一个基于终端的 AI 编程助手，结合了强大的大语言模型（DeepSeek）和 Model Context Protocol (MCP)，旨在提供流畅的命令行编程体验。它通过终端用户界面（TUI）集成了聊天、代码编辑、任务规划和工具执行功能。

## ✨ 功能特性

- **终端用户界面 (TUI)**: 基于 [Textual](https://github.com/Textualize/textual) 构建，无需离开终端即可享受现代化的交互体验。
- **智能对话**: 集成 DeepSeek 大模型，支持上下文理解和多轮对话。
- **MCP 协议支持**: 通过 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 扩展能力，支持连接文件系统、搜索工具（如 Tavily）等外部服务。
- **任务规划**: 内置任务管理面板，帮助你分解和跟踪复杂任务。
- **代码编辑与执行**:
  - 内置简易代码编辑器。
  - 支持文件操作（查看、创建、编辑）。
  - 集成 Bash 终端命令执行。
- **LangGraph 驱动**: 使用 LangGraph 构建智能体工作流，确保任务执行的逻辑性和稳定性。

## 🛠 技术栈

- **编程语言**: Python
- **UI 框架**: [Textual](https://textual.textualize.io/)
- **LLM 框架**: [LangChain](https://www.langchain.com/) & [LangGraph](https://langchain-ai.github.io/langgraph/)
- **模型支持**: DeepSeek (通过 OpenAI 兼容接口)
- **扩展协议**: Model Context Protocol (MCP)

## 🚀 快速开始

### 前置要求

- Python 3.10+
- Node.js & npm (用于安装 MCP 服务器，如 filesystem, tavily)

### 安装

1.  **克隆项目**

    ```bash
    git clone <repository-url>
    cd code-deer
    ```

2.  **创建并激活虚拟环境**

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # macOS/Linux
    # .venv\Scripts\activate   # Windows
    ```

3.  **安装依赖**

    ```bash
    pip install -r requirements.txt
    ```

### 配置

1.  **MCP 服务器配置**
    复制示例配置文件并进行修改：
    ```bash
    cp mcp_server_config.example.json mcp_server_config.json
    ```
    编辑 `mcp_server_config.json`，配置你需要的 MCP 服务器（例如文件系统访问权限或 API 密钥）。

2.  **启动脚本配置**
    复制示例启动脚本：
    ```bash
    cp start.example.sh start.sh
    chmod +x start.sh
    ```
    编辑 `start.sh`，填入你的 DeepSeek API Key 和项目路径：
    ```bash
    export DEEPSEEK_API_KEY="your_api_key_here"
    # 确保 PYTHONPATH 指向 src 目录
    ```

### 运行

执行启动脚本即可运行 Code Deer：

```bash
./start.sh
```

## 📂 项目结构

```
code-deer/
├── src/
│   └── code_deer/
│       ├── app.py          # Textual TUI 应用程序入口
│       ├── graph.py        # LangGraph 智能体逻辑定义
│       ├── main.py         # 程序启动入口
│       ├── mcp_manager.py  # MCP 客户端及工具管理
│       └── tools.py        # 本地工具实现 (Bash, Editor 等)
├── mcp_server_config.json  # MCP 服务器配置文件
├── requirements.txt        # Python 依赖
└── start.sh                # 启动脚本
```
