#!/usr/bin/env python3
"""DAN MCP - TEST SUITE"""
import asyncio
import json
import os
os.environ['DISPLAY'] = ':99'

from dan_computer_use_mcp import server

async def test(name, handler, args, expect_error=False):
    try:
        r = await handler(name, args)
        d = json.loads(r)
        ok = d.get('ok', False)
        has_err = 'error' in d
        if (expect_error and has_err) or (not expect_error and ok):
            return True, ""
        return False, r[:80]
    except Exception as e:
        return False, str(e)[:60]

async def main():
    p = f = 0
    
    print("\n=== STATE ===")
    ok, err = await test('get_state', server.handle_get_state, {})
    print("✅ get_state" if ok else f"❌ get_state: {err}")
    p += ok; f += not ok
    
    print("\n=== MOUSE ===")
    tests = [
        ("click", server.handle_click, {'x': 100, 'y': 100}, False),
        ("click empty", server.handle_click, {}, True),
        ("click neg", server.handle_click, {'x': -1, 'y': -1}, True),
        ("move_mouse", server.handle_move_mouse, {'x': 100, 'y': 100}, False),
        ("drag", server.handle_drag, {'from_x': 1, 'from_y': 1, 'to_x': 2, 'to_y': 2}, False),
        ("drag empty", server.handle_drag, {}, True),
        ("scroll", server.handle_scroll, {'x': 100, 'y': 100, 'clicks': 5}, False),
        ("scroll empty", server.handle_scroll, {}, True),
    ]
    for name, h, a, err in tests:
        ok, e = await test(name, h, a, err)
        print(f"✅ {name}" if ok else f"❌ {name}: {e}")
        p += ok; f += not ok
    
    print("\n=== KEYBOARD ===")
    ok, _ = await test('type_text', server.handle_type_text, {'text': 'hi'}, False)
    print("✅ type_text" if ok else "❌ type_text")
    p += ok; f += not ok
    
    ok, _ = await test('press_key', server.handle_press_key, {'key': 'enter'}, False)
    print("✅ press_key" if ok else "❌ press_key")
    p += ok; f += not ok
    
    ok, _ = await test('hotkey', server.handle_hotkey, {'keys': ['ctrl', 'c']}, False)
    print("✅ hotkey" if ok else "❌ hotkey")
    p += ok; f += not ok
    
    print("\n=== CLIPBOARD ===")
    ok, _ = await test('get_clipboard', server.handle_get_clipboard, {}, False)
    print("✅ get_clipboard" if ok else "❌ get_clipboard")
    p += ok; f += not ok
    
    ok, _ = await test('set_clipboard', server.handle_set_clipboard, {'text': 'test'}, False)
    print("✅ set_clipboard" if ok else "❌ set_clipboard")
    p += ok; f += not ok
    
    print("\n=== WINDOWS ===")
    ok, _ = await test('list_windows', server.handle_list_windows, {}, False)
    print("✅ list_windows" if ok else "❌ list_windows")
    p += ok; f += not ok
    
    print("\n=== BROWSER ===")
    ok, _ = await test('nav', server.handle_browser_navigate, {'url': 'https://example.com'}, False)
    print("✅ browser valid" if ok else f"❌ browser: {err}")
    p += ok; f += not ok
    
    ok, _ = await test('nav', server.handle_browser_navigate, {'url': 'bad'}, True)
    print("✅ browser invalid" if ok else f"❌ browser: {err}")
    p += ok; f += not ok
    
    print("\n=== SHELL ===")
    ok, _ = await test('run', server.handle_run_command, {'command': 'echo ok'}, False)
    print("✅ run safe" if ok else f"❌ run: {err}")
    p += ok; f += not ok
    
    ok, _ = await test('run', server.handle_run_command, {'command': 'rm -rf /'}, True)
    print("✅ run blocked" if ok else f"❌ run: {err}")
    p += ok; f += not ok
    
    print("\n=== FILES ===")
    ok, _ = await test('read', server.handle_read_file, {'path': '/etc/hostname'}, False)
    print("✅ read allowed" if ok else f"❌ read: {err}")
    p += ok; f += not ok
    
    ok, _ = await test('read', server.handle_read_file, {'path': '/etc/passwd'}, True)
    print("✅ read blocked" if ok else f"❌ read: {err}")
    p += ok; f += not ok
    
    ok, _ = await test('read', server.handle_read_file, {'path': '../etc'}, True)
    print("✅ read traversal" if ok else f"❌ read: {err}")
    p += ok; f += not ok
    
    ok, _ = await test('write', server.handle_write_file, {'path': '/tmp/t.txt', 'content': 'x'}, False)
    print("✅ write allowed" if ok else f"❌ write: {err}")
    p += ok; f += not ok
    
    ok, _ = await test('write', server.handle_write_file, {'path': '../../../x', 'content': 'x'}, True)
    print("✅ write traversal" if ok else f"❌ write: {err}")
    p += ok; f += not ok
    
    print("\n" + "="*50)
    print(f"FINAL: {p} ✅ PASSED | {f} ❌ FAILED")
    print("="*50)

asyncio.run(main())