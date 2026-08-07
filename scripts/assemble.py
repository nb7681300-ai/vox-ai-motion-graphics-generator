#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, io
if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
"""
Assembly stage (ffmpeg): multi-shot clips + per-beat narration + music -> final.mp4
"""
import json
import os
import re
import subprocess
import unicodedata

import text_overlay

FPS, TAIL = 24, 0.5
WATERMARK = ""  # Watermark disabled
RES = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}


def _slugify(text: str) -> str:
    """Convert a Vietnamese/Unicode title to an ASCII hyphen-slug.
    E.g. 'Hòn Đá Trên Đường' -> 'hon-da-tren-duong'
    """
    # Normalise to NFD so diacritics become separate combining chars
    nfd = unicodedata.normalize("NFD", text)
    # Drop combining diacritical marks (category Mn)
    ascii_str = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    # Special Vietnamese replacements that survive NFD (Đ/đ)
    ascii_str = ascii_str.replace("Đ", "D").replace("đ", "d")
    # Lowercase, replace non-alphanumeric runs with hyphens
    ascii_str = ascii_str.lower()
    ascii_str = re.sub(r"[^a-z0-9]+", "-", ascii_str)
    return ascii_str.strip("-")

def ff(args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)

def probe_dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    try:
        return float(out.strip())
    except ValueError:
        return 0.0


def shots_of(beat):
    if beat.get("shots"):
        for s in beat["shots"]:
            yield s
    else:
        yield beat


def _restore_punctuation(words, narration_text):
    """
    Re-attach punctuation stripped by Whisper/Edge-TTS to word-level timestamps.
    Aligns word list sequentially against narration_text and appends any
    punctuation/trailing characters that follow each word in the source text.
    Handles standalone punctuation tokens like '—' gracefully without overriding spoken words.
    """
    import re
    tokens = re.findall(r"\S+", narration_text)
    if not tokens:
        return words

    result = []
    tok_idx = 0
    for w_info in words:
        raw = w_info.get("word", "")
        raw_core = raw.strip(".,!?;:\"'—–…()[]").lower()
        if not raw_core:
            result.append(w_info)
            continue

        matched_tok = None
        matched_ti = None
        search_start = tok_idx
        for ti in range(search_start, min(search_start + 5, len(tokens))):
            tok = tokens[ti]
            tok_core = tok.strip(".,!?;:\"'—–…()[]").lower()
            if not tok_core:
                # Standalone punctuation token (e.g. "—"), do not match as core word
                continue
            if tok_core == raw_core or (len(raw_core) >= 3 and raw_core in tok_core) or (len(tok_core) >= 3 and tok_core in raw_core):
                matched_tok = tok
                matched_ti = ti
                break

        if matched_tok is not None:
            # Check for any standalone punctuation tokens between tok_idx and matched_ti
            extra_punct = ""
            for ti in range(tok_idx, matched_ti):
                p_core = tokens[ti].strip(".,!?;:\"'—–…()[]").lower()
                if not p_core:
                    extra_punct += " " + tokens[ti]

            # Attach trailing standalone punctuation (like "—") to previous word if available
            if extra_punct and result:
                result[-1]["word"] += extra_punct

            tok_idx = matched_ti + 1
            new_info = dict(w_info)
            new_info["word"] = matched_tok
            result.append(new_info)
        else:
            result.append(w_info)

    # Attach any trailing standalone punctuation tokens after the last word
    extra_punct = ""
    for ti in range(tok_idx, len(tokens)):
        p_core = tokens[ti].strip(".,!?;:\"'—–…()[]").lower()
        if not p_core:
            extra_punct += " " + tokens[ti]
    if extra_punct and result:
        result[-1]["word"] += extra_punct

    return result


