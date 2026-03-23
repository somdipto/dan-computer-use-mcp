"""
Tests for Dan Computer Use MCP.

Run: pytest tests/ -v
"""

import asyncio
import json
import pytest


class TestBasicTools:
    """Test basic tools."""

    @pytest.mark.asyncio
    async def test_type_text(self):
        from dan_computer_use_mcp.server import handle_type_text
        result = await handle_type_text("type_text", {"text": "test", "interval": 0.01})
        data = json.loads(result)
        assert data.get("ok") is True

    @pytest.mark.asyncio
    async def test_press_key(self):
        from dan_computer_use_mcp.server import handle_press_key
        result = await handle_press_key("press_key", {"key": "enter"})
        data = json.loads(result)
        assert data.get("ok") is True

    @pytest.mark.asyncio
    async def test_hotkey(self):
        from dan_computer_use_mcp.server import handle_hotkey
        result = await handle_hotkey("hotkey", {"keys": ["ctrl", "c"]})
        data = json.loads(result)
        assert data.get("ok") is True

    @pytest.mark.asyncio
    async def test_move_mouse(self):
        from dan_computer_use_mcp.server import handle_move_mouse
        result = await handle_move_mouse("move_mouse", {"x": 100, "y": 200, "duration": 0.1})
        data = json.loads(result)
        assert data.get("ok") is True

    @pytest.mark.asyncio
    async def test_click(self):
        from dan_computer_use_mcp.server import handle_click
        result = await handle_click("click", {"x": 150, "y": 250, "button": "left"})
        data = json.loads(result)
        assert data.get("ok") is True


class TestShellTools:
    """Test shell tools."""

    @pytest.mark.asyncio
    async def test_run_command(self):
        from dan_computer_use_mcp.server import handle_run_command
        result = await handle_run_command("run_command", {"command": "echo hello", "timeout": 5})
        data = json.loads(result)
        assert data.get("ok") is True
        assert "hello" in data.get("stdout", "")

    @pytest.mark.asyncio
    async def test_run_command_blocked(self):
        from dan_computer_use_mcp.server import handle_run_command
        result = await handle_run_command("run_command", {"command": "rm -rf /", "timeout": 5})
        data = json.loads(result)
        assert data.get("ok") is False
        assert "Blocked" in data.get("error", "")

    @pytest.mark.asyncio
    async def test_list_dir(self):
        from dan_computer_use_mcp.server import handle_list_dir
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "test1.txt"), "w").close()
            open(os.path.join(tmpdir, "test2.txt"), "w").close()
            result = await handle_list_dir("list_dir", {"path": tmpdir})
            data = json.loads(result)
            assert "entries" in data
            assert data.get("count", 0) >= 2


class TestServer:
    """Test server configuration."""

    def test_tool_count(self):
        from dan_computer_use_mcp.server import ALL_TOOLS
        assert len(ALL_TOOLS) == 30

    def test_all_tools_have_handlers(self):
        from dan_computer_use_mcp.server import ALL_TOOLS, HANDLERS
        for tool in ALL_TOOLS:
            assert tool.name in HANDLERS
            assert HANDLERS[tool.name] is not None

    def test_tool_names_unique(self):
        from dan_computer_use_mcp.server import ALL_TOOLS
        names = [tool.name for tool in ALL_TOOLS]
        assert len(names) == len(set(names))
