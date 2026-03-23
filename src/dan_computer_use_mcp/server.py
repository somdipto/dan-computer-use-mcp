"""
Dan Computer Use MCP — Cross-platform computer control via MCP protocol.

Works with: Gemini CLI, Claude Code, Qwen Code, Cursor, any MCP-compatible client.

Usage:
    dan-computer-use-mcp    # Start MCP server
    python -m dan_computer_use_mcp  # Alternative
"""

import asyncio
import base64
import io
import json
import platform
import subprocess
from pathlib import Path
from typing import Any, Optional

# Logging setup
import logging
import os
import sys

# Configure logging
_log_level = os.environ.get("DAN_MCP_LOG_LEVEL", "INFO").upper()
_log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
logging.basicConfig(
    level=getattr(logging, _log_level, logging.INFO),
    format=_log_format,
    handlers=[
        logging.StreamHandler(sys.stderr),
    ]
)
logger = logging.getLogger("dan-computer-use-mcp")

# Optional file logging (enable with DAN_MCP_LOG_FILE=/path/to/log)
_log_file = os.environ.get("DAN_MCP_LOG_FILE")
if _log_file:
    file_handler = logging.FileHandler(_log_file)
    file_handler.setFormatter(logging.Formatter(_log_format))
    logger.addHandler(file_handler)


# Configuration system
_config = None


def _load_config() -> dict:
    """Load configuration from file and environment variables.

    Config file locations (in order of precedence):
    1. ./dan-mcp-config.json (current directory)
    2. ~/.dan-computer-use-mcp.json (home directory)
    3. Environment variables (highest priority)

    Config options:
    - browser.headless: bool (default: true)
    - browser.timeout: int (default: 30000ms)
    - ocr.language: str (default: "eng")
    - timeout.command: int (default: 30s)
    - escalate.url: str
    - escalate.default_model: str
    """
    global _config
    if _config is not None:
        return _config

    config = {
        "browser": {
            "headless": True,
            "timeout": 30000,
        },
        "ocr": {
            "language": "eng",
        },
        "timeout": {
            "command": 30,
        },
    }

    # Load from file
    config_paths = [
        Path("./dan-mcp-config.json"),
        Path.home() / ".dan-computer-use-mcp.json",
    ]

    for path in config_paths:
        if path.exists():
            try:
                with open(path) as f:
                    file_config = json.load(f)
                    # Deep merge
                    for key, value in file_config.items():
                        if key in config and isinstance(config[key], dict):
                            config[key].update(value)
                        else:
                            config[key] = value
                logger.info(f"Loaded config from {path}")
                break
            except Exception as e:
                logger.warning(f"Failed to load config from {path}: {e}")

    # Override with environment variables (highest priority)
    if os.environ.get("DAN_MCP_BROWSER_HEADLESS"):
        config["browser"]["headless"] = os.environ.get("DAN_MCP_BROWSER_HEADLESS").lower() == "true"
    if os.environ.get("DAN_MCP_BROWSER_TIMEOUT"):
        config["browser"]["timeout"] = int(os.environ.get("DAN_MCP_BROWSER_TIMEOUT"))
    if os.environ.get("DAN_MCP_OCR_LANGUAGE"):
        config["ocr"]["language"] = os.environ.get("DAN_MCP_OCR_LANGUAGE")
    if os.environ.get("DAN_MCP_TIMEOUT_COMMAND"):
        config["timeout"]["command"] = int(os.environ.get("DAN_MCP_TIMEOUT_COMMAND"))

    _config = config
    logger.info(f"Final config: {config}")
    return config


def get_config() -> dict:
    """Get current configuration."""
    if _config is None:
        _load_config()
    return _config


import pyautogui
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from PIL import Image

# Disable pyautogui failsafe
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05

# Server instance
app = Server("dan-computer-use-mcp")

# Session state
_session = {"actions": [], "active_window": "unknown", "elements": []}

# Browser state
_browser_page = None
_browser_playwright = None
_browser_headless = True  # Default to headless

# OCR availability (cached)
_ocr_available = None
_tesseract_error = None


def _check_ocr_available() -> tuple[bool, str]:
    """Check if OCR (pytesseract + tesseract binary) is available."""
    global _ocr_available, _tesseract_error
    if _ocr_available is not None:
        return _ocr_available, _tesseract_error or ""
    try:
        import pytesseract
        # Try to get version to verify tesseract is actually installed
        pytesseract.get_tesseract_version()
        _ocr_available = True
        _tesseract_error = ""
        return True, ""
    except pytesseract.TesseractNotFoundError:
        _ocr_available = False
        _tesseract_error = "Tesseract binary not found in PATH. Install tesseract: brew install tesseract (macOS), apt install tesseract-ocr (Ubuntu), choco install tesseract (Windows)"
        return False, _tesseract_error
    except ImportError:
        _ocr_available = False
        _tesseract_error = "pytesseract not installed. Run: pip install pytesseract"
        return False, _tesseract_error
    except Exception as e:
        _ocr_available = False
        _tesseract_error = f"OCR error: {str(e)}"
        return False, _tesseract_error


# ============================================================================
# TOOLS (24 total)
# ============================================================================

get_state = Tool(
    name="get_state",
    description="Get screen state: screenshot + OCR elements + active window. ALWAYS call first.",
    inputSchema={"type": "object", "properties": {"region": {"type": "string", "default": "full", "enum": ["full", "active_window"]}}}
)

