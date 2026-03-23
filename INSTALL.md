# Install Dan Computer Use MCP

## Quick Install

### Option 1: From PyPI (Once Published)

```bash
pipx install dan-computer-use-mcp
```

### Option 2: From Local Directory (Right Now)

```bash
cd /Users/sodan/Desktop/x/dan-computer-use-mcp
pipx install .
```

### Option 3: From GitHub (Once Published)

```bash
pipx install git+https://github.com/danlab/dan-computer-use-mcp.git
```

### Option 4: pip (Local)

```bash
cd /Users/sodan/Desktop/x/dan-computer-use-mcp
pip install -e .
```

---

## Configure Your MCP Client

### Quick Config (Copy-Paste)

**For Claude Desktop:**
```json
{
  "mcpServers": {
    "dan-computer-use-mcp": {
      "command": "dan-computer-use-mcp"
    }
  }
}
```

**For Cursor:**
```json
{
  "mcpServers": {
    "dan-computer-use-mcp": {
      "command": "dan-computer-use-mcp"
    }
  }
}
```

**For Qwen Code:**
```json
{
  "mcpServers": {
    "dan-computer-use-mcp": {
      "command": "python3",
      "args": ["-m", "dan_computer_use_mcp"]
    }
  }
}
```

**For VS Code:**
```json
{
  "mcpServers": {
    "dan-computer-use-mcp": {
      "command": "dan-computer-use-mcp"
    }
  }
}
```

---

## Config File Locations

| Client | Config Path |
|--------|-------------|
| **Claude Desktop (Mac)** | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Claude Desktop (Windows)** | `%APPDATA%\Claude\claude_desktop_config.json` |
| **Cursor** | `~/.cursor/mcp.json` |
| **Qwen Code** | `~/.qwen/settings.json` |
| **VS Code** | `.vscode/mcp.json` (workspace) or `~/.vscode/mcp.json` (global) |

---

## Full Setup (5 Minutes)

### Step 1: Install

```bash
pipx install dan-computer-use-mcp
playwright install chromium
```

### Step 2: (Optional) Install Tesseract for OCR

```bash
# macOS
brew install tesseract

# Linux (Ubuntu/Debian)
sudo apt install tesseract-ocr

# Linux (Fedora/RHEL)
sudo dnf install tesseract

# Windows (with Chocolatey)
choco install tesseract
```

### Step 3: Install Linux Window Tools (Linux Only)

For Linux, install these tools for window management:

```bash
# Ubuntu/Debian
sudo apt install xdotool wmctrl

# Fedora/RHEL
sudo dnf install xdotool wmctrl

# Arch Linux
sudo pacman -S xdotool wmctrl
```

These enable:
- `list_windows` - List all open windows
- `switch_window` - Switch to a specific window
- `get_active_window` - Get the current active window title

### Step 3: Add to Your MCP Client

1. Open your MCP client's config file (see paths above)
2. Copy-paste the config snippet for your client
3. Save the file
4. Restart your MCP client

### Step 4: Verify

Ask your AI agent:
```
"What MCP servers are connected?"
```

You should see `dan-computer-use-mcp` listed.

---

## Quick Test

Once connected, try:
```
"Get my screen state"
```

This should return a screenshot and list of visible elements.

---

## Need Help?

- **Docs:** https://github.com/danlab/dan-computer-use-mcp
- **Issues:** https://github.com/danlab/dan-computer-use-mcp/issues
- **Discord:** [Coming Soon]

---

*Dan Computer Use MCP — One-line install, works everywhere*
