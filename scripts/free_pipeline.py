#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
free_pipeline.py — Alias for run_pipeline.py (new animation_html pipeline).

This pipeline only supports the new workflow:
  content.md + animation.html → beats.json → TTS audio → clip recording → final.mp4

Usage:
  python scripts/free_pipeline.py --content ./input/content.md --animation ./input/animation.html --project out/my-project

For help:
  python scripts/free_pipeline.py --help
"""
import runpy
import sys
import os

# Forward to run_pipeline.py
_here = os.path.dirname(os.path.abspath(__file__))
sys.argv[0] = os.path.join(_here, "run_pipeline.py")
runpy.run_path(sys.argv[0], run_name="__main__")