click = Tool(
    name="click",
    description="Click at coordinates or on text element. Prefer element_text over x,y.",
    inputSchema={"type": "object", "properties": {"x": {"type": "number"}, "y": {"type": "number"}, "element_text": {"type": "string"}, "button": {"type": "string", "default": "left", "enum": ["left", "right", "middle"]}, "clicks": {"type": "integer", "default": 1}}}
)

move_mouse = Tool(
    name="move_mouse",
    description="Move mouse to coordinates.",
    inputSchema={"type": "object", "properties": {"x": {"type": "number"}, "y": {"type": "number"}, "duration": {"type": "number", "default": 0.2}}, "required": ["x", "y"]}
)

drag = Tool(
    name="drag",
    description="Drag from one position to another.",
    inputSchema={"type": "object", "properties": {"from_x": {"type": "number"}, "from_y": {"type": "number"}, "to_x": {"type": "number"}, "to_y": {"type": "number"}, "duration": {"type": "number", "default": 0.5}}, "required": ["from_x", "from_y", "to_x", "to_y"]}
)

scroll = Tool(
    name="scroll",
    description="Scroll mouse wheel. Positive=up, Negative=down.",
    inputSchema={"type": "object", "properties": {"x": {"type": "number"}, "y": {"type": "number"}, "clicks": {"type": "integer"}}, "required": ["x", "y", "clicks"]}
)

type_text = Tool(
    name="type_text",
    description="Type text at cursor position. Click target field first.",
    inputSchema={"type": "object", "properties": {"text": {"type": "string"}, "interval": {"type": "number", "default": 0.02}}, "required": ["text"]}
)

press_key = Tool(
    name="press_key",
    description="Press a key (enter, tab, escape, f1-f12, arrows, etc.).",
    inputSchema={"type": "object", "properties": {"key": {"type": "string"}, "presses": {"type": "integer", "default": 1}}, "required": ["key"]}
)

hotkey = Tool(
    name="hotkey",
    description="Press keyboard shortcut (e.g., ['ctrl','c'] or ['cmd','space']).",
    inputSchema={"type": "object", "properties": {"keys": {"type": "array", "items": {"type": "string"}}}, "required": ["keys"]}
)

get_clipboard = Tool(
    name="get_clipboard",
    description="Get text from clipboard.",
    inputSchema={"type": "object", "properties": {}}
)

set_clipboard = Tool(
    name="set_clipboard",
    description="Set text in clipboard.",
    inputSchema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}
)

open_app = Tool(
    name="open_app",
    description="Open application by name (chrome, firefox, terminal, vscode, etc.).",
    inputSchema={"type": "object", "properties": {"app_name": {"type": "string"}, "args": {"type": "array", "items": {"type": "string"}, "default": []}}, "required": ["app_name"]}
)

