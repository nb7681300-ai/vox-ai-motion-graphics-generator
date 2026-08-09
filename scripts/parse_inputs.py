#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parser for input/content.md and input/animation.html
Extracts scene titles, timings, narrations, and maps to beats.json structure.
"""

import json
import os
import re
import sys


def parse_content_md(content_path: str) -> dict:
    if not os.path.exists(content_path):
        raise FileNotFoundError(f"Content file not found: {content_path}")

    with open(content_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Auto-unescape backslash-escaped Markdown characters
    # (common when AI output is copy-pasted with \#, \*\*, \---, \> etc.)
    text = re.sub(r'\\([#*\->`|!\[\]()_~{}])', r'\1', text)

    # Extract overall title from H1 (single #)
    h1_match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
    if h1_match:
        full_topic = h1_match.group(1).strip()
    else:
        full_topic = text.splitlines()[0].lstrip("#").strip() if text else "Video"

    # Extract description from any bold "Thông điệp..." field or blockquote > "..."
    desc_match = re.search(
        r'\*\*Th\u00f4ng \u0111i\u1ec7p[^*]*\*\*\s*[:\.]?\s*["\u201c]?([^"\u201d\n]{10,})["\u201d]?',
        text, re.IGNORECASE
    )
    if desc_match:
        description = desc_match.group(1).strip().strip('"\u201c\u201d\u2018\u2019').strip('|').strip()
    else:
        # Fallback: look for blockquote > "..." in text
        bq_match = re.search(r'>\s*["\u201c]?([^"\u201d\n]{15,})["\u201d]?', text)
        description = bq_match.group(1).strip().strip('"\u201c\u201d\u2018\u2019').strip('|').strip() if bq_match else ""

    # Split text into scene sections (flexible to any title/timing order on "##/###/#### Cảnh N" lines)
    scene_pattern = re.compile(
        r'^#{2,4}\s*(?:C[\u1EA3\u1EA2A]NH|C\u1EA3nh|Scene)\s*(\d+)([^\n]*)',
        re.IGNORECASE | re.MULTILINE
    )

    matches = list(scene_pattern.finditer(text))
    beats = []

    def parse_sec(time_str: str) -> float:
        time_str = time_str.strip().rstrip('s').strip()
        if ":" in time_str:
            parts = time_str.split(":")
            return float(parts[0]) * 60 + float(parts[1])
        return float(time_str)

    def is_markdown_field_line(line: str) -> bool:
        text = line.strip()
        if not text.startswith("**") or ":" not in text:
            return False
        return not re.match(r'^\*\*(?:L\u1eddi b\u00ecnh|voice-over|VO)[^*]*\*\*\s*:?', text, re.IGNORECASE)

    if matches:
        for i, match in enumerate(matches):
            scene_num = int(match.group(1))
            rest_of_line = match.group(2).strip()

            # Extract timing from (start - end) bracket if present anywhere on the line
            time_match = re.search(
                r'\(\s*([\d:.]+s?)\s*[-\u2013\u2014]\s*([\d:.]+s?)[^)]*\)',
                rest_of_line
            )
            if time_match:
                t_start = parse_sec(time_match.group(1))
                t_end   = parse_sec(time_match.group(2))
                dur = round(max(2.0, t_end - t_start), 2)
                # Remove timing bracket to leave clean title
                raw_title = rest_of_line.replace(time_match.group(0), "").strip(" :—-")
            else:
                t_start = 0.0
                dur = 8.0
                raw_title = rest_of_line.strip(" :—-")

            scene_title = raw_title if raw_title else f"Scene {scene_num}"

            # Slice section content up to the next scene or EOF
            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            sec_content = text[start_pos:end_pos]

            # Extract voice-over narration text
            narr_lines = []
            loi_binh_match = re.search(
                r'\*\*(?:L\u1eddi b\u00ecnh|voice-over|VO)[^*]*\*\*\s*:?\s*',
                sec_content, re.IGNORECASE
            )
            if loi_binh_match:
                sub = sec_content[loi_binh_match.end():]
                for line in sub.splitlines():
                    line_str = line.strip()
                    if not line_str:
                        continue
                    
                    # Skip metadata/timing lines like (~13s), (10s thoại, 80%):
                    clean_test = re.sub(r'[\d\s\(\)~\-%\.:,≈\u2013\u2014\u2248\u224b|/]', '', line_str).lower()
                    for w in ('thoại', 'thoai', 'giây', 'giay', 'cảnh', 'canh', 's'):
                        clean_test = clean_test.replace(w, '')
                    if len(clean_test) == 0:
                        continue

                    if line_str.startswith(">"):
                        cleaned = line_str.lstrip(">").strip()
                        if cleaned:
                            narr_lines.append(cleaned)
                    elif line_str.startswith("- **") or line_str.startswith("#") or is_markdown_field_line(line_str):
                        # Stop if hit next field or header
                        break
                    elif line_str and not line_str.startswith("-"):
                        cleaned = line_str.strip('"“\'”')
                        if cleaned:
                            narr_lines.append(cleaned)
                        break
                
                # If no blockquote lines (> ...), take first line after label
                if not narr_lines and sub.strip():
                    for line in sub.splitlines():
                        first_line = line.strip()
                        if not first_line:
                            continue
                        # Skip metadata/timing lines
                        clean_test = re.sub(r'[\d\s\(\)~\-%\.:,≈\u2013\u2014\u2248\u224b|/]', '', first_line).lower()
                        for w in ('thoại', 'thoai', 'giây', 'giay', 'cảnh', 'canh', 's'):
                            clean_test = clean_test.replace(w, '')
                        if len(clean_test) == 0:
                            continue
                        if first_line.startswith("#") or is_markdown_field_line(first_line):
                            break
                        if not first_line.startswith("- **"):
                            cleaned = first_line.strip('"“\'”')
                            if cleaned:
                                narr_lines.append(cleaned)
                        break

            narr = " ".join(narr_lines).strip()
            if (narr.startswith('"') and narr.endswith('"')) or (narr.startswith('“') and narr.endswith('”')):
                narr = narr[1:-1].strip()

            beats.append({
                "id": scene_num,
                "scene_id": f"scene{scene_num}",
                "title": scene_title.upper(),
                "narration": narr,
                "start": t_start,
                "dur": dur,
                "camera_move": "static",
            })
    else:
        # Fallback: Try Markdown table format with intelligent header column mapping
        lines = text.splitlines()
        header_idx = -1
        col_map = {}

        for i, line in enumerate(lines):
            line_s = line.strip()
            if line_s.startswith("|") and line_s.endswith("|"):
                cells = [c.strip().lower() for c in line_s.split("|")[1:-1]]
                has_scene_col = any("cảnh" in c or "scene" in c or c == "#" or "stt" in c for c in cells)
                has_narr_col = any(kw in c for c in cells for kw in ["lời bình", "voice", "thuyết minh", "lời thoại"])
                if len(cells) >= 3 and has_scene_col and has_narr_col:
                    header_idx = i
                    for idx, c in enumerate(cells):
                        if any(kw in c for kw in ["lời bình", "voice", "thuyết minh", "lời thoại"]):
                            col_map["narr"] = idx
                        elif any(kw in c for kw in ["thời lượng", "thời gian", "duration", "time"]):
                            col_map["time"] = idx
                        elif any(kw in c for kw in ["tên cảnh", "tên", "title"]):
                            col_map["title"] = idx
                        elif any(kw in c for kw in ["hình ảnh", "nội dung", "mô tả", "visual", "image"]):
                            col_map["desc"] = idx
                        elif any(kw in c for kw in ["cảnh", "scene", "stt"]) or c == "#":
                            col_map["num"] = idx
                    break

        if header_idx != -1:
            for line in lines[header_idx + 1:]:
                line_s = line.strip()
                if line_s.startswith("|") and line_s.endswith("|"):
                    cells = [c.strip() for c in line_s.split("|")[1:-1]]
                    if not cells or "---" in cells[0]:
                        continue
                    num_m = re.search(r'(\d+)', cells[0])
                    if num_m:
                        s_num = int(num_m.group(1))
                        narr_idx = col_map.get("narr", -1)
                        raw_narr = cells[narr_idx] if 0 <= narr_idx < len(cells) else ""

                        # Clean timing notes in parentheses e.g. (≈12s thoại / 14s cảnh)
                        narr = re.sub(r'\(\s*[\approx~]?\s*[\d:.]+s?\s*thoại[^\)]*\)', '', raw_narr, flags=re.IGNORECASE)
                        narr = re.sub(r'\([^\)]*cảnh[^\)]*\)', '', narr, flags=re.IGNORECASE)
                        narr = narr.strip(' *\"“\'”\t\n\r')

                        title_idx = col_map.get("title", col_map.get("desc", 0))
                        raw_title = cells[title_idx].strip("*") if 0 <= title_idx < len(cells) else f"Scene {s_num}"

                        t_idx = col_map.get("time", 1)
                        t_range = cells[t_idx] if 0 <= t_idx < len(cells) else ""

                        tm = re.search(r'([\d:.]+s?)\s*[-\u2013\u2014]\s*([\d:.]+s?)', t_range)
                        if tm:
                            t_start = parse_sec(tm.group(1))
                            t_end = parse_sec(tm.group(2))
                            dur = round(max(2.0, t_end - t_start), 2)
                        else:
                            t_start = 0.0
                            dur = 8.0

                        beats.append({
                            "id": s_num,
                            "scene_id": f"scene{s_num}",
                            "title": raw_title.upper(),
                            "narration": narr,
                            "start": t_start,
                            "dur": dur,
                            "camera_move": "static",
                        })

    return {
        "topic": full_topic,
        "description": description,
        "language": "vi",
        "aspect": "16:9",
        "theme": "stickman",
        "music": "acoustic light BGM",
        "beats": beats
    }


def parse_animation_html(html_path: str) -> list:
    """Extract scene objects defined in animation.html JS if present."""
    if not os.path.exists(html_path):
        return []

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Look for const scenes = [...]
    js_match = re.search(r'const\s+scenes\s*=\s*(\[.*?\]);', html, re.DOTALL)
    if not js_match:
        return []

    try:
        # Convert JS object keys to valid JSON format for parsing
        raw_js = js_match.group(1)
        raw_json = re.sub(r'([{,]\s*)([a-zA-Z0-9_]+)\s*:', r'\1"\2":', raw_js)
        # Handle trailing commas
        raw_json = re.sub(r',\s*([\]}])', r'\1', raw_json)
        return json.loads(raw_json)
    except Exception:
        return []


def build_beats_doc(content_path: str, animation_path: str, out_dir: str) -> str:
    doc = parse_content_md(content_path)
    js_scenes = parse_animation_html(animation_path)

    # Merge narration or timing from animation.html if missing in content.md
    if js_scenes:
        for idx, beat in enumerate(doc["beats"]):
            if idx < len(js_scenes):
                js_item = js_scenes[idx]
                if not beat["narration"] and js_item.get("text"):
                    beat["narration"] = js_item["text"]

    if not doc["beats"]:
        raise ValueError(
            f"No scenes parsed from '{content_path}'. "
            "Please make sure content.md contains scene headers (e.g. '### CẢNH 1') or a storyboard Markdown table."
        )

    doc["mode"] = "animation_html"
    doc["animation_html_file"] = os.path.abspath(animation_path)
    doc["content_file"] = os.path.abspath(content_path)

    os.makedirs(out_dir, exist_ok=True)
    bpath = os.path.join(out_dir, "beats.json")
    with open(bpath, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)

    print(f"[parse_input] Saved beat map ({len(doc['beats'])} scenes) -> {bpath}")
    return bpath


if __name__ == "__main__":
    c_path = sys.argv[1] if len(sys.argv) > 1 else "./input/content.md"
    a_path = sys.argv[2] if len(sys.argv) > 2 else "./input/animation.html"
    o_dir = sys.argv[3] if len(sys.argv) > 3 else "./out/chiec-riu-vang"
    build_beats_doc(c_path, a_path, o_dir)
