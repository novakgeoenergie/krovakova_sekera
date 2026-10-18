# TASK T05: Adobe Audition (`.sesx`) XML Parser to Canonical IR

- **Primary Model:** Gemini 3.8 Flash
- **Escalation Model:** Gemini 4 Argon
- **Allowed Context (Read):**
  - `.antigravity/rules.md`
  - `src/machete/ir/timecode.py`
  - `src/machete/ir/schema.py`
  - `tests/fixture_factory.py`
- **Target Outputs (Write):**
  - `src/machete/parsers/sesx_extract.py`
  - `tests/test_sesx_extract.py`

## 1. OBJECTIVE
Parse Adobe Audition `.sesx` multitrack session XML files into `ProjectIR` using exact sample-to-frame rational conversion.

## 2. SPECIFICATIONS (`src/machete/parsers/sesx_extract.py`)
Implement `parse_sesx(path: str | Path, target_edit_rate: Fraction = Fraction(25, 1)) -> ProjectIR`:
1. Read `<session>` attributes: `sampleRate` (int, default `48000`) and `duration` (samples).
2. Read `<files>/<file>` elements: map `id` to `MediaSourceIR` (`file_path=absolutePath`, `sample_rate=sampleRate`, `has_video=False`, `has_audio=True`).
3. Read `<tracks>/<audioTrack>`:
   - Create `TrackIR(kind="sound", name=..., track_index=...)`.
   - For each `<audioClip>`:
     - Convert `startPoint`, `endPoint` (or `EndPoint`), and `sourceInPoint` from integer audio samples to frames via `samples_to_frames(samples, sample_rate, target_edit_rate)`.
     - Parse any volume keyframes or fade envelopes into `ClipIR.volume_keyframes`.
4. Call `seq.validate_no_overlaps()` on the resulting `SequenceIR`.

## 3. ACCEPTANCE TESTS (`tests/test_sesx_extract.py`)
1. Parse `sample_audition.sesx` at `25` fps (`48000` Hz):
   - Clip 1 (`0..96000` samples) -> `timeline_in_frames == 0`, `timeline_out_frames == 50`.
   - Clip 2 (`144000..240000` samples, `sourceInPoint="24000"`) -> `timeline_in_frames == 75`, `timeline_out_frames == 125`, `source_in_frames == 12`.
2. Verify JSON serialization of the resulting `ProjectIR`.

## 4. STOP RULES
- Run `pytest tests/test_sesx_extract.py` and stop immediately when green.
