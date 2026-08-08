#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, io
if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
"""
Main entry script for the new input workflow:
  content.md + animation.html -> beats.json -> audio -> clips -> assemble -> final.mp4

Usage:
  python scripts/run_pipeline.py --content input/content.md --animation input/animation.html

All paths can be relative to the project root or absolute.
The output folder is auto-named output/YYMMDD-HH-MM-Story Name by default.
"""

import argparse
import importlib
import os
import re
import sys
import time
import unicodedata

def _import(name: str):
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    return importlib.import_module(name)

def _banner(msg: str):
    bar = "=" * 60
    print(f"\n{bar}\n  {msg}\n{bar}")

def _strip_accents(text: str) -> str:
    """Remove Vietnamese diacritics and non-ASCII punctuation; keep spaces and casing.
    E.g. 'Hòn Đá Trên Đường' -> 'Hon Da Tren Duong'
         'Con Cáo — Bài Học' -> 'Con Cao Bai Hoc'
    """
    # Replace em/en dashes and other common non-ASCII punctuation with a space
    for ch in ("—", "–", "‒", "―", "·"):
        text = text.replace(ch, " ")
    # Handle Đ/đ which survive NFD decomposition unchanged
    text = text.replace("Đ", "D").replace("đ", "d")
    nfd = unicodedata.normalize("NFD", text)
    # Drop combining diacritical marks (category Mn)
    result = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    # Collapse multiple spaces that may result from dash replacement
    import re as _re
    return _re.sub(r"  +", " ", result).strip()

def _extract_story_name(content_path: str) -> str:
    """Read the first H1 line of content.md and return only the story title part.

    Given a line like:
      # KỊCH BẢN VIDEO HOẠT HÌNH NGƯỜI QUE: HOÀNG TỬ BÉ VÀ CON CÁO — BÀI HỌC VỀ SỰ CẢM HÓA (Tổng thời lượng: 120 giây)
    Returns:
      'Hoang Tu Be Va Con Cao'
    """
    try:
        import re as _re
        with open(content_path, "r", encoding="utf-8") as f:
            for line in f:
                # Auto-unescape backslash-escaped Markdown characters
                line = _re.sub(r'\\([#*\->`|!\[\]()_~{}])', r'\1', line)
                line = line.strip()
                if line.startswith("#"):
                    title = line.lstrip("#").strip()
                    
                    # 1. Strip trailing parentheses or brackets first
                    title = _re.sub(r'\s*\([^)]*\)\s*$', '', title).strip()
                    title = _re.sub(r'\s*\[[^\]]*\]\s*$', '', title).strip()
                    
                    # 2. Strip prefix pattern like "KỊCH BẢN VIDEO HOẠT HÌNH NGƯỜI QUE: "
                    prefix_match = _re.match(
                        r'^(?:kịch\s+bản|video|hoạt\s+hình|người\s+que|lồng\s+tiếng|ngụ\s+ngôn|thần\s+thoại|truyện|tập|phần\s+\d+|\s)+:\s*',
                        title,
                        _re.IGNORECASE
                    )
                    if prefix_match:
                        title = title[prefix_match.end():].strip()
                    
                    # 3. Strip moral/meaning suffixes (after —, –, -, or ()
                    for sep in ("—", "–", " - ", "("):
                        idx = title.find(sep)
                        if idx != -1:
                            title = title[:idx]
                            
                    title = title.strip()
                    return _strip_accents(title).title()
    except Exception:
        pass
    return "Video"


def _render_svg_thumbnail(svg_path: str, out_png: str, width: int = 1280, height: int = 720) -> bool:
    """
    Use Playwright headless Chromium to render a .svg file as PNG.
    Returns True on success, False on failure.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[thumbnail] playwright not installed — skipping SVG thumbnail render.")
        return False

    try:
        svg_url = "file:///" + svg_path.replace("\\", "/").lstrip("/")
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(svg_url)
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            page.screenshot(path=out_png, full_page=False)
            browser.close()
        print(f"[thumbnail] Rendered SVG thumbnail -> {out_png}")
        return True
    except Exception as e:
        print(f"[thumbnail] SVG thumbnail render failed: {e}")
        return False


def _render_html_thumbnail(html_path: str, out_png: str, width: int = 1280, height: int = 720) -> bool:
    """
    Use Playwright headless Chromium to screenshot thumbnail_generator.html
    and save it as a PNG. Returns True on success, False on failure.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[thumbnail] playwright not installed — skipping HTML thumbnail render.")
        return False

    try:
        html_url = "file:///" + html_path.replace("\\", "/").lstrip("/")
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(html_url)
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            import time as _time
            _time.sleep(1.0)  # Let CSS animations reach first keyframe
            page.screenshot(path=out_png, full_page=False)
            browser.close()
        print(f"[thumbnail] Rendered HTML thumbnail -> {out_png}")
        return True
    except Exception as e:
        print(f"[thumbnail] HTML thumbnail render failed: {e}")
        return False


def _open_file(filepath: str):
    """Open a file with system default application (Notepad/VSCode/TextEdit)."""
    import subprocess
    try:
        if sys.platform == "win32":
            os.startfile(filepath)
        elif sys.platform == "darwin":
            subprocess.run(["open", filepath])
        else:
            subprocess.run(["xdg-open", filepath])
    except Exception as e:
        print(f"  (Note: could not auto-open file: {e})")