switch_window = Tool(
    name="switch_window",
    description="Switch to window by title (partial match).",
    inputSchema={"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}
)

list_windows = Tool(
    name="list_windows",
    description="List all open windows.",
    inputSchema={"type": "object", "properties": {}}
)

close_window = Tool(
    name="close_window",
    description="Close active window (Cmd+W on macOS, Alt+F4 on Linux/Windows).",
    inputSchema={"type": "object", "properties": {}}
)

get_active_window = Tool(
    name="get_active_window",
    description="Get title of active window.",
    inputSchema={"type": "object", "properties": {}}
)

set_window_position = Tool(
    name="set_window_position",
    description="Set window position and/or size. Use x,y for position, width,height for size. Leave blank to only move or only resize.",
    inputSchema={"type": "object", "properties": {"title": {"type": "string"}, "x": {"type": "number"}, "y": {"type": "number"}, "width": {"type": "number"}, "height": {"type": "number"}}, "required": ["title"]}
)

browser_navigate = Tool(
    name="browser_navigate",
    description="Navigate to URL in browser.",
    inputSchema={"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}
)

browser_get_text = Tool(
    name="browser_get_text",
    description="Get all text from current page.",
    inputSchema={"type": "object", "properties": {}}
)

browser_click = Tool(
    name="browser_click",
    description="Click element by CSS selector or visible text.",
    inputSchema={"type": "object", "properties": {"selector": {"type": "string"}}, "required": ["selector"]}
)

browser_fill = Tool(
    name="browser_fill",
    description="Fill form field with value.",
    inputSchema={"type": "object", "properties": {"selector": {"type": "string"}, "value": {"type": "string"}}, "required": ["selector", "value"]}
)

browser_scrape = Tool(
    name="browser_scrape",
    description="Navigate to URL and return text (one-shot).",
    inputSchema={"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}
)

browser_screenshot = Tool(
    name="browser_screenshot",
    description="Take screenshot of current page.",
    inputSchema={"type": "object", "properties": {"full_page": {"type": "boolean", "default": False}}}
)

browser_close = Tool(
    name="browser_close",
    description="Close the browser and cleanup resources.",
    inputSchema={"type": "object", "properties": {}}
)

browser_restart = Tool(
    name="browser_restart",
    description="Restart browser with a fresh session (close and reopen).",
    inputSchema={"type": "object", "properties": {}}
)

browser_set_mode = Tool(
    name="browser_set_mode",
    description="Set browser mode (headless or headful).",
    inputSchema={"type": "object", "properties": {"headless": {"type": "boolean", "default": True}}}
)

run_command = Tool(
    name="run_command",
    description="Run shell command. Dangerous commands blocked.",
    inputSchema={"type": "object", "properties": {"command": {"type": "string"}, "cwd": {"type": "string"}, "timeout": {"type": "integer", "default": 30}}, "required": ["command"]}
)

read_file = Tool(
    name="read_file",
    description="Read file contents.",
    inputSchema={"type": "object", "properties": {"path": {"type": "string"}, "max_chars": {"type": "integer", "default": 10000}}, "required": ["path"]}
)

write_file = Tool(
    name="write_file",
    description="Write file (creates parent dirs).",
    inputSchema={"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}, "append": {"type": "boolean", "default": False}}, "required": ["path", "content"]}
)

list_dir = Tool(
    name="list_dir",
    description="List directory contents.",
    inputSchema={"type": "object", "properties": {"path": {"type": "string", "default": "."}, "recursive": {"type": "boolean", "default": False}}}
)

escalate = Tool(
    name="escalate",
    description="Hand off complex task to external AI service. Configure via DAN_ESCALATE_URL environment variable. Supports OpenAI-compatible APIs, Ollama, etc.",
    inputSchema={"type": "object", "properties": {"task": {"type": "string"}, "context": {"type": "string"}, "model": {"type": "string"}, "endpoint": {"type": "string", "description": "Override the default escalation endpoint URL"}}, "required": ["task"]}
)

ALL_TOOLS = [
    get_state, click, move_mouse, drag, scroll,
    type_text, press_key, hotkey, get_clipboard, set_clipboard,
    open_app, switch_window, list_windows, close_window, get_active_window, set_window_position,
    browser_navigate, browser_get_text, browser_click, browser_fill, browser_scrape, browser_screenshot, browser_close, browser_restart, browser_set_mode,
    run_command, read_file, write_file, list_dir,
    escalate,
]


# ============================================================================
# HANDLERS
# ============================================================================

def _log_action(action: str):
    """Log action to session and Python logger."""
    _session["actions"].append({"action": action, "time": asyncio.get_event_loop().time()})
    if len(_session["actions"]) > 20:
        _session["actions"] = _session["actions"][-20:]
    # Also log to Python logger
    logger.debug(f"Action: {action}")


def _get_monitors() -> list[dict]:
    """Get list of monitors. Returns basic info for primary monitor."""
    plat = platform.system()
    monitors = []

    if plat == "Darwin":
        # Use system_profiler to get display info
        try:
            result = subprocess.run(["system_profiler", "SPDisplaysDataType"], capture_output=True, text=True, timeout=5)
            # Parse basic info from output
            monitors.append({
                "id": 0,
                "name": "Built-in Display",
                "width": pyautogui.size()[0],
                "height": pyautogui.size()[1],
            })
        except Exception:
            monitors.append({"id": 0, "width": pyautogui.size()[0], "height": pyautogui.size()[1]})
    elif plat == "Linux":
        try:
            result = subprocess.run(["xrandr", "--listmonitors"], capture_output=True, text=True, timeout=3)
            for line in result.stdout.strip().split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 4:
                    monitors.append({
                        "id": len(monitors),
                        "name": parts[-1] if len(parts) > 3 else f"Monitor {len(monitors)}",
                        "width": pyautogui.size()[0],  # xrandr doesn't give easy dimensions
                        "height": pyautogui.size()[1],
                    })
        except Exception:
            monitors.append({"id": 0, "width": pyautogui.size()[0], "height": pyautogui.size()[1]})
    else:  # Windows
        monitors.append({"id": 0, "width": pyautogui.size()[0], "height": pyautogui.size()[1]})

    return monitors


def _get_active_window() -> str:
    try:
        if platform.system() == "Darwin":
            result = subprocess.run(["osascript", "-e", 'tell application "System Events" to get name of first process whose frontmost is true'], capture_output=True, text=True, timeout=2)
            return result.stdout.strip() or "unknown"
        elif platform.system() == "Linux":
            result = subprocess.run(["xdotool", "getactivewindow", "getwindowname"], capture_output=True, text=True, timeout=2)
            return result.stdout.strip() or "unknown"
        else:
            return _get_active_window_windows()
    except Exception:
        return "unknown"


def _get_active_window_windows() -> str:
    """Get active window title on Windows using ctypes."""
    import ctypes
    from ctypes import wintypes
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return "unknown"
    buf = ctypes.create_unicode_buffer(length + 1)
    ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value or "unknown"


def _list_windows_windows() -> list[str]:
    """List all visible window titles on Windows using ctypes."""
    import ctypes
    from ctypes import wintypes

    windows = []

    # Callback function for EnumWindows
    def enum_callback(hwnd, lParam):
        if ctypes.windll.user32.IsWindowVisible(hwnd):
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value.strip()
                if title:
                    windows.append(title)
        return True

    # Define callback type
    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    ctypes.windll.user32.EnumWindows(enum_proc(enum_callback), 0)

    return windows


def _get_clipboard_text() -> str:
    """Get text from clipboard. Works on macOS, Linux, and Windows."""
    import shutil
    plat = platform.system()
    if plat == "Darwin":
        result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=2)
        return result.stdout
    elif plat == "Linux":
        # Try xclip first, then xsel
        try:
            result = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                return result.stdout
        except FileNotFoundError:
            pass
        try:
            result = subprocess.run(["xsel", "--clipboard", "--output"], capture_output=True, text=True, timeout=2)
            return result.stdout
        except FileNotFoundError:
            pass
        # Try wl-paste (Wayland)
        try:
            result = subprocess.run(["wl-paste"], capture_output=True, text=True, timeout=2)
            return result.stdout
        except FileNotFoundError:
            pass
        return ""
    else:
        # Windows
        try:
            import ctypes
            CF_TEXT = 1
            kernel32 = ctypes.windll.kernel32
            kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
            kernel32.GlobalLock.restype = ctypes.c_void_p
            kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]

            user32 = ctypes.windll.user32
            user32.GetClipboardData.argtypes = [ctypes.c_uint]
            user32.GetClipboardData.restype = ctypes.c_void_p
            user32.OpenClipboard.argtypes = [ctypes.c_void_p]
            user32.CloseClipboard.argtypes = []
            user32.EmptyClipboard.argtypes = []

            user32.OpenClipboard(None)
            try:
                h_data = user32.GetClipboardData(CF_TEXT)
                if h_data:
                    data = kernel32.GlobalLock(h_data)
                    if data:
                        text = ctypes.c_char_p(data).value.decode("utf-8")
                        kernel32.GlobalUnlock(data)
                        return text
            finally:
                user32.CloseClipboard()
            return ""
        except Exception:
            return ""
    return ""


def _set_clipboard_text(text: str) -> bool:
    """Set text in clipboard. Works on macOS, Linux, and Windows."""
    plat = platform.system()
    if plat == "Darwin":
        result = subprocess.run(["pbcopy"], input=text, capture_output=True, timeout=2)
        return result.returncode == 0
    elif plat == "Linux":
        # Try xclip first, then xsel
        try:
            result = subprocess.run(["xclip", "-selection", "clipboard"], input=text, capture_output=True, timeout=2)
            if result.returncode == 0:
                return True
        except FileNotFoundError:
            pass
        try:
            result = subprocess.run(["xsel", "--clipboard", "--input"], input=text, capture_output=True, timeout=2)
            if result.returncode == 0:
                return True
        except FileNotFoundError:
            pass
        # Try wl-paste (Wayland)
        try:
            result = subprocess.run(["wl-paste"], input=text, capture_output=True, timeout=2)
            return result.returncode == 0
        except FileNotFoundError:
            pass
        return False
    else:
        # Windows
        try:
            import ctypes
            CF_TEXT = 1
            kernel32 = ctypes.windll.kernel32
            GlobalAlloc = kernel32.GlobalAlloc
            GlobalLock = kernel32.GlobalLock
            GlobalUnlock = kernel32.GlobalUnlock

            user32 = ctypes.windll.user32
            OpenClipboard = user32.OpenClipboard
            EmptyClipboard = user32.EmptyClipboard
            SetClipboardData = user32.SetClipboardData
            CloseClipboard = user32.CloseClipboard

            data = text.encode("utf-8")
            h_data = GlobalAlloc(0x0002, len(data) + 1)  # GMEM_MOVEABLE
            p_data = GlobalLock(h_data)
            ctypes.memmove(p_data, data, len(data))
            ctypes.memset(p_data + len(data), 0, 1)
            GlobalUnlock(h_data)

            OpenClipboard(None)
            EmptyClipboard()
            SetClipboardData(CF_TEXT, h_data)
            CloseClipboard()
            return True
        except Exception:
            return False


def _build_element_map(screenshot: Image.Image) -> tuple[list[dict], bool, str]:
    """Build element map from screenshot using OCR.

    Returns: (elements, ocr_available, error_message)
    """
    ocr_available, error_msg = _check_ocr_available()
    if not ocr_available:
        return [], False, error_msg
    try:
        import pytesseract
        data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT, config="--psm 11")
        elements = []
        n = len(data["text"])
        for i in range(n):
            text = data["text"][i].strip()
            conf = int(data["conf"][i])
            if text and conf >= 50 and data["width"][i] >= 5 and data["height"][i] >= 5:
                elements.append({"text": text, "x": data["left"][i], "y": data["top"][i], "w": data["width"][i], "h": data["height"][i], "center_x": data["left"][i] + data["width"][i] // 2, "center_y": data["top"][i] + data["height"][i] // 2, "confidence": conf})
        elements.sort(key=lambda e: e["confidence"], reverse=True)
        return elements[:50], True, ""
    except Exception as e:
        return [], False, f"OCR processing error: {str(e)}"


async def handle_get_state(name: str, args: dict) -> str:
    loop = asyncio.get_event_loop()
    screenshot = await loop.run_in_executor(None, pyautogui.screenshot)
    buf = io.BytesIO()
    screenshot.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    elements, ocr_available, ocr_error = await loop.run_in_executor(None, _build_element_map, screenshot)
    active_window = _get_active_window()
    _session["active_window"] = active_window
    _session["elements"] = elements  # Store for element_text lookup
    _log_action("get_state")
    return json.dumps({
        "screenshot_base64": b64,
        "active_window": active_window,
        "screen_size": {"width": pyautogui.size()[0], "height": pyautogui.size()[1]},
        "platform": platform.system(),
        "elements": elements,
        "ocr_available": ocr_available,
        "ocr_error": ocr_error,
        "last_actions": _session["actions"][-5:]
    })


async def handle_click(name: str, args: dict) -> str:
    x, y = args.get("x"), args.get("y")
    element_text = args.get("element_text")

    # If element_text provided, look up coordinates from last get_state
    if element_text:
        elements = _session.get("elements", [])
        if not elements:
            return json.dumps({"error": "No elements available. Call get_state first to detect elements on screen."})

        # Find matching element (case-insensitive partial match)
        matching = None
        for elem in elements:
            if element_text.lower() in elem.get("text", "").lower():
                matching = elem
                break

        if not matching:
            # Show available elements for debugging
            available = [e.get("text", "")[:30] for e in elements[:10]]
            return json.dumps({
                "error": f"Element '{element_text}' not found. Available: {available}",
                "available_elements": available
            })

        x = matching["center_x"]
        y = matching["center_y"]
        action_desc = f"clicked '{matching.get('text', '')[:20]}' at ({x}, {y})"
    elif x is None or y is None:
        return json.dumps({"error": "x,y coordinates or element_text required"})

    loop = asyncio.get_event_loop()
    button = args.get("button", "left")
    clicks = args.get("clicks", 1)
    await loop.run_in_executor(None, lambda: pyautogui.click(int(x), int(y), button=button, clicks=clicks))
    _log_action(f"click({x},{y})")
    return json.dumps({"ok": True, "action": action_desc if element_text else f"clicked ({int(x)},{int(y)})"})


async def handle_move_mouse(name: str, args: dict) -> str:
    x, y = args["x"], args["y"]
    duration = args.get("duration", 0.2)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: pyautogui.moveTo(int(x), int(y), duration=duration))
    _log_action(f"move_mouse({x},{y})")
    return json.dumps({"ok": True})


async def handle_drag(name: str, args: dict) -> str:
    from_x, from_y = args["from_x"], args["from_y"]
    to_x, to_y = args["to_x"], args["to_y"]
    duration = args.get("duration", 0.5)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: pyautogui.drag(to_x - from_x, to_y - from_y, duration=duration, button="left"))
    _log_action(f"drag({from_x},{from_y}→{to_x},{to_y})")
    return json.dumps({"ok": True})


async def handle_scroll(name: str, args: dict) -> str:
    x, y, clicks = args["x"], args["y"], args["clicks"]
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: pyautogui.scroll(int(clicks), x=int(x), y=int(y)))
    _log_action(f"scroll({clicks} at {x},{y})")
    return json.dumps({"ok": True})


