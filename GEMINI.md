# Workspace Rules for AgentEcom

## Python Environment & Virtual Environments
- **Primary Virtual Environment**: Always use the existing virtual environment located at `.venv` (`D:\projects\AgentEcom\.venv`).
  - Python Executable: `.\.venv\Scripts\python.exe`
  - Pytest Executable: `.\.venv\Scripts\pytest`
  - PowerShell Activation: `.\.venv\Scripts\Activate.ps1`
- **Strict Rule**: **NEVER** run `python -m venv` or create any new virtual environment. All project dependencies (`fastapi`, `langchain`, `langgraph`, `pytest`, `aiosqlite`, etc.) are already installed in `.venv`.
- When running commands via terminal or subagents, always invoke Python tools via `.\.venv\Scripts\<tool>` or activate `.venv` first.
