import argparse
import sys
from .app import CodeDeerApp
from .tools import set_working_directory


def main() -> None:
    parser = argparse.ArgumentParser(description="Code Deer AI Agent")
    parser.add_argument(
        "cwd", 
        nargs="?", 
        default=".", 
        help="The working directory for the agent (default: current directory)"
    )
    args = parser.parse_args()

    # Set the working directory globally for tools
    set_working_directory(args.cwd)
    
    print(f"Starting Code Deer in {args.cwd}...")
    CodeDeerApp().run()


if __name__ == "__main__":
    main()