async def handle_type_text(name: str, args: dict) -> str:
    text = args["text"]
    interval = args.get("interval", 0.02)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: pyautogui.write(text, interval=interval))
    _log_action(f"type_text('{text[:30]}...')" if len(text) > 30 else f"type_text('{text}')")
    return json.dumps({"ok": True, "typed": text})


async def handle_press_key(name: str, args: dict) -> str:
    key = args["key"]
    presses = args.get("presses", 1)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: pyautogui.press(key, presses=presses))
    _log_action(f"press_key({key} x{presses})")
    return json.dumps({"ok": True})


async def handle_hotkey(name: str, args: dict) -> str:
    keys = args["keys"]
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: pyautogui.hotkey(*keys))
    _log_action(f"hotkey({'+'.join(keys)})")
    return json.dumps({"ok": True})


async def handle_get_clipboard(name: str, args: dict) -> str:
    """Get text from clipboard."""
    loop = asyncio.get_event_loop()
    text = await loop.run_in_executor(None, _get_clipboard_text)
    _log_action("get_clipboard()")
    return json.dumps({"text": text, "length": len(text)})


async def handle_set_clipboard(name: str, args: dict) -> str:
    """Set text in clipboard."""
    text = args["text"]
    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(None, lambda: _set_clipboard_text(text))
    _log_action(f"set_clipboard({len(text)} chars)")
    return json.dumps({"ok": success, "length": len(text)})


