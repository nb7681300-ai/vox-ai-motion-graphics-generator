#!/usr/bin/env python3
"""
HTML/CSS Animation clip generator.
Records each scene from input/animation.html via Playwright, then re-encodes to MP4.

Requirements:
    pip install playwright
    playwright install chromium
    ffmpeg on PATH
"""

import json
import os
import subprocess
import sys
import time

# ---------------------------------------------------------------------------
# Aspect dimensions
# ---------------------------------------------------------------------------
ASPECT_DIMS = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1":  (1080, 1080),
    "4:3":  (1440, 1080),
    "3:4":  (1080, 1440),
}

# Record at half-res, ffmpeg upscales — much faster Playwright recording
RECORD_SCALE = 0.5



def ff_convert(webm: str, dest: str, w: int, h: int, duration: int):
    """Re-encode Playwright WebM to H.264 MP4 at target resolution."""
    subprocess.run([
        "ffmpeg", "-y", "-i", webm,
        "-vf", f"scale={w}:{h}:flags=lanczos",
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        dest,
    ], check=True, stderr=subprocess.DEVNULL)


def run(project_dir: str, default_clip_dur: int = 8):
    bpath = os.path.join(project_dir, "beats.json")
    with open(bpath, encoding="utf-8") as f:
        doc = json.load(f)

    aspect = doc.get("aspect", "16:9")
    w, h = ASPECT_DIMS.get(aspect, (1920, 1080))
    rw, rh = int(w * RECORD_SCALE), int(h * RECORD_SCALE)

    clip_dir = os.path.join(project_dir, "clips")
    tmp_html = os.path.join(project_dir, "_html_clips")
    tmp_webm = os.path.join(project_dir, "_webm")
    for d in (clip_dir, tmp_html, tmp_webm):
        os.makedirs(d, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed.")
        print("Run:  pip install playwright && playwright install chromium")
        sys.exit(1)

    with sync_playwright() as pw:
        # Launch with flags to ensure CSS animations play in headless mode
        browser = pw.chromium.launch(
            args=[
                "--autoplay-policy=no-user-gesture-required",
                "--disable-features=ReducedMotionOnInteract",
                "--force-prefers-reduced-motion=no-preference",
                "--enable-precise-memory-info",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
            ]
        )

        # Handle pre-built HTML animation document mode (animation.html)
        anim_html = doc.get("animation_html_file")
        if not anim_html:
            default_anim = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "input", "animation.html"))
            if os.path.exists(default_anim) and doc.get("mode") == "animation_html":
                anim_html = default_anim

        if anim_html and os.path.exists(anim_html):
            with open(anim_html, "r", encoding="utf-8") as f:
                anim_source = f.read()

            print(f"[html_clips] Recording from animation.html: {anim_html}")

            for beat in doc["beats"]:
                key = str(beat["id"])
                dest = os.path.join(clip_dir, f"clip_{key}.mp4")
                # Skip existing clip ONLY if it's larger than 50KB (valid video frame content)
                if os.path.exists(dest) and os.path.getsize(dest) > 50000:
                    beat["clip_path"] = dest
                    print(f"[{key}] skip (valid clip exists: {dest})")
                    continue

                dur = max(3.0, float(beat.get("dur", 8)))
                scene_id = beat.get("scene_id", f"scene{key}")
                idx = int(key) - 1

                # Build a standalone per-scene HTML — scene is pre-activated via injected CSS
                # and a synchronous inline script so animations start from frame 0
                inject_css = f"""
<style id="__scene_inject__">
  html, body {{ margin:0!important; padding:0!important; width:100%!important; height:100%!important; overflow:hidden!important; background:#111!important; }}
  #stage-wrap  {{ padding:0!important; max-width:100%!important; margin:0!important; width:100vw!important; height:100vh!important; }}
  #frame       {{ border:none!important; border-radius:0!important;
                  width:100vw!important; height:100vh!important;
                  aspect-ratio:unset!important; position:relative!important; }}
  #topbar, #controls, #caption {{ display:none!important; }}
  .scene       {{ display:block!important; opacity:0!important; visibility:hidden!important; transition:none!important; z-index:1!important; }}
  /* Keep scene 1 slightly visible (opacity 0.001) so browser SVG renderer retains <defs> gradients (#bgDusk, #bgNight) */
  #scene1, #scene-1, #scene_1, .scene:first-of-type {{ display:block!important; opacity:0.001!important; visibility:visible!important; z-index:0!important; pointer-events:none!important; }}
  /* Target scene — match any ID convention (scene1, scene-1, scene_1) or fallback to index */
  #{scene_id}, #scene-{key}, #scene_{key}, .scene:nth-of-type({key}) {{ display:block!important; opacity:1!important; visibility:visible!important; z-index:100!important; }}
  /* force animations to play — override prefers-reduced-motion */
  @media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
      animation-duration:   revert !important;
      animation-delay:      revert !important;
      transition-duration:  revert !important;
    }}
  }}
</style>"""

                inject_script = f"""
<script id="__scene_init__">
  // Run synchronously before page renders to freeze JS timeline loop
  (function() {{
    window.requestAnimationFrame = function() {{ return 0; }};
    function init() {{
      if (window.rafId) {{ cancelAnimationFrame(window.rafId); window.rafId = null; }}
      if (window.animationFrameId) {{ cancelAnimationFrame(window.animationFrameId); window.animationFrameId = null; }}
      if (typeof window.paused !== 'undefined') window.paused = true;

      // Deactivate all scenes except ours
      var allScenes = document.querySelectorAll('.scene');
      allScenes.forEach(function(s) {{
        s.classList.remove('active');
      }});

      var sc = document.getElementById('{scene_id}') ||
               document.getElementById('scene-{key}') ||
               document.getElementById('scene_{key}') ||
               allScenes[{idx}];
      if (!sc) return;
      sc.classList.add('active');

      // Collect ALL animated descendants
      var animated = Array.from(sc.querySelectorAll('*'));
      // Reset animations in one batch, single reflow, then re-enable
      animated.forEach(function(n) {{ n.style.animation = 'none'; }});
      void sc.offsetWidth;  // single reflow
      animated.forEach(function(n) {{
        n.style.animation = '';
        n.style.animationPlayState = 'running';
      }});
    }}
    if (document.readyState === 'loading') {{
      document.addEventListener('DOMContentLoaded', init);
    }} else {{
      init();
    }}
  }})();
</script>"""

                # Inject before </head>
                standalone_html = anim_source.replace('</head>', inject_css + inject_script + '</head>', 1)

                # Write to a temp file that browser can load via file://
                scene_html_path = os.path.join(tmp_html, f"scene_{scene_id}.html")
                with open(scene_html_path, "w", encoding="utf-8") as f:
                    f.write(standalone_html)

                scene_url = "file:///" + scene_html_path.replace("\\", "/").lstrip("/")
                print(f"[{key}] Recording {scene_id} ({dur}s)...")

                context = browser.new_context(
                    viewport={"width": rw, "height": rh},
                    record_video_dir=tmp_webm,
                    record_video_size={"width": rw, "height": rh},
                )
                page = context.new_page()

                # Load the per-scene HTML — scene already active in CSS, animations start immediately
                page.goto(scene_url)
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=8000)
                except Exception:
                    pass

                # Small grace period to let first frames render before we start timing
                time.sleep(0.5)

                # Let the animation play for the full scene duration
                time.sleep(dur)

                video = page.video
                context.close()

                webm_path = video.path() if video else None
                if not webm_path or not os.path.exists(webm_path):
                    webms = [os.path.join(tmp_webm, f) for f in os.listdir(tmp_webm) if f.endswith(".webm")]
                    webm_path = max(webms, key=os.path.getmtime) if webms else None

                if webm_path:
                    # Trim 0.5s loading head, keep exactly dur seconds
                    ff_convert(webm_path, dest, w, h, dur)
                    try:
                        os.remove(webm_path)
                    except Exception:
                        pass
                    beat["clip_path"] = dest
                    print(f"[{key}] saved  {dest}")

            browser.close()
            with open(bpath, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            print(f"Updated {bpath}")
            return

        # Only animation_html mode is supported
        browser.close()
        print("ERROR: beats.json missing 'animation_html_file'. "
              "Only animation_html mode is supported.\n"
              "Run: python scripts/run_pipeline.py --content input/content.md "
              "--animation input/animation.html --project <out_dir>")
        sys.exit(1)

    with open(bpath, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"Updated {bpath}")


if __name__ == "__main__":
    proj = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "out", "demo")
    run(os.path.abspath(proj))
