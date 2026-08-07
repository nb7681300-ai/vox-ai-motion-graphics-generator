#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, io
if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
"""
Free audio stage — replaces audio.py with zero-cost alternatives.

  • Narration  : Microsoft Edge TTS via `edge-tts` (free, no API key needed)
  • Background : Ambient drone generated with ffmpeg (or a bundled CC0 file)

Requirements:
    pip install edge-tts
    ffmpeg on PATH
"""

import asyncio
import json
import os
import shutil
import subprocess
import sys

# ---------------------------------------------------------------------------
# Edge TTS voice map  (language code → voice name)
# Full list: edge-tts --list-voices
# ---------------------------------------------------------------------------
VOICE_MAP = {
    "en":  "en-US-AriaNeural",
    "en-US": "en-US-AriaNeural",
    "en-GB": "en-GB-SoniaNeural",
    "vi":  "vi-VN-HoaiMyNeural",
    "vi-VN": "vi-VN-HoaiMyNeural",
    "zh":  "zh-CN-XiaoxiaoNeural",
    "ja":  "ja-JP-NanamiNeural",
    "ko":  "ko-KR-SunHiNeural",
    "fr":  "fr-FR-DeniseNeural",
    "de":  "de-DE-KatjaNeural",
    "es":  "es-ES-ElviraNeural",
    "pt":  "pt-BR-FranciscaNeural",
}
DEFAULT_VOICE = "vi-VN-HoaiMyNeural"

# ---------------------------------------------------------------------------
# Ambient BGM (A-minor pentatonic drone + echo, generated with ffmpeg)
# ---------------------------------------------------------------------------
# Frequencies:  A2  E3    A3    C4    E4    A4
BGM_FREQS = [110, 164.81, 220, 261.63, 329.63, 440]
BGM_AMPS  = [0.11, 0.07, 0.06,  0.05,  0.04, 0.03]

BGM_DURATION_S = 120   # seconds of generated ambient music
BGM_FADE_IN_S  = 4
BGM_FADE_OUT_S = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _probe_dur(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True,
    ).stdout
    try:
        return float(out.strip())
    except ValueError:
        return 0.0


async def _tts_async(text: str, voice: str, out_path: str, rate: str = "+0%", pitch: str = "+0Hz"):
    """Generate TTS audio with edge-tts and save to out_path, returning word timestamps with retries."""
    import edge_tts
    import asyncio

    for attempt in range(1, 4):
        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
            words = []
            audio_bytes = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_bytes.extend(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    t_start = round(chunk["offset"] / 10000000.0, 3)
                    t_dur = round(chunk["duration"] / 10000000.0, 3)
                    words.append({
                        "word": chunk["text"],
                        "start": t_start,
                        "end": round(t_start + t_dur, 3),
                    })
            if audio_bytes:
                with open(out_path, "wb") as f:
                    f.write(audio_bytes)
                return words
        except Exception as e:
            print(f"[tts-retry] attempt {attempt}/3 failed ({e}), retrying in 1.5s…")
            await asyncio.sleep(1.5)

    # Fallback to standard communicate without WordBoundary if WordBoundary stream fails
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(out_path)
    return []


def generate_tts(text: str, voice: str, out_path: str, rate: str = "+0%", pitch: str = "+0Hz"):
    return asyncio.run(_tts_async(text, voice, out_path, rate=rate, pitch=pitch))


def generate_ambient_bgm(out_path: str, duration: int = BGM_DURATION_S):
    """Generate a soft ambient drone using ffmpeg sine-wave synthesis."""
    expr = "+".join(f"{a}*sin(2*PI*{f}*t)" for f, a in zip(BGM_FREQS, BGM_AMPS))
    fade_out_start = max(0, duration - BGM_FADE_OUT_S)

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"aevalsrc='{expr}:sample_rate=44100:channel_layout=stereo'",
        "-af", (
            f"aecho=0.80:0.88:500|800|1200:0.35|0.22|0.12,"
            f"lowpass=f=900,"
            f"volume=0.60,"
            f"afade=t=in:ss=0:d={BGM_FADE_IN_S},"
            f"afade=t=out:st={fade_out_start}:d={BGM_FADE_OUT_S}"
        ),
        "-t", str(duration),
        "-c:a", "libmp3lame", "-q:a", "3",
        out_path,
    ]
    print("[bgm] generating ambient BGM with ffmpeg…")
    subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
    print(f"[bgm] saved  {out_path}")