def _build_karaoke_overlays_for_beat(beat, beat_dur, tmp, W, H, beat_id):
    cap_overlays = []
    t_text = beat.get("narration", "").strip()
    if not t_text:
        return []

    words = beat.get("words")
    if not words:
        raw_words = t_text.split()
        dur = float(beat.get("narration_dur", beat_dur))
        w_dur = dur / max(1, len(raw_words))
        words = [
            {"word": w, "start": round(idx * w_dur, 3), "end": round((idx + 1) * w_dur, 3)}
            for idx, w in enumerate(raw_words)
        ]
    else:
        # Whisper strips punctuation from word-level output — restore it
        words = _restore_punctuation(words, t_text)

    chunks = []
    curr = []
    curr_chars = 0
    for w_info in words:
        w_str = w_info["word"]
        if len(curr) >= 4 or (curr_chars + len(w_str) > 22 and len(curr) >= 2):
            chunks.append(curr)
            curr = [w_info]
            curr_chars = len(w_str)
        else:
            curr.append(w_info)
            curr_chars += len(w_str) + 1
    if curr:
        chunks.append(curr)

    cap_id = 0
    for c_idx, chunk in enumerate(chunks):
        word_strs = [item["word"] for item in chunk]
        for w_idx, w_info in enumerate(chunk):
            s_start = round(w_info["start"], 3)
            if w_idx + 1 < len(chunk):
                s_end = round(chunk[w_idx + 1]["start"], 3)
            elif c_idx + 1 < len(chunks):
                s_end = round(chunks[c_idx + 1][0]["start"], 3)
            else:
                s_end = round(max(w_info["end"], beat_dur), 3)

            if s_end <= s_start:
                s_end = s_start + 0.1

            c_png = os.path.join(tmp, f"karaoke_b{beat_id}_{cap_id:04d}.png")
            cap_id += 1
            text_overlay.render_karaoke_caption(word_strs, active_idx=w_idx, out_path=c_png, W=W, H=H)
            cap_overlays.append((c_png, s_start, s_end))

    return cap_overlays


def run(project_dir):
    with open(os.path.join(project_dir, "beats.json"), encoding="utf-8") as f:
        doc = json.load(f)
    beats = doc["beats"]
    W, H = RES.get(doc.get("aspect", "16:9"), (1920, 1080))
    wm_text = doc.get("watermark", WATERMARK)
    mix = doc.get("mix", {})
    music_vol = float(mix.get("music", 0.6))
    voice_vol = float(mix.get("voice", 1.25))
    tmp = os.path.join(project_dir, "_seg")
    os.makedirs(tmp, exist_ok=True)

    # Derive output filename from story title slug
    raw_topic = doc.get("topic", "").strip()
    # Strip prefix keywords (e.g. "KỊCH BẢN VIDEO HOẠT HÌNH NGƯỜI QUE: ")
    name_part = raw_topic
    colon_idx = raw_topic.find(":")
    if colon_idx != -1:
        name_part = raw_topic[colon_idx + 1:]
    # Strip moral/meaning suffixes (after —, –, -, or ()
    for sep in ("—", "–", " - ", "("):
        sep_idx = name_part.find(sep)
        if sep_idx != -1:
            name_part = name_part[:sep_idx]

    story_slug = _slugify(name_part.strip()) or "video"
    story_title = name_part.strip().title()
    # Build filesystem-safe Vietnamese title for the output filename
    # Only strip truly illegal filename characters (Windows: \ / : * ? " < > |)
    import re as _re
    story_filename = _re.sub(r'[\\/:*?"<>|]', '', story_title).strip() or story_slug

    segs = []
    beat_spans = []
    t = 0.0
    for beat in beats:
        beat_start = t
        shot_list = list(shots_of(beat))
        durs = [float(s.get("dur", 10)) for s in shot_list]
        need = float(beat.get("narration_dur", sum(durs))) + TAIL
        if sum(durs) < need:
            durs[-1] += need - sum(durs)
        for s, d in zip(shot_list, durs):
            clip_p = s.get("clip_path") or os.path.join(project_dir, "clips", f"clip_{beat['id']}.mp4")
            segs.append({"clip": clip_p, "dur": round(d, 2), "beat": beat})
            t += d
        beat_spans.append({"start": beat_start, "dur": round(t - beat_start, 2), "beat": beat})
    total = round(t, 2)

    seg_files = []
    for i, s in enumerate(segs):
        out = os.path.join(tmp, f"seg_{i:02d}.mp4")
        cd = probe_dur(s["clip"])
        factor = s["dur"] / cd if cd > 0 else 1.0
        pre = f"setpts={factor:.4f}*PTS," if factor > 1.02 else ""

        beat = s["beat"]
        beat_caps = _build_karaoke_overlays_for_beat(beat, s["dur"], tmp, W, H, beat.get("id", i + 1))

        inputs = ["-i", s["clip"]]
        fc_parts = [
            f"[0:v]{pre}split[s0][s1];"
            f"[s0]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"boxblur=26:2,eq=brightness=-0.05[bg];"
            f"[s1]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,fps={FPS},"
            f"tpad=stop_mode=clone:stop_duration=1[v0]"
        ]
        last_v = "[v0]"

        for c_idx, (c_png, s_start, s_end) in enumerate(beat_caps, start=1):
            inputs.extend(["-i", c_png])
            out_v = f"[vcap{c_idx}]"
            fc_parts.append(
                f"{last_v}[{c_idx}:v]overlay=0:0:enable='between(t,{s_start:.3f},{s_end:.3f})'{out_v}"
            )
            last_v = out_v

        full_fc = ";".join(fc_parts)
        ff([*inputs, "-an", "-filter_complex", full_fc, "-map", last_v, "-t", f"{s['dur']}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", out])
        seg_files.append(out)

    listf = os.path.join(tmp, "list.txt")
    with open(listf, "w", encoding="utf-8") as f:
        for s in seg_files:
            f.write(f"file '{s}'\n")

    v_concat = os.path.join(tmp, "v_concat.mp4")
    ff(["-f", "concat", "-safe", "0", "-i", listf, "-c", "copy", v_concat])

    narr_inputs, amix_filters = [], []
    for i, span in enumerate(beat_spans):
        b = span["beat"]
        apath = b.get("audio_path")
        if apath and os.path.exists(apath):
            idx = (len(narr_inputs) // 2) + 1
            narr_inputs.extend(["-i", apath])
            delay_ms = int(span["start"] * 1000)
            amix_filters.append(f"[{idx}:a]volume={voice_vol},adelay={delay_ms}|{delay_ms}[a{idx}];")

    bgm_path = os.path.join(project_dir, "audio", "bgm.mp3")
    has_bgm = os.path.exists(bgm_path)
    if has_bgm:
        bgm_idx = (len(narr_inputs) // 2) + 1
        narr_inputs.extend(["-stream_loop", "-1", "-i", bgm_path])

    filter_lines = []
    n_narr = len(amix_filters)
    if amix_filters:
        filter_lines.extend(amix_filters)
        ins = "".join(f"[a{i+1}]" for i in range(n_narr))
        filter_lines.append(f"{ins}amix=inputs={n_narr}:duration=longest:dropout_transition=0.5[vo];")
        if has_bgm:
            filter_lines.append(
                f"[{bgm_idx}:a]volume={music_vol}[bgm0];"
                f"[vo]asplit=2[vo1][vo2];"
                f"[bgm0][vo1]sidechaincompress=threshold=0.08:ratio=6:attack=15:release=250[bgm_ducked];"
                f"[vo2][bgm_ducked]amix=inputs=2:duration=longest:weights=1.2 0.7[aout]"
            )
        else:
            filter_lines.append(f"[vo]anull[aout]")
    elif has_bgm:
        filter_lines.append(f"[{bgm_idx}:a]volume={music_vol}[aout]")
    else:
        filter_lines.append("anullsrc=channel_layout=stereo:sample_rate=44100[aout]")

    full_filter = "".join(filter_lines)
    audio_full = os.path.join(tmp, "audio_mixed.m4a")
    ff(["-i", v_concat, *narr_inputs, "-filter_complex", full_filter,
        "-map", "[aout]", "-t", f"{total}", "-c:a", "aac", "-b:a", "192k", audio_full])

    wm_png = os.path.join(tmp, "watermark.png")
    text_overlay.render_watermark(wm_text, wm_png, W=W, H=H)

    final_mp4 = os.path.join(project_dir, f"{story_filename}.mp4")

    if os.path.exists(wm_png) and wm_text:
        ff(["-i", v_concat, "-i", wm_png, "-i", audio_full,
            "-filter_complex", "[0:v][1:v]overlay=0:0[vfinal]",
            "-map", "[vfinal]", "-map", "2:a", "-t", f"{total}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
            "-c:a", "copy", final_mp4])
    else:
        ff(["-i", v_concat, "-i", audio_full,
            "-map", "0:v", "-map", "1:a", "-t", f"{total}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
            "-c:a", "copy", final_mp4])

    # ── Write caption.txt ──────────────────────────────────────────────────
    description = doc.get("description", "").strip()
    if not description:
        # Fall back: use the message/thong-diep field if present in beats.json
        description = doc.get("message", "").strip()
    if not description:
        # Last resort: concatenate first-beat narration as a 1-sentence summary
        first_narr = beats[0].get("narration", "") if beats else ""
        description = first_narr[:180].rsplit(" ", 1)[0] + "…" if len(first_narr) > 180 else first_narr

    caption_path = os.path.join(project_dir, "caption.txt")
    with open(caption_path, "w", encoding="utf-8") as cap_f:
        cap_f.write(story_title + "\n")
        cap_f.write(description + "\n")
    print(f"Caption written  -> {caption_path}")

    print(f"Assembly finished -> {final_mp4}")


if __name__ == "__main__":
    proj = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "out", "demo")
    run(os.path.abspath(proj))
