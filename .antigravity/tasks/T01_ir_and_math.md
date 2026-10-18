# TASK T01: Canonical IR Schema & Rational Timecode Engine

- **Primary Model:** Claude Opus 5.5
- **Escalation Model:** None (Architectural Foundation)
- **Allowed Context (Read):** `.antigravity/rules.md`, `pyproject.toml`
- **Target Outputs (Write):**
  - `src/machete/__init__.py`
  - `src/machete/ir/__init__.py`
  - `src/machete/ir/timecode.py`
  - `src/machete/ir/schema.py`
  - `tests/test_timecode.py`

## 1. OBJECTIVE
Build the exact rational math engine (`timecode.py`) and strict Pydantic data contract (`schema.py`) that guarantee zero frame/sample drift across feature-length timelines (3+ hours).

## 2. SPECIFICATIONS

### A. `src/machete/ir/timecode.py`
Implement using `fractions.Fraction` and `int` only (no `float` arithmetic):
- `PPRO_TICKS_PER_SEC: int = 254_016_000_000`
- Standard broadcast edit rates dictionary `EDIT_RATES`:
  - `"23.976"`: `Fraction(24000, 1001)`
  - `"24"`: `Fraction(24, 1)`
  - `"25"`: `Fraction(25, 1)`
  - `"29.97"`: `Fraction(30000, 1001)`
  - `"30"`: `Fraction(30, 1)`
  - `"50"`: `Fraction(50, 1)`
  - `"59.94"`: `Fraction(60000, 1001)`
  - `"60"`: `Fraction(60, 1)`
- Functions:
  - `ticks_to_frames(ticks: int, edit_rate: Fraction) -> int`: Exact nearest integer frame using rational division `(Fraction(ticks, PPRO_TICKS_PER_SEC) * edit_rate)` rounded half-to-even or floor-consistent.
  - `frames_to_ticks(frames: int, edit_rate: Fraction) -> int`: Exact integer ticks `int(round(Fraction(frames, 1) / edit_rate * PPRO_TICKS_PER_SEC))`.
  - `samples_to_frames(samples: int, sample_rate: int, edit_rate: Fraction) -> int`
  - `frames_to_samples(frames: int, sample_rate: int, edit_rate: Fraction) -> int`
  - `frames_to_smpte_tc(frames: int, edit_rate: Fraction, drop_frame: bool = False) -> str`:
    - Format `HH:MM:SS:FF` for non-drop-frame, `HH:MM:SS;FF` for drop-frame.
    - Must accurately apply SMPTE 29.97 (drop 2 frame numbers every minute except every 10th minute, `D = 17982` frames per 10-min block) and 59.94 (drop 4 frame numbers).
  - `deterministic_mob_uid(seed_str: str) -> uuid.UUID`: Return `uuid.uuid5(uuid.NAMESPACE_DNS, f"krovak.machete:{seed_str}")`.

### B. `src/machete/ir/schema.py`
Use `pydantic.BaseModel`. Support seamless JSON serialization of `Fraction` (serialize as string `"num/den"`, parse back from `"num/den"` or `int`):
- `MediaSourceIR`:
  - `source_id: str`
  - `name: str`
  - `file_path: str | None`
  - `reel_name: str = "AX"`
  - `start_tc_frames: int = 0`
  - `duration_frames: int`
  - `edit_rate: Fraction`
  - `sample_rate: int = 48000`
  - `audio_channels: int = 2`
  - `has_video: bool = True`
  - `has_audio: bool = True`
- `KeyframeIR`:
  - `offset_frames: int` (relative to clip `timeline_in_frames`)
  - `value: Fraction` (linear gain multiplier `0/1` to `4/1`, or pan `-1/1` to `1/1`)
- `TransitionIR`:
  - `duration_frames: int`
  - `alignment: Literal["center", "start", "end"] = "center"`
  - `kind: Literal["cross_dissolve", "audio_crossfade"] = "cross_dissolve"`
- `EffectNoticeIR`:
  - `effect_name: str`
  - `parameters_summary: str = ""`
  - `requires_manual_recreate: bool = True`
- `MarkerIR`:
  - `frame_offset: int`
  - `duration_frames: int = 1`
  - `name: str`
  - `comment: str = ""`
  - `color: Literal["red", "yellow", "green", "blue", "cyan", "magenta", "white", "black"] = "red"`
- `ClipIR`:
  - `clip_id: str`
  - `name: str`
  - `source_id: str`
  - `timeline_in_frames: int`
  - `timeline_out_frames: int`
  - `source_in_frames: int`
  - `source_channel: int = 0`
  - `speed_ratio: Fraction = Fraction(1, 1)`
  - `gain_db: Fraction = Fraction(0, 1)`
  - `volume_keyframes: list[KeyframeIR] = []`
  - `pan_keyframes: list[KeyframeIR] = []`
  - `transition_in: TransitionIR | None = None`
  - `transition_out: TransitionIR | None = None`
  - `unsupported_effects: list[EffectNoticeIR] = []`
  - `markers: list[MarkerIR] = []`
  - Property `duration_frames -> int`: returns `timeline_out_frames - timeline_in_frames`.
- `TrackIR`:
  - `track_index: int`
  - `name: str`
  - `kind: Literal["picture", "sound"]`
  - `channel_index: int = 0`
  - `clips: list[ClipIR] = []`
- `SequenceIR`:
  - `seq_id: str`
  - `name: str`
  - `edit_rate: Fraction = Fraction(25, 1)`
  - `drop_frame: bool = False`
  - `sample_rate: int = 48000`
  - `start_tc_frames: int = 0`
  - `duration_frames: int`
  - `tracks: list[TrackIR] = []`
  - `markers: list[MarkerIR] = []`
  - Method `validate_no_overlaps(self) -> None`: Raises `ValueError` if any track has clips with `timeline_out_frames <= timeline_in_frames`, negative positions, or unsorted/overlapping intervals.
- `ProjectIR`:
  - `project_name: str`
  - `source_format: Literal["prproj", "sesx"]`
  - `media_sources: dict[str, MediaSourceIR] = {}`
  - `sequences: list[SequenceIR] = []`

## 3. ACCEPTANCE TESTS (`tests/test_timecode.py`)
1. Test `ticks_to_frames` and `frames_to_ticks` round-trip at `24`, `25`, and `24000/1001` across a 3-hour feature duration (`10800` seconds) with zero frame drift.
2. Test SMPTE drop-frame timecode at `30000/1001` (`drop_frame=True`): frame `1799` -> `"00:00:59;29"`, frame `1800` -> `"00:01:00;02"`, frame `17982` -> `"00:10:00;00"`.
3. Test `ProjectIR` JSON round-trip (`model_dump_json()` -> `model_validate_json()`) preserving exact `Fraction` types.
4. Test `SequenceIR.validate_no_overlaps()` raises `ValueError` when two clips overlap.

## 4. STOP RULES
- Run `pytest tests/test_timecode.py`.
- Once green, terminate immediately. Do not touch parser or exporter directories.