async def handle_open_app(name: str, args: dict) -> str:
    app_name = args["app_name"]
    extra_args = args.get("args", [])
    apps = {"darwin": {"chrome": ["open", "-a", "Google Chrome"], "firefox": ["open", "-a", "Firefox"], "terminal": ["open", "-a", "Terminal"], "vscode": ["open", "-a", "Visual Studio Code"]}, "linux": {"chrome": ["google-chrome"], "firefox": ["firefox"], "terminal": ["gnome-terminal"], "vscode": ["code"]}, "windows": {"chrome": ["start", "chrome"], "firefox": ["start", "firefox"], "terminal": ["cmd", "/c", "start", "cmd"], "vscode": ["code"]}}
    plat = platform.system().lower()
    plat_key = "darwin" if plat == "Darwin" else "linux" if plat == "Linux" else "windows"
    cmd = apps.get(plat_key, {}).get(app_name.lower(), [app_name])
    cmd.extend(extra_args)
    try:
        subprocess.Popen(cmd, start_new_session=True)
        _log_action(f"open_app({app_name})")
        return json.dumps({"ok": True, "launched": app_name})
    except FileNotFoundError:
        return json.dumps({"error": f"App '{app_name}' not found"})


async def handle_switch_window(name: str, args: dict) -> str:
    title = args["title"]
    try:
        if platform.system() == "Darwin":
            # Try to activate by app name first, then by window title
            script = f'tell application "{title}" to activate'
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3)
            if result.returncode != 0:
                # Fallback: try to find window with title
                script = '''
                tell application "System Events"
                    set frontApp to first application process whose frontmost is true
                    set windowList to windows of frontApp
                    repeat with win in windowList
                        if name of win contains "{title}" then
                            set frontmost of win to true
                            return true
                        end if
                    end repeat
                end tell
                '''.format(title=title)
                subprocess.run(["osascript", "-e", script], timeout=3)
        elif platform.system() == "Linux":
            try:
                subprocess.run(["wmctrl", "-a", title], timeout=3)
            except FileNotFoundError:
                return json.dumps({"error": "wmctrl not found. Install with: sudo apt install wmctrl"})
        else:
            # Windows - use partial match
            import ctypes
            from ctypes import wintypes

            # Callback to find window containing title
            found_hwnd = None

            def enum_callback(hwnd, lParam):
                nonlocal found_hwnd
                if ctypes.windll.user32.IsWindowVisible(hwnd):
                    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                        if title.lower() in buf.value.lower():
                            found_hwnd = hwnd
                            return False  # Stop enumeration
                return True

            enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            ctypes.windll.user32.EnumWindows(enum_proc(enum_callback), 0)

            if found_hwnd:
                ctypes.windll.user32.SetForegroundWindow(found_hwnd)
                ctypes.windll.user32.BringWindowToTop(found_hwnd)
            else:
                return json.dumps({"error": f"Window not found: {title}"})

        _session["active_window"] = title
        _log_action(f"switch_window({title})")
        return json.dumps({"ok": True})
    except FileNotFoundError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def handle_list_windows(name: str, args: dict) -> str:
    try:
        if platform.system() == "Darwin":
            script = 'tell application "System Events" to get name of every window of every process'
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3)
            return json.dumps({"windows": result.stdout.strip().split(", ") if result.stdout else []})
        elif platform.system() == "Linux":
            try:
                result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, timeout=3)
                windows = [line.split(None, 3)[-1] for line in result.stdout.strip().splitlines() if line]
                return json.dumps({"windows": windows})
            except FileNotFoundError:
                return json.dumps({"error": "wmctrl not found. Install with: sudo apt install wmctrl", "windows": []})
        else:
            # Windows
            loop = asyncio.get_event_loop()
            windows = await loop.run_in_executor(None, _list_windows_windows)
            return json.dumps({"windows": windows})
    except FileNotFoundError as e:
        return json.dumps({"error": str(e), "windows": []})
    except Exception as e:
        return json.dumps({"error": str(e), "windows": []})


