# Dan Computer Use MCP — One-Line Install

## Install (Right Now)

```bash
cd /Users/sodan/Desktop/x/dan-computer-use-mcp
pipx install .
```

## Configure

Add to your MCP client's config file:

```json
{
  "mcpServers": {
    "dan-computer-use-mcp": {
      "command": "dan-computer-use-mcp"
    }
  }
}
```

### Config Locations

- **Claude Desktop:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Cursor:** `~/.cursor/mcp.json`
- **Qwen Code:** `~/.qwen/settings.json`
- **VS Code:** `.vscode/mcp.json`

## Use

```
"Get my screen state"
"Click the Submit button"
"Open Chrome and go to google.com"
```

---

**That's it!** Two commands, one config snippet.

For details: [INSTALL.md](INSTALL.md)

*Dan Computer Use MCP — Works everywhere*
