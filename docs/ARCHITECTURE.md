# Architecture — Dan Computer Use MCP

**Type:** MCP Server  
**Purpose:** Cross-platform computer control

---

## Overview

```
AI Agent (Client)
    │
    │ MCP Protocol (stdio)
    ▼
Dan Computer Use MCP
    │
    ├── 24 Tool Handlers
    ├── Platform Backends (macOS/Linux/Windows)
    └── Session State
    │
    ▼
Operating System
```

---

## Design Principles

1. **Minimal** — 24 essential tools only
2. **Cross-Platform** — macOS, Linux, Windows
3. **Safe** — Dangerous commands blocked
4. **MCP Compliant** — Works with any MCP client

---

## Tools

### State (1)
- `get_state` — Screenshot + OCR + active window

### Mouse (4)
- `click`, `move_mouse`, `drag`, `scroll`

### Keyboard (3)
- `type_text`, `press_key`, `hotkey`

### Window (5)
- `open_app`, `switch_window`, `list_windows`, `close_window`, `get_active_window`

### Browser (6)
- `browser_navigate`, `browser_get_text`, `browser_click`, `browser_fill`, `browser_scrape`, `browser_screenshot`

### Shell (4)
- `run_command`, `read_file`, `write_file`, `list_dir`

### Escalation (1)
- `escalate` — MetaClaw handoff

---

## Implementation

### Single File
All tools and handlers in `server.py` (~700 lines)

### Platform Detection
```python
if platform.system() == "Darwin":  # macOS
elif platform.system() == "Linux":  # Linux
else:  # Windows
```

### Session State
```python
_session = {"actions": [], "active_window": "unknown"}
```

---

## Security

**Blocked:** `rm -rf /`, `mkfs`, `dd if=/dev`, `:(){:|:&};:`, `chmod 777 /`

**Logging:** Last 20 actions retained

---

## Dependencies

- `mcp` — Protocol
- `Pillow` — Images
- `pytesseract` — OCR
- `pyautogui` — Mouse/keyboard
- `playwright` — Browser
- `httpx` — HTTP (escalation)

---

*Dan Computer Use MCP*