async def handle_close_window(name: str, args: dict) -> str:
    loop = asyncio.get_event_loop()
    if platform.system() == "Darwin":
        await loop.run_in_executor(None, lambda: pyautogui.hotkey("cmd", "w"))
    else:
        await loop.run_in_executor(None, lambda: pyautogui.hotkey("alt", "f4"))
    _log_action("close_window()")
    return json.dumps({"ok": True})


async def handle_get_active_window(name: str, args: dict) -> str:
    title = _get_active_window()
    _session["active_window"] = title
    _log_action("get_active_window()")
    return json.dumps({"active_window": title})


async def handle_set_window_position(name: str, args: dict) -> str:
    """Set window position and/or size."""
    title = args.get("title")
    x = args.get("x")
    y = args.get("y")
    width = args.get("width")
    height = args.get("height")

    if not title:
        return json.dumps({"error": "title is required"})

    plat = platform.system()

    try:
        if plat == "Darwin":
            # Use osascript to move/resize window
            script_parts = []
            script_parts.append(f'set windowPosition to false')
            if x is not None and y is not None:
                script_parts = [f'set position of window 1 of process "{title}" to {{x, y}}']
                script = f'''
                tell application "System Events"
                    tell process "{title}"
                        set frontmost to true
                        set position of window 1 to {{{x}, {y}}}
                    end tell
                end tell
                '''
            if width is not None and height is not None:
                script += f'''
                tell application "System Events"
                    tell process "{title}"
                        set size of window 1 to {{{width}, {height}}}
                    end tell
                end tell
                '''
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=3)

        elif plat == "Linux":
            # Use wmctrl to move/resize
            if x is not None and y is not None:
                subprocess.run(["wmctrl", "-r", title, "-e", f"0,{x},{y},-1,-1"], timeout=3)
            if width is not None and height is not None:
                # -1 means keep current
                wx = x if x is not None else -1
                wy = y if y is not None else -1
                subprocess.run(["wmctrl", "-r", title, "-e", f"0,{wx},{wy},{width},{height}"], timeout=3)

        else:  # Windows
            import ctypes
            from ctypes import wintypes

            # Find window by title (partial match)
            found_hwnd = None

            def enum_callback(hwnd, lParam):
                nonlocal found_hwnd
                if ctypes.windll.user32.IsWindowVisible(hwnd):
                    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                        if title.lower() in buf.value.lower():
                            found_hwnd = hwnd
                            return False
                return True

            enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            ctypes.windll.user32.EnumWindows(enum_proc(enum_callback), 0)

            if found_hwnd:
                if x is not None and y is not None:
                    ctypes.windll.user32.SetWindowPos(found_hwnd, None, x, y, 0, 0, 0x0001 | 0x0004)  # SWP_NOSIZE | SWP_NOZORDER
                if width is not None and height is not None:
                    ctypes.windll.user32.SetWindowPos(found_hwnd, None, 0, 0, width, height, 0x0002 | 0x0004)  # SWP_NOMOVE | SWP_NOZORDER
            else:
                return json.dumps({"error": f"Window not found: {title}"})

        _log_action(f"set_window_position({title})")
        return json.dumps({"ok": True, "title": title, "x": x, "y": y, "width": width, "height": height})

    except FileNotFoundError:
        return json.dumps({"error": "Window manager tool not found. Install wmctrl on Linux."})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def _get_browser_page():
    """Get or create browser page. Uses headless mode by default."""
    global _browser_page, _browser_playwright
    if _browser_page is None:
        # Use config if available, otherwise use global default
        cfg = get_config()
        headless = cfg.get("browser", {}).get("headless", _browser_headless)
        from playwright.async_api import async_playwright
        _browser_playwright = await async_playwright().start()
        browser = await _browser_playwright.chromium.launch(headless=headless)
        _browser_page = await browser.new_page()
    return _browser_page


