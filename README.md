# Dan Computer Use MCP

**Cross-platform computer control via MCP.**

Works with: **Claude Desktop** ✅ | **Cursor** ✅ | **Qwen Code** ✅ | **VS Code** ✅ | **Any MCP Client** ✅

---

## One-Line Install

### From Local Directory (Right Now)

```bash
cd /Users/sodan/Desktop/x/dan-computer-use-mcp
pipx install .
```

### From PyPI (Once Published)

```bash
pipx install dan-computer-use-mcp
```

**That's it!** Then add the config to your MCP client.

---

## Quick Config (Copy-Paste)

Add this to your MCP client's config file:

```json
{
  "mcpServers": {
    "dan-computer-use-mcp": {
      "command": "dan-computer-use-mcp"
    }
  }
}
```

### Config File Locations

| Client | Config Path |
|--------|-------------|
| **Claude Desktop (Mac)** | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Claude Desktop (Windows)** | `%APPDATA%\Claude\claude_desktop_config.json` |
| **Cursor** | `~/.cursor/mcp.json` |
| **Qwen Code** | `~/.qwen/settings.json` |
| **VS Code** | `.vscode/mcp.json` |

---

## Full Setup (See INSTALL.md)

For detailed instructions, see [INSTALL.md](INSTALL.md).

### Quick Summary:

1. **Install:** `pipx install dan-computer-use-mcp`
2. **Add config:** Copy-paste JSON to your client's config file
3. **Restart:** Restart your MCP client
4. **Use:** "Get my screen state"

---

## Tools (24 Total)

### State (1)
| Tool | Description |
|------|-------------|
| `get_state` | Screenshot + OCR elements + active window |

### Mouse (4)
| Tool | Description |
|------|-------------|
| `click` | Click at coordinates |
| `move_mouse` | Move mouse |
| `drag` | Drag |
| `scroll` | Scroll |

### Keyboard (3)
| Tool | Description |
|------|-------------|
| `type_text` | Type text |
| `press_key` | Press key |
| `hotkey` | Keyboard shortcut |

### Window (5)
| Tool | Description |
|------|-------------|
| `open_app` | Open app |
| `switch_window` | Switch window |
| `list_windows` | List windows |
| `close_window` | Close window |
| `get_active_window` | Get active window |

### Browser (6)
| Tool | Description |
|------|-------------|
| `browser_navigate` | Navigate to URL |
| `browser_get_text` | Get page text |
| `browser_click` | Click element |
| `browser_fill` | Fill form |
| `browser_scrape` | Scrape page |
| `browser_screenshot` | Screenshot |

### Shell (4)
| Tool | Description |
|------|-------------|
| `run_command` | Run command |
| `read_file` | Read file |
| `write_file` | Write file |
| `list_dir` | List directory |

### Escalation (1)
| Tool | Description |
|------|-------------|
| `escalate` | Hand off to MetaClaw |

---

## Usage

```
# Basic
"Get my screen state"
"Click the Submit button"
"Type 'hello world'"
"Open Chrome"
"Navigate to google.com"

# Complex
"Open Chrome, go to github.com, get the text"
"Get screen state, find terminal, run git status"
```

---

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Platform Support

| Platform | Status |
|----------|--------|
| **macOS** | ✅ Tested |
| **Linux** | ✅ Tested |
| **Windows** | 🚧 Untested |

---

## Requirements

- Python 3.11+
- MCP-compatible client
- Tesseract OCR (optional, for element detection)
- Playwright Chromium (`playwright install chromium`)

### Linux-Specific Requirements

For Linux, install window management tools:
```bash
# Ubuntu/Debian
sudo apt install xdotool wmctrl

# Fedora/RHEL
sudo dnf install xdotool wmctrl
```

---

## Security

**Blocked commands:** `rm -rf /`, `mkfs`, `dd if=/dev`, `:(){:|:&};:`, `chmod 777 /`

**Session logging:** Last 20 actions retained

---

## Development

```bash
# Run tests
pytest tests/ -v

# Lint
ruff check src/dan_computer_use_mcp/
```

---

## License

MIT License

---

*Dan Computer Use MCP — Minimal, robust, cross-platform*
