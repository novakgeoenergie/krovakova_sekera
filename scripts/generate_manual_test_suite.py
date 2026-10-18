#!/usr/bin/env python3
"""
Manual Test Suite Generator for Křovákova Sekera (machete).

Generates real media files (MOV videos with burnt-in timecode, WAV tones)
and self-contained test project folders with both Adobe source files
(.prproj, .sesx) and pre-exported Avid AAF files for manual QA in
Avid Media Composer and Avid Pro Tools.
"""
from __future__ import annotations

import math
import shutil
import struct
import sys
import wave
from pathlib import Path

# Add src to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

import cv2
import numpy as np

from machete.exporters.aaf_core import export_project_to_aaf
from machete.parsers.prproj_extract import parse_prproj
from machete.parsers.sesx_extract import parse_sesx
from tests.fixture_factory import (
    generate_nested_seq_prproj,
    generate_sample_audition_sesx,
    generate_sample_tone_wav,
    generate_simple_cut_prproj,
)


def generate_video(
    output_path: Path,
    duration_sec: float,
    fps: int = 25,
    resolution: tuple[int, int] = (1280, 720),
    color_bgr: tuple[int, int, int] = (40, 40, 140),
    title: str = "TEST SHOT",
) -> Path:
    """Generate a clean test video with burnt-in SMPTE timecode and frame counter."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    w, h = resolution
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_path), fourcc, float(fps), (w, h))

    total_frames = int(duration_sec * fps)
    for f in range(total_frames):
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:] = color_bgr

        # Outer white border
        cv2.rectangle(img, (20, 20), (w - 20, h - 20), (255, 255, 255), 2)
        # Safe area 90%
        cv2.rectangle(img, (int(w * 0.05), int(h * 0.05)), (int(w * 0.95), int(h * 0.95)), (120, 120, 120), 1)

        sec = f // fps
        frame = f % fps
        tc_str = f"01:00:{sec:02d}:{frame:02d}"

        cv2.putText(img, f"{title} [{output_path.name}]", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
        cv2.putText(img, f"TC: {tc_str}", (50, 220), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 255, 255), 4)
        cv2.putText(img, f"Frame {f + 1} / {total_frames}  (@ {fps} fps)", (50, 310), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (200, 255, 200), 2)
        cv2.putText(img, "KROVAKOVA SEKERA — MANUAL QA TEST ASSET", (50, h - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180, 180, 180), 2)

        out.write(img)

    out.release()
    return output_path


def generate_stereo_wav(output_path: Path, duration_sec: int = 6, sample_rate: int = 48000) -> Path:
    """Generate 48kHz 16-bit stereo PCM WAV with 440Hz Left, 880Hz Right."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    num_samples = sample_rate * duration_sec
    with wave.open(str(output_path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.setnframes(num_samples)
        frames = bytearray()
        for i in range(num_samples):
            s_l = int(12000 * math.sin(2.0 * math.pi * 440 * i / sample_rate))
            s_r = int(12000 * math.sin(2.0 * math.pi * 880 * i / sample_rate))
            frames.extend(struct.pack("<hh", s_l, s_r))
        w.writeframes(frames)
    return output_path


def build_manual_test_suite(target_dir: Path) -> None:
    """Construct complete manual testing folders with projects, media, and AAF exports."""
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Master Media Cache
    media_cache = target_dir / "media"
    media_cache.mkdir(parents=True, exist_ok=True)
    shot_01 = generate_video(media_cache / "Shot_01.mov", duration_sec=6.0, fps=25, color_bgr=(40, 40, 140), title="SHOT 01 (STUDIO A)")
    shot_a = generate_video(media_cache / "Shot_A.mov", duration_sec=4.0, fps=25, color_bgr=(120, 60, 30), title="SHOT A (EXTERIOR)")
    shot_b = generate_video(media_cache / "Shot_B.mov", duration_sec=4.0, fps=25, color_bgr=(30, 100, 40), title="SHOT B (DRONE)")
    mono_wav = generate_sample_tone_wav(media_cache / "sample_tone.wav")
    stereo_wav = generate_stereo_wav(media_cache / "stereo_music.wav")

    # 2. Test 01: Simple Cut & Effects
    t1_dir = target_dir / "test_01_simple_cut"
    t1_dir.mkdir(parents=True, exist_ok=True)
    generate_simple_cut_prproj(t1_dir / "simple_cut.prproj")
    shutil.copy(shot_01, t1_dir / "Shot_01.mov")
    shutil.copy(mono_wav, t1_dir / "sample_tone.wav")
    proj1 = parse_prproj(t1_dir / "simple_cut.prproj")
    export_project_to_aaf(proj1, t1_dir / "simple_cut.aaf")

    # 3. Test 02: Nested Sequences (Flattening)
    t2_dir = target_dir / "test_02_nested_seq"
    t2_dir.mkdir(parents=True, exist_ok=True)
    generate_nested_seq_prproj(t2_dir / "nested_seq.prproj")
    shutil.copy(shot_a, t2_dir / "Shot_A.mov")
    shutil.copy(shot_b, t2_dir / "Shot_B.mov")
    proj2 = parse_prproj(t2_dir / "nested_seq.prproj", flatten_nested=True)
    export_project_to_aaf(proj2, t2_dir / "nested_seq.aaf")

    # 4. Test 03: Adobe Audition Multitrack (.sesx)
    t3_dir = target_dir / "test_03_audition_mix"
    t3_dir.mkdir(parents=True, exist_ok=True)
    generate_sample_audition_sesx(t3_dir / "sample_audition.sesx")
    shutil.copy(mono_wav, t3_dir / "sample_tone.wav")
    proj3 = parse_sesx(t3_dir / "sample_audition.sesx")
    export_project_to_aaf(proj3, t3_dir / "sample_audition_embedded.aaf", embed_audio=True)
    export_project_to_aaf(proj3, t3_dir / "sample_audition_linked.aaf", embed_audio=False)

    # 5. Test 04: Real-World Premiere Project (1.1 MB from projectivetech)
    t4_dir = target_dir / "test_04_real_premiere_project"
    t4_dir.mkdir(parents=True, exist_ok=True)
    sub_dir = t4_dir / "Unterwasser Klangkost"
    sub_dir.mkdir(parents=True, exist_ok=True)
    prproj_path = t4_dir / "sample.prproj"
    if not prproj_path.exists():
        import urllib.request
        url = "https://raw.githubusercontent.com/projectivetech/media-samples/master/sample.prproj"
        urllib.request.urlretrieve(url, prproj_path)

    v1 = generate_video(t4_dir / "Comic1.mov", duration_sec=10.0, fps=25, color_bgr=(50, 80, 160), title="COMIC 1 (UNDERWATER)")
    v2 = generate_video(t4_dir / "Pt2 n.mov", duration_sec=8.0, fps=25, color_bgr=(140, 50, 70), title="PART 2 (SCENE B)")
    v3 = generate_video(t4_dir / "PT3 n.mov", duration_sec=6.0, fps=25, color_bgr=(60, 120, 50), title="PART 3 (SCENE C)")
    v4 = generate_video(t4_dir / "Pt1 n.mov", duration_sec=6.0, fps=25, color_bgr=(130, 100, 30), title="PART 1 (SCENE A)")
    shutil.copy(v1, sub_dir / "Comic1.mov")

    proj4 = parse_prproj(prproj_path)
    export_project_to_aaf(proj4, t4_dir / "sample.aaf")

    print(f"Manual test suite successfully built at: {target_dir}")


if __name__ == "__main__":
    out_dir = REPO_ROOT / "manual_testing"
    build_manual_test_suite(out_dir)