async def _close_browser():
    """Close browser and cleanup."""
    global _browser_page, _browser_playwright
    if _browser_page is not None:
        try:
            await _browser_page.close()
        except Exception:
            pass
        _browser_page = None
    if _browser_playwright is not None:
        try:
            await _browser_playwright.stop()
        except Exception:
            pass
        _browser_playwright = None


async def _restart_browser():
    """Restart browser with new session."""
    await _close_browser()
    return await _get_browser_page()


async def handle_browser_navigate(name: str, args: dict) -> str:
    url = args["url"]
    page = await _get_browser_page()
    await page.goto(url, wait_until="networkidle", timeout=30000)
    title = await page.title()
    _log_action(f"browser_navigate({url})")
    return json.dumps({"ok": True, "url": url, "title": title})


async def handle_browser_get_text(name: str, args: dict) -> str:
    page = await _get_browser_page()
    text = await page.evaluate("() => document.body.innerText")
    _log_action("browser_get_text()")
    return json.dumps({"text": text[:5000], "truncated": len(text) > 5000})


async def handle_browser_click(name: str, args: dict) -> str:
    selector = args["selector"]
    page = await _get_browser_page()
    try:
        await page.click(selector, timeout=5000)
    except Exception:
        await page.get_by_text(selector).first.click(timeout=5000)
    _log_action(f"browser_click({selector})")
    return json.dumps({"ok": True})


async def handle_browser_fill(name: str, args: dict) -> str:
    selector, value = args["selector"], args["value"]
    page = await _get_browser_page()
    await page.fill(selector, value)
    _log_action(f"browser_fill({selector})")
    return json.dumps({"ok": True})


async def handle_browser_scrape(name: str, args: dict) -> str:
    url = args["url"]
    page = await _get_browser_page()
    await page.goto(url, wait_until="networkidle", timeout=30000)
    text = await page.evaluate("() => document.body.innerText")
    _log_action(f"browser_scrape({url})")
    return json.dumps({"url": url, "text": text[:8000], "truncated": len(text) > 8000})


async def handle_browser_screenshot(name: str, args: dict) -> str:
    full_page = args.get("full_page", False)
    page = await _get_browser_page()
    screenshot = await page.screenshot(full_page=full_page)
    b64 = base64.b64encode(screenshot).decode()
    _log_action(f"browser_screenshot(full_page={full_page})")
    return json.dumps({"screenshot_base64": b64, "full_page": full_page})


async def handle_browser_close(name: str, args: dict) -> str:
    """Close the browser and cleanup resources."""
    await _close_browser()
    _log_action("browser_close()")
    return json.dumps({"ok": True, "message": "Browser closed"})


async def handle_browser_restart(name: str, args: dict) -> str:
    """Restart browser with a fresh session."""
    await _restart_browser()
    _log_action("browser_restart()")
    return json.dumps({"ok": True, "message": "Browser restarted"})


async def handle_browser_set_mode(name: str, args: dict) -> str:
    """Set browser mode (headless or headful)."""
    global _browser_headless
    headless = args.get("headless", True)
    was_headless = _browser_headless
    _browser_headless = headless
    # If browser exists and mode changed, restart to apply
    if _browser_page is not None and was_headless != headless:
        await _restart_browser()
    _log_action(f"browser_set_mode(headless={headless})")
    return json.dumps({"ok": True, "headless": _browser_headless})


async def handle_run_command(name: str, args: dict) -> str:
    command = args["command"]
    cwd = args.get("cwd", str(Path.home()))
    timeout = args.get("timeout", 30)
    dangerous = ["rm -rf /", "mkfs", "dd if=/dev", ":(){:|:&};:", "chmod 777 /"]
    if any(d in command.lower() for d in dangerous):
        return json.dumps({"error": "Blocked dangerous command", "ok": False})
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, lambda: subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout, cwd=cwd))
        _log_action(f"run_command('{command[:50]}...')" if len(command) > 50 else f"run_command('{command}')")
        return json.dumps({"stdout": result.stdout[-3000:], "stderr": result.stderr[-1000:], "returncode": result.returncode, "ok": result.returncode == 0})
    except subprocess.TimeoutExpired:
        return json.dumps({"error": f"Command timed out after {timeout}s", "ok": False})
    except Exception as e:
        return json.dumps({"error": str(e), "ok": False})