def main():
    from datetime import datetime

    # Project root = parent of this script's directory
    _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _default_content   = os.path.join(_project_root, "input", "content.md")
    _default_animation = os.path.join(_project_root, "input", "animation.html")

    parser = argparse.ArgumentParser(
        description="Run end-to-end video generator from content.md and animation.html"
    )
    parser.add_argument("--content",   default=None, help="Path to script file (default: input/content.md)")
    parser.add_argument("--animation", default=None, help="Path to animated HTML file (default: input/animation.html)")
    parser.add_argument("--thumbnail", default=None, help="Path to thumbnail image file (default: input/thumbnail.png)")
    parser.add_argument("--project",   default=None, help="Output project directory (default: output/YYMMDD-HH-MM-Story Name)")
    parser.add_argument("--voice",     default="vi-VN-HoaiMyNeural", help="Voice for edge-tts (default: vi-VN-HoaiMyNeural)")
    parser.add_argument("--aspect",    default="16:9", choices=["16:9", "9:16", "1:1", "4:3"], help="Output aspect ratio")
    args = parser.parse_args()

    # Resolve paths: if user provided a relative path, resolve relative to cwd;
    # if not provided, use project-root-based defaults (always correct).
    def _resolve(arg_val, default_abs):
        if arg_val is None:
            return default_abs
        return os.path.abspath(arg_val)

    content_path   = _resolve(args.content,   _default_content)
    animation_path = _resolve(args.animation, _default_animation)

    # Build default project dir: YYMMDD-HH-MM-Story Name
    if args.project is None:
        dt_prefix  = datetime.now().strftime("%y%m%d-%H-%M")
        story_name = _extract_story_name(content_path)
        folder_name = f"{dt_prefix}-{story_name}" if story_name else dt_prefix
        _default_project = os.path.join(_project_root, "output", folder_name)
    else:
        _default_project = None

    project_dir    = _resolve(args.project,   _default_project)

    # Handle thumbnail: render from HTML generator or copy static file
    import shutil
    copied_thumbnail = None
    input_dir = os.path.dirname(content_path)
    os.makedirs(project_dir, exist_ok=True)

    if args.thumbnail:
        # Explicit --thumbnail flag: copy as-is
        user_thumb = os.path.abspath(args.thumbnail)
        if os.path.exists(user_thumb):
            dest_thumb = os.path.join(project_dir, "thumbnail" + os.path.splitext(user_thumb)[1])
            shutil.copy2(user_thumb, dest_thumb)
            copied_thumbnail = dest_thumb
    else:
        # Priority 1: static thumbnail image files (thumbnail.png / .jpg / .jpeg / .webp)
        for thumb_name in ("thumbnail.png", "thumbnail.jpg", "thumbnail.jpeg", "thumbnail.webp"):
            src_thumb = os.path.join(input_dir, thumb_name)
            if os.path.exists(src_thumb):
                dest_thumb = os.path.join(project_dir, os.path.basename(src_thumb))
                shutil.copy2(src_thumb, dest_thumb)
                copied_thumbnail = dest_thumb
                break

        # Priority 2: thumbnail_generator.svg -> render via Playwright
        if not copied_thumbnail:
            svg_gen = os.path.join(input_dir, "thumbnail_generator.svg")
            if os.path.exists(svg_gen):
                dest_thumb = os.path.join(project_dir, "thumbnail.png")
                if _render_svg_thumbnail(svg_gen, dest_thumb):
                    copied_thumbnail = dest_thumb

        # Priority 3: thumbnail_generator.html -> screenshot via Playwright
        if not copied_thumbnail:
            html_gen = os.path.join(input_dir, "thumbnail_generator.html")
            if os.path.exists(html_gen):
                dest_thumb = os.path.join(project_dir, "thumbnail.png")
                if _render_html_thumbnail(html_gen, dest_thumb):
                    copied_thumbnail = dest_thumb

    print(f"\n[NEW PIPELINE]")
    print(f"   Content   : {content_path}")
    print(f"   Animation : {animation_path}")
    print(f"   Project   : {project_dir}")
    if copied_thumbnail:
        print(f"   Thumbnail : {copied_thumbnail}")

    t_total = time.time()

    # 1. Parse inputs -> beats.json
    _banner("Stage 1 / 4 — Parsing content.md & animation.html")
    parser_mod = _import("parse_inputs")
    bpath = parser_mod.build_beats_doc(content_path, animation_path, project_dir)

    # Set custom voice if requested
    if args.voice:
        import json
        with open(bpath, "r", encoding="utf-8") as f:
            doc = json.load(f)
        doc["voice"] = {"voice_id": args.voice}
        doc["aspect"] = args.aspect
        with open(bpath, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

    # 2. Audio Stage (TTS narration + BGM)
    _banner("Stage 2 / 4 — Synthesizing narration TTS & BGM")
    audio_mod = _import("free_audio")
    audio_mod.run(project_dir)

    # 3. Clips Stage (Record scene clips from animation.html)
    _banner("Stage 3 / 4 — Recording scene clips with Playwright")
    clips_mod = _import("html_clips")
    clips_mod.run(project_dir)

    # 4. Assemble Stage (Mux video, audio, captions)
    _banner("Stage 4 / 4 — Final video assembly with ffmpeg")
    assemble_mod = _import("assemble")
    assemble_mod.run(project_dir)

    import glob
    mp4_files = glob.glob(os.path.join(project_dir, "*.mp4"))
    final_mp4 = mp4_files[0] if mp4_files else os.path.join(project_dir, "video.mp4")
    caption_txt = os.path.join(project_dir, "caption.txt")
    elapsed = time.time() - t_total
    print(f"\n{'='*60}")
    print(f"  SUCCESS! Final video generated in {elapsed:.1f}s")
    print(f"  Video    : {final_mp4}")
    if copied_thumbnail and os.path.exists(copied_thumbnail):
        print(f"  Thumbnail: {copied_thumbnail}")
    if os.path.exists(caption_txt):
        print(f"  Caption  : {caption_txt}")
        _open_file(caption_txt)
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
