# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Dan Computer Use MCP is a cross-platform computer control server that provides AI agents with the ability to control mouse, keyboard, windows, browsers, and execute shell commands. It follows the Model Context Protocol (MCP) specification.

## Commands

```bash
# Install the package in development mode
cd /Users/sodan/Desktop/x/dan-computer-use-mcp
pipx install .

# Run tests
pytest tests/ -v

# Lint code
ruff check src/dan_computer_use_mcp/

# Run MCP server directly
python -m dan_computer_use_mcp
# or
./run-mcp.sh

# Build package
pip install -e .
```

## Architecture

### Server (`src/dan_computer_use_mcp/server.py`)
- Main MCP server implementation using `mcp.server.stdio`
- Exports `ALL_TOOLS` (30 tools) and `HANDLERS` dictionary
- Tool handlers are async functions that receive tool name and parameters
- Returns JSON-encoded results

### Tool Categories
- **State**: `get_state` - Screenshot + OCR elements + active window
- **Mouse**: `click`, `move_mouse`, `drag`, `scroll`
- **Keyboard**: `type_text`, `press_key`, `hotkey`
- **Window**: `open_app`, `switch_window`, `list_windows`, `close_window`, `get_active_window`
- **Browser**: `browser_navigate`, `browser_get_text`, `browser_click`, `browser_fill`, `browser_scrape`, `browser_screenshot`
- **Shell**: `run_command`, `read_file`, `write_file`, `list_dir`
- **Escalation**: `escalate` - Hand off to MetaClaw

### Browser Automation
Uses Playwright Chromium for browser control. Requires `playwright install chromium`.

### Platform Support
- **macOS**: Tested and working (uses pyautogui, pygetwindow)
- **Linux**: Requires `xdotool` and `wmctrl` system packages
- **Windows**: Untested

### Security
- Blocked commands: `rm -rf /`, `mkfs`, `dd if=/dev`, fork bombs, `chmod 777 /`
- Session logging: Last 20 actions retained

## MCP Integration

### Configuration
Add to Claude Desktop's `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "dan-computer-use-mcp": {
      "command": "dan-computer-use-mcp"
    }
  }
}
```

For Claude Code, configure in project settings or use the MCP JSON server format.

### Running the MCP Server
The server runs over stdio. Use `run-mcp.sh` script which wraps the stdio server launch.

## Key Files

- `src/dan_computer_use_mcp/server.py` - Main server with all tool handlers
- `mcp.json` - MCP server manifest
- `server.json` - Server configuration
- `pyproject.toml` - Package configuration
- `run-mcp.sh` - Stdio server launch script