async def handle_read_file(name: str, args: dict) -> str:
    path = Path(args["path"]).expanduser()
    max_chars = args.get("max_chars", 10000)
    try:
        content = path.read_text(errors="replace")[:max_chars]
        _log_action(f"read_file({path})")
        return json.dumps({"content": content, "path": str(path), "truncated": len(content) >= max_chars})
    except Exception as e:
        return json.dumps({"error": str(e), "ok": False})


async def handle_write_file(name: str, args: dict) -> str:
    path = Path(args["path"]).expanduser()
    content = args["content"]
    append = args.get("append", False)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if append:
            with open(path, "a") as f:
                f.write(content)
        else:
            path.write_text(content)
        _log_action(f"write_file({path})")
        return json.dumps({"ok": True, "path": str(path), "bytes": len(content)})
    except Exception as e:
        return json.dumps({"error": str(e), "ok": False})


async def handle_list_dir(name: str, args: dict) -> str:
    path = Path(args.get("path", ".")).expanduser()
    recursive = args.get("recursive", False)
    try:
        if recursive:
            entries = [str(p.relative_to(path)) for p in path.rglob("*") if p.is_file()][:200]
        else:
            entries = sorted([p.name for p in path.iterdir()])
        _log_action(f"list_dir({path})")
        return json.dumps({"entries": entries, "count": len(entries), "path": str(path)})
    except Exception as e:
        return json.dumps({"error": str(e), "ok": False})


async def handle_escalate(name: str, args: dict) -> str:
    """Escalate to an external AI for complex tasks.

    Configurable via environment variables:
    - DAN_ESCALATE_URL: Base URL for the API (default: http://localhost:31000)
    - DAN_ESCALATE_ENDPOINT: API endpoint path (default: /v1/chat/completions)
    - DAN_ESCALATE_API_KEY: Optional API key
    - DAN_ESCALATE_DEFAULT_MODEL: Default model to use
    """
    import os

    task = args["task"]
    context = args.get("context", "")
    model = args.get("model", os.environ.get("DAN_ESCALATE_DEFAULT_MODEL", "qwen-plus"))
    endpoint = args.get("endpoint", os.environ.get("DAN_ESCALATE_URL", "http://localhost:31000"))
    api_path = os.environ.get("DAN_ESCALATE_ENDPOINT", "/v1/chat/completions")
    api_key = os.environ.get("DAN_ESCALATE_API_KEY")

    full_prompt = f"Context: {context}\n\nTask: {task}" if context else task

    # Build headers
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            url = f"{endpoint}{api_path}"
            payload = {"model": model, "messages": [{"role": "user", "content": full_prompt}]}
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                return json.dumps({"error": f"Escalation API returned {resp.status_code}: {resp.text[:200]}", "ok": False})
            data = resp.json()
            # Handle different response formats (OpenAI-compatible, Ollama, etc.)
            if "choices" in data and len(data["choices"]) > 0:
                reply = data["choices"][0].get("message", {}).get("content", "")
            elif "response" in data:  # Ollama format
                reply = data["response"]
            else:
                reply = str(data)
            _log_action(f"escalate('{task[:40]}...')")
            return json.dumps({"result": reply, "escalated_to": endpoint, "model": model, "ok": True})
    except httpx.ConnectError:
        return json.dumps({"error": f"Cannot connect to escalation service at {endpoint}. Set DAN_ESCALATE_URL environment variable.", "ok": False})
    except Exception as e:
        return json.dumps({"error": str(e), "ok": False})


HANDLERS = {
    "get_state": handle_get_state, "click": handle_click, "move_mouse": handle_move_mouse, "drag": handle_drag, "scroll": handle_scroll,
    "type_text": handle_type_text, "press_key": handle_press_key, "hotkey": handle_hotkey, "get_clipboard": handle_get_clipboard, "set_clipboard": handle_set_clipboard,
    "open_app": handle_open_app, "switch_window": handle_switch_window, "list_windows": handle_list_windows, "close_window": handle_close_window, "get_active_window": handle_get_active_window, "set_window_position": handle_set_window_position,
    "browser_navigate": handle_browser_navigate, "browser_get_text": handle_browser_get_text, "browser_click": handle_browser_click, "browser_fill": handle_browser_fill, "browser_scrape": handle_browser_scrape, "browser_screenshot": handle_browser_screenshot, "browser_close": handle_browser_close, "browser_restart": handle_browser_restart, "browser_set_mode": handle_browser_set_mode,
    "run_command": handle_run_command, "read_file": handle_read_file, "write_file": handle_write_file, "list_dir": handle_list_dir,
    "escalate": handle_escalate,
}


# ============================================================================
# MCP SERVER
# ============================================================================

@app.list_tools()
async def list_tools() -> list[Tool]:
    return ALL_TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool invocation with logging."""
    logger.info(f"Tool call: {name} with args: {arguments}")
    handler = HANDLERS.get(name)
    if not handler:
        logger.warning(f"Unknown tool: {name}")
        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]
    try:
        result = await handler(name, arguments)
        logger.debug(f"Tool {name} result: {result[:200]}..." if len(result) > 200 else f"Tool {name} result: {result}")
        return [TextContent(type="text", text=result)]
    except Exception as e:
        logger.error(f"Tool {name} error: {str(e)}", exc_info=True)
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