def _resolve_voice(doc: dict) -> str:
    """Pick edge-tts voice from beats.json settings."""
    voice_cfg = doc.get("voice", {})
    vid = voice_cfg.get("voice_id", "")
    if vid:
        return vid
    lang = voice_cfg.get("language") or doc.get("language", "vi")
    return VOICE_MAP.get(lang, DEFAULT_VOICE)


def generate_tts_with_preset(text: str, voice: str, out_path: str, rate: str = "+0%", pitch: str = "+0Hz"):
    """Generate TTS audio with Edge-TTS, OpenAI TTS, or FPT.AI."""
    # 1. Check OpenAI API key for native high-quality male voice (onyx / echo)
    oa_key = os.environ.get("OPENAI_API_KEY")
    fpt_key = os.environ.get("FPT_API_KEY")

    if oa_key and voice in ("openai-male", "onyx", "echo"):
        import urllib.request
        model_voice = "onyx" if voice != "echo" else "echo"
        print(f"[tts] OpenAI TTS ({model_voice})…")
        req = urllib.request.Request(
            "https://api.openai.com/v1/audio/speech",
            data=json.dumps({
                "model": "tts-1",
                "input": text,
                "voice": model_voice,
            }).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {oa_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r, open(out_path, "wb") as f:
            f.write(r.read())
        return []

    if fpt_key and "fpt" in voice.lower():
        import urllib.request
        print(f"[tts] FPT.AI TTS (leminh - Nam Miền Bắc)…")
        req = urllib.request.Request(
            "https://api.fpt.ai/hcm/v5/v1",
            data=text.encode("utf-8"),
            headers={"api_key": fpt_key, "voice": "leminh", "speed": "0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.load(r)
            async_url = res.get("async")
            if async_url:
                time.sleep(3)
                urllib.request.urlretrieve(async_url, out_path)
                return []

    # 2. Native Edge-TTS Male Voice (vi-VN-NamMinhNeural) or specified voice
    target_voice = voice
    if voice in ("vi-male", "vi-north-male", "vi-VN-NamBac", "vi-north", "male"):
        target_voice = "vi-VN-NamMinhNeural"

    return generate_tts(text, target_voice, out_path, rate=rate, pitch=pitch)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(project_dir: str):
    bpath = os.path.join(project_dir, "beats.json")
    with open(bpath, encoding="utf-8") as f:
        doc = json.load(f)

    adir = os.path.join(project_dir, "audio")
    os.makedirs(adir, exist_ok=True)

    # Check edge-tts
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        print("ERROR: edge-tts not installed.\nRun: pip install edge-tts")
        sys.exit(1)

    voice = _resolve_voice(doc)
    speed = doc.get("voice", {}).get("speed", 1.0)
    pitch_str = doc.get("voice", {}).get("pitch", "-5Hz")
    # edge-tts rate syntax: "+10%" = 10% faster, "-10%" = slower
    pct = int((speed - 1.0) * 100)
    rate_str = f"+{pct}%" if pct >= 0 else f"{pct}%"

    print(f"Voice: {voice}  rate: {rate_str}  pitch: {pitch_str}")

    # ---- Narration per beat ------------------------------------------------
    for beat in doc["beats"]:
        narr = beat.get("narration", "").strip()
        if not narr:
            continue

        dest = os.path.join(adir, f"narr_{beat['id']}.mp3")
        if os.path.exists(dest) and beat.get("words"):
            print(f"[narr_{beat['id']}] reuse existing")
        else:
            print(f"[narr_{beat['id']}] generating TTS…")
            words = generate_tts_with_preset(narr, voice, dest, rate=rate_str, pitch=pitch_str)
            beat["words"] = words
            print(f"[narr_{beat['id']}] saved  {dest} ({len(words)} words)")

        beat["audio_path"] = dest
        beat["narration_dur"] = _probe_dur(dest)
        if beat["narration_dur"] > 0:
            target_dur = round(beat["narration_dur"] + 0.5, 2)
            if target_dur > beat.get("dur", 0):
                beat["dur"] = target_dur

    # ---- Background music (Disabled per user request) -----------------------
    bgm_dest = os.path.join(adir, "bgm.mp3")
    if os.path.exists(bgm_dest):
        try:
            os.remove(bgm_dest)
            print("[bgm] removed existing bgm.mp3 (BGM disabled)")
        except Exception:
            pass

    # ---- Write back --------------------------------------------------------
    with open(bpath, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"Updated {bpath}")


if __name__ == "__main__":
    proj = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "out", "demo")
    run(os.path.abspath(proj))
