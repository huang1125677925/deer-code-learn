import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple, Literal

from langchain_core.tools import tool

# Global working directory variable
# In a more complex app, this might be managed via a ContextVar or dependency injection
_WORKING_DIRECTORY = Path(".").resolve()

def set_working_directory(path: str):
    global _WORKING_DIRECTORY
    _WORKING_DIRECTORY = Path(path).resolve()
    # Also change the process working directory so relative paths work as expected
    try:
        os.chdir(_WORKING_DIRECTORY)
    except Exception as e:
        print(f"Error changing directory to {path}: {e}")

def get_working_directory() -> Path:
    return _WORKING_DIRECTORY

def resolve_path(path: str) -> Path:
    """Resolve path relative to the working directory."""
    # If path is absolute, use it directly (but maybe we should restrict it to be within cwd for safety?)
    # For this tool, we'll allow absolute paths but prioritize relative to cwd.
    p = Path(path)
    if p.is_absolute():
        return p
    return (get_working_directory() / p).resolve()

@tool
def bash(command: str) -> str:
    """Run commands in a bash shell.
    When using this tool, the command is executed in the configured working directory.
    Output will be truncated if it is too long.
    """
    try:
        # Run command with timeout and capture output
        process = subprocess.run(
            command,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,  # 2 minutes timeout
            executable="/bin/bash",
            cwd=get_working_directory() # Run in the working directory
        )
        
        stdout = process.stdout
        stderr = process.stderr
        
        output = ""
        if stdout:
            output += f"{stdout}"
        if stderr:
            output += f"\nError output:\n{stderr}"
            
        if not output and process.returncode == 0:
            return "Command executed successfully with no output."
        
        return output
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 120 seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"


@tool
def text_editor(
    command: Literal["view", "create", "str_replace", "insert"],
    path: str,
    file_text: Optional[str] = None,
    old_str: Optional[str] = None,
    new_str: Optional[str] = None,
    insert_line: Optional[int] = None,
    view_range: Optional[List[int]] = None
) -> str:
    """A text editor tool for viewing, creating, and editing files.
    
    Commands:
    - view: Read file content. Use `view_range` [start_line, end_line] to view specific lines (1-indexed).
    - create: Create a new file with `file_text` content. Overwrites if exists.
    - str_replace: Replace unique `old_str` with `new_str`. `old_str` must be unique in the file.
    - insert: Insert `new_str` after `insert_line`. `insert_line` is 0-indexed (0 to insert at start, n to insert after line n).
    """
    try:
        file_path = resolve_path(path)
        
        if command == "view":
            if not file_path.exists():
                return f"Error: File {path} does not exist."
            
            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines(keepends=True)
            
            if view_range:
                if len(view_range) != 2:
                    return "Error: view_range must have exactly 2 elements [start, end]."
                start, end = view_range
                # Adjust for 1-based indexing
                start = max(1, start)
                end = min(len(lines), end)
                
                if start > len(lines):
                    return "" # Empty if start is beyond EOF
                
                selected_lines = lines[start-1:end]
                return "".join(selected_lines)
            
            return content

        elif command == "create":
            if file_text is None:
                return "Error: file_text is required for create command."
            
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file_text, encoding="utf-8")
            return f"Successfully created file {path}"

        elif command == "str_replace":
            if not file_path.exists():
                return f"Error: File {path} does not exist."
            if old_str is None or new_str is None:
                return "Error: old_str and new_str are required for str_replace command."
            
            content = file_path.read_text(encoding="utf-8")
            
            if old_str not in content:
                return f"Error: The text to replace was not found in {path}."
            
            count = content.count(old_str)
            if count > 1:
                return f"Error: old_str found {count} times. Please provide a unique string to replace."
            
            new_content = content.replace(old_str, new_str)
            file_path.write_text(new_content, encoding="utf-8")
            return f"Successfully replaced text in {path}"

        elif command == "insert":
            if not file_path.exists():
                return f"Error: File {path} does not exist."
            if new_str is None:
                return "Error: new_str is required for insert command."
            if insert_line is None:
                return "Error: insert_line is required for insert command."
            
            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines(keepends=True)
            
            if insert_line < 0 or insert_line > len(lines):
                return f"Error: insert_line {insert_line} is out of range (0-{len(lines)})."
            
            # Ensure new_str ends with newline if it's a line insertion, or handle accordingly
            # Anthropic's insert usually just inserts the string.
            # But let's assume line-based insertion for code.
            
            lines.insert(insert_line, new_str + ("\n" if not new_str.endswith("\n") else ""))
            new_content = "".join(lines)
            file_path.write_text(new_content, encoding="utf-8")
            return f"Successfully inserted text in {path} at line {insert_line}"

        else:
            return f"Error: Unknown command {command}"

    except Exception as e:
        return f"Error executing {command} on {path}: {str(e)}"


