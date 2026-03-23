"""
Dan Voice Integration - STT + TTS for Dan MCP
"""

import os
import subprocess
import json
import logging

logger = logging.getLogger("dan-computer-use-mcp")

# ============================================================================
# STT - Speech to Text (whisper.cpp)
# ============================================================================

def get_whisper_path() -> str:
    """Find whisper executable."""
    # Check common locations
    paths = [
        "/usr/local/bin/whisper-cli",
        "/usr/bin/whisper-cli",
        os.path.expanduser("~/whisper.cpp/build/bin/whisper-cli"),
        os.path.expanduser("~/.local/bin/whisper-cli"),
        "whisper-cli",  # PATH
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return "whisper-cli"  # Fallback to PATH


async def handle_speech_to_text(name: str, args: dict) -> str:
    """Convert speech/audio to text."""
    audio_path = args.get("audio_path")
    language = args.get("language", "en")
    
    if not audio_path:
        # Check if base64 audio provided
        audio_base64 = args.get("audio_base64")
        if audio_base64:
            # Save to temp file
            audio_path = "/tmp/stt_input.wav"
            try:
                audio_data = base64.b64decode(audio_base64)
                with open(audio_path, "wb") as f:
                    f.write(audio_data)
            except Exception as e:
                return json.dumps({"error": f"Failed to decode audio: {e}"})
        else:
            return json.dumps({"error": "audio_path or audio_base64 required"})
    
    if not os.path.exists(audio_path):
        return json.dumps({"error": f"Audio file not found: {audio_path}"})
    
    whisper_path = get_whisper_path()
    
    try:
        # Run whisper
        result = subprocess.run(
            [whisper_path, "-m", os.path.expanduser("~/whisper.cpp/models/ggml-tiny.bin"),
             "-f", audio_path, "-l", language, "-np"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        text = result.stdout.strip()
        return json.dumps({
            "ok": True,
            "text": text,
            "language": language,
            "audio_path": audio_path
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "STT timeout - audio too long"})
    except FileNotFoundError:
        return json.dumps({
            "error": "whisper-cli not found. Install: https://github.com/ggerganov/whisper.cpp",
            "install_hint": "brew install whisper-cpp (Mac) or compile from source"
        })
    except Exception as e:
        return json.dumps({"error": f"STT failed: {str(e)}"})


# ============================================================================
# TTS - Text to Speech (KittenTTS / gTTS fallback)
# ============================================================================

_tts_available = None
_tts_model = None


def _init_tts():
    """Initialize TTS engine."""
    global _tts_available, _tts_model
    
    if _tts_available is not None:
        return
    
    # Try KittenTTS first
    try:
        from kittentts import KittenTTS
        _tts_model = KittenTTS("KittenML/kitten-tts-nano-0.8")
        _tts_available = "kittentts"
        logger.info("KittenTTS initialized")
        return
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"KittenTTS init failed: {e}")
    
    # Fallback to gTTS
    try:
        from gtts import gTTS
        _tts_available = "gtts"
        logger.info("gTTS initialized (fallback)")
        return
    except ImportError:
        pass
    
    _tts_available = None
    logger.error("No TTS available - install kittentts or gtts")


async def handle_text_to_speech(name: str, args: dict) -> str:
    """Convert text to speech audio."""
    global _tts_available, _tts_model
    
    text = args.get("text")
    voice = args.get("voice", "Bella")  # KittenTTS default
    output_path = args.get("output_path", "/tmp/tts_output.mp3")
    speed = args.get("speed", 1.0)
    
    if not text:
        return json.dumps({"error": "text is required"})
    
    # Initialize if needed
    if _tts_available is None:
        _init_tts()
    
    if _tts_available is None:
        return json.dumps({"error": "No TTS available. Install: pip install gtts or kittentts"})
    
    try:
        if _tts_available == "kittentts":
            audio = _tts_model.generate(text, voice=voice, speed=speed)
            
            # Save as WAV (24kHz)
            import numpy as np
            import wave
            
            # Convert to 16-bit
            audio_int16 = (audio * 32767).astype(np.int16)
            
            output_path_wav = output_path.replace(".mp3", ".wav")
            with wave.open(output_path_wav, 'wb') as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(24000)
                f.writeframes(audio_int16.tobytes())
            
            return json.dumps({
                "ok": True,
                "audio_path": output_path_wav,
                "voice": voice,
                "speed": speed,
                "engine": "kittentts"
            })
            
        elif _tts_available == "gtts":
            from gtts import gTTS
            tts = gTTS(text)
            tts.save(output_path)
            
            return json.dumps({
                "ok": True,
                "audio_path": output_path,
                "voice": "default",
                "speed": speed,
                "engine": "gtts"
            })
            
    except Exception as e:
        return json.dumps({"error": f"TTS failed: {str(e)}"})


async def handle_list_voices(name: str, args: dict) -> str:
    """List available TTS voices."""
    global _tts_available, _tts_model
    
    if _tts_available is None:
        _init_tts()
    
    if _tts_available == "kittentts":
        return json.dumps({
            "ok": True,
            "voices": _tts_model.available_voices,
            "engine": "kittentts"
        })
    elif _tts_available == "gtts":
        return json.dumps({
            "ok": True,
            "voices": ["default"],
            "engine": "gtts"
        })
    else:
        return json.dumps({
            "error": "No TTS available",
            "available_voices": [],
            "engines": ["kittentts", "gtts"]
        })