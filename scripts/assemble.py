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

VIE_HASHTAG_STOPWORDS = {
    "và", "va", "của", "cua", "cho", "những", "nhung", "một", "mot",
    "là", "la", "với", "voi", "như", "nhu", "trong", "tren", "có", "co",
    "mà", "ma", "này", "nay", "đã", "da", "nếu", "neu", "vì", "vi",
    "hay", "hoặc", "hoac", "như", "nhu", "để", "de", "không", "khong",
    "mình", "minh", "họ", "ho", "còn", "con", "vẫn", "van", "đang", "dang",
}

UNWANTED_HASHTAGS = {
    "kichbanlong", "kichban", "long", "video", "hoathinh", "nguoique",
    "luong", "lua", "dong", "thuyet", "truyen"
}


def _normalize_for_hashtag(text: str) -> str:
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    text = re.sub(
        r"\b\d+(?:[.,]\d+)?\s*(?:giay|giây|s|sec|secs|second|seconds|phut|phút|min|mins|minute|minutes)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"[^A-Za-z0-9\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokenize_for_hashtag(text: str) -> list[str]:
    text = _normalize_for_hashtag(text).lower()
    tokens = [t for t in re.findall(r"[A-Za-z0-9]+", text) if t and t not in VIE_HASHTAG_STOPWORDS]
    return tokens


def _make_hashtag(words: list[str]) -> str | None:
    if not words:
        return None
    return "#" + "".join(w.capitalize() for w in words if w)


def _story_title_for_hashtag(topic: str) -> str:
    title = re.sub(r"\s*\([^)]*\)\s*$", "", topic or "").strip()
    prefix_match = re.match(
        r"^(?:kịch\s+bản|video|hoạt\s+hình|người\s+que|lồng\s+tiếng|ngụ\s+ngôn|thần\s+thoại|truyện|tập|phần\s+\d+|\s)+:\s*",
        title,
        re.IGNORECASE,
    )
    if prefix_match:
        title = title[prefix_match.end():].strip()
    for separator in ("—", "–", " - "):
        if separator in title:
            title = title.split(separator, 1)[0].strip()
    return title


def _message_hashtag(description: str) -> str | None:
    first_clause = re.split(r"[,;.!?]", description, maxsplit=1)[0]
    words = re.findall(r"[A-Za-z0-9]+", _normalize_for_hashtag(first_clause))
    return _make_hashtag(words)


def _build_caption_hashtags(doc: dict, beats: list[dict]) -> str:
    topic = doc.get("topic", "").strip()
    description = doc.get("description", "").strip() or doc.get("message", "").strip()
    origin = (doc.get("origin", "") or doc.get("source", "")).strip()

    story_title = _story_title_for_hashtag(topic)
    story_title_tokens = re.findall(r"[A-Za-z0-9]+", _normalize_for_hashtag(story_title))
    if not story_title_tokens and beats:
        story_title_tokens = re.findall(
            r"[A-Za-z0-9]+",
            _normalize_for_hashtag(beats[0].get("title") or beats[0].get("scene", "")),
        )

    message_tag = _message_hashtag(description) if description else None
    candidates = []

    for beat in beats[:3]:
        title = beat.get("title") or beat.get("scene") or beat.get("narration", "")
        if title:
            beat_tokens = _tokenize_for_hashtag(title)
            if beat_tokens:
                candidates.append(beat_tokens[:3])

    tags = []
    story_tag = _make_hashtag(story_title_tokens)
    if story_tag:
        tags.append(story_tag)
    origin_tag = _make_hashtag(re.findall(r"[A-Za-z0-9]+", _normalize_for_hashtag(origin)))
    tags.append(origin_tag or "#NguonGocCuaCauChuyen")
    if message_tag:
        tags.append(message_tag)

    if len(tags) < 3:
        for token_group in candidates:
            tag = _make_hashtag(token_group)
            if tag:
                tag_key = tag[1:].lower()
                if tag_key not in UNWANTED_HASHTAGS and tag.lower() not in {item.lower() for item in tags}:
                    tags.append(tag)
            if len(tags) >= 3:
                break

    if len(tags) < 3:
        extra_tokens = []
        for text in (description,):
            extra_tokens.extend(_tokenize_for_hashtag(text))
        for token in extra_tokens:
            tag = _make_hashtag([token])
            if tag:
                tag_key = tag[1:].lower()
                if tag_key not in UNWANTED_HASHTAGS and tag.lower() not in {item.lower() for item in tags}:
                    tags.append(tag)
            if len(tags) >= 3:
                break

    while len(tags) < 3:
        tags.append("#CauChuyen")

    tags.append("#CauChuyen_YNghia")
    return ", ".join(tags)

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
    import re as _re
    
    # 1. Strip trailing parentheses or brackets first
    name_part = _re.sub(r'\s*\([^)]*\)\s*$', '', raw_topic).strip()
    name_part = _re.sub(r'\s*\[[^\]]*\]\s*$', '', name_part).strip()
    
    # 2. Strip prefix pattern like "KỊCH BẢN VIDEO HOẠT HÌNH NGƯỜI QUE: "
    prefix_match = _re.match(
        r'^(?:kịch\s+bản|video|hoạt\s+hình|người\s+que|lồng\s+tiếng|ngụ\s+ngôn|thần\s+thoại|truyện|tập|phần\s+\d+|\s)+:\s*',
        name_part,
        _re.IGNORECASE
    )
    if prefix_match:
        name_part = name_part[prefix_match.end():].strip()
        
    # 3. Strip moral/meaning suffixes (after —, –, -, or ()
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

    # Ensure transparent.png exists in tmp
    transparent_png = os.path.join(tmp, "transparent.png")
    if not os.path.exists(transparent_png):
        from PIL import Image as _Image
        _Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(transparent_png)

    seg_files = []
    for i, s in enumerate(segs):
        out = os.path.join(tmp, f"seg_{i:02d}.mp4")
        cd = probe_dur(s["clip"])
        factor = s["dur"] / cd if cd > 0 else 1.0
        pre = f"setpts={factor:.4f}*PTS," if factor > 1.02 else ""

        beat = s["beat"]
        beat_caps = _build_karaoke_overlays_for_beat(beat, s["dur"], tmp, W, H, beat.get("id", i + 1))

        # Build subtitle list for concat demuxer
        sub_list_txt = os.path.join(tmp, f"sub_list_{i:02d}.txt")
        with open(sub_list_txt, "w", encoding="utf-8") as f_sub:
            curr_t = 0.0
            last_png = "transparent.png"
            for c_png, s_start, s_end in beat_caps:
                s_start = max(0.0, s_start)
                s_end = max(s_start, s_end)
                c_name = os.path.basename(c_png)
                
                # Gap before this word
                if s_start > curr_t:
                    gap_dur = s_start - curr_t
                    f_sub.write(f"file 'transparent.png'\nduration {gap_dur:.3f}\n")
                    curr_t = s_start
                
                # The word itself
                word_dur = s_end - s_start
                f_sub.write(f"file '{c_name}'\nduration {word_dur:.3f}\n")
                curr_t = s_end
                last_png = c_name
                
            # Gap at the end
            if s["dur"] > curr_t:
                gap_dur = s["dur"] - curr_t
                f_sub.write(f"file 'transparent.png'\nduration {gap_dur:.3f}\n")
                last_png = "transparent.png"
                
            # Repeat last file for the duration bug
            f_sub.write(f"file '{last_png}'\n")

        inputs = [
            "-i", s["clip"],
            "-f", "concat", "-safe", "0", "-i", sub_list_txt
        ]
        
        full_fc = (
            f"[0:v]{pre}split[s0][s1];"
            f"[s0]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"boxblur=26:2,eq=brightness=-0.05[bg];"
            f"[s1]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,fps={FPS},"
            f"tpad=stop_mode=clone:stop_duration=1[v0];"
            f"[v0][1:v]overlay=0:0[vfinal]"
        )

        ff([*inputs, "-an", "-filter_complex", full_fc, "-map", "[vfinal]", "-t", f"{s['dur']}",
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
    # Normalize capitalization: if description is ALL CAPS, convert to standard sentence case
    if description.isupper():
        description = description.lower()
        sentences = _re.split(r'(\s*[\.\?!]\s*)', description)
        for idx in range(0, len(sentences), 2):
            if sentences[idx]:
                sentences[idx] = sentences[idx][0].upper() + sentences[idx][1:]
        description = "".join(sentences)

    hashtags = _build_caption_hashtags(doc, beats)
    with open(caption_path, "w", encoding="utf-8") as cap_f:
        cap_f.write(description + "\n")
        cap_f.write(hashtags + "\n")
    print(f"Caption written  -> {caption_path}")

    print(f"Assembly finished -> {final_mp4}")


if __name__ == "__main__":
    proj = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "out", "demo")
    run(os.path.abspath(proj))