# File system tools (Wrappers or independent implementations)

@tool
def ls_files(path: str = ".") -> str:
    """List files and directories in the given path (like ls -F)."""
    try:
        target_path = resolve_path(path)
        if not target_path.exists():
            return f"Error: Path {path} does not exist."
        
        # We can use os.listdir or Path.iterdir
        # Let's behave like ls -F (append / to dirs)
        items = sorted(target_path.iterdir())
        result = []
        for item in items:
            name = item.name
            if item.is_dir():
                name += "/"
            result.append(name)
        return "\n".join(result)
    except Exception as e:
        return f"Error listing directory: {str(e)}"


@tool
def tree_files(path: str = ".", max_depth: int = 2) -> str:
    """List files in a tree-like structure."""
    target_path = resolve_path(path)
    if not target_path.exists():
        return f"Error: Path {path} does not exist."

    def _tree(dir_path: Path, prefix: str = "", current_depth: int = 0):
        if current_depth > max_depth:
            return
        
        try:
            items = sorted(dir_path.iterdir())
        except PermissionError:
            return
        
        entries = []
        for i, item in enumerate(items):
            is_last = (i == len(items) - 1)
            connector = "└── " if is_last else "├── "
            entries.append(f"{prefix}{connector}{item.name}{'/' if item.is_dir() else ''}")
            
            if item.is_dir():
                extension = "    " if is_last else "│   "
                sub_entries = _tree(item, prefix + extension, current_depth + 1)
                if sub_entries:
                    entries.extend(sub_entries)
        return entries

    result = _tree(target_path)
    return "\n".join(result) if result else ""


@tool
def grep_files(pattern: str, path: str = ".", recursive: bool = True) -> str:
    """Search for a pattern in files (like grep)."""
    # Using python's subprocess to call real grep is often better for performance and compatibility
    # But if we want to be pure python... 
    # Let's use real grep if available (since user asked for bash tools), fallback to python?
    # Actually, `bash` tool can do this.
    # But as a standalone tool, let's try to use subprocess grep if on linux/mac.
    
    try:
        target_path = resolve_path(path)
        
        cmd = ["grep", "-n"]
        if recursive:
            cmd.append("-r")
        cmd.extend([pattern, str(target_path)])
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=get_working_directory()
        )
        if result.returncode == 0:
            return result.stdout
        elif result.returncode == 1:
            return "No matches found."
        else:
            return f"Error: {result.stderr}"
    except FileNotFoundError:
        return "Error: 'grep' command not found."


@tool
def update_plan(markdown_content: str) -> str:
    """Update the current plan/todo list.
    The content should be valid Markdown.
    Example:
    - [ ] Task 1
    - [x] Task 2
    """
    return "Plan updated successfully."


def apply_editor_command(current_text: str, command: str) -> Tuple[str, str]:
    parts = command.strip().split(" ", 1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if cmd == "/help":
        return (
            current_text,
            "命令: /set <text> /append <text> /clear /load <path> /save <path>",
        )

    if cmd == "/set":
        return arg, "已设置编辑器内容"
        
    return current_text, f"Unknown command: {cmd}"
