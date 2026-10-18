# TASK T02: Synthetic Adobe Fixture Factory (`.prproj`, `.sesx`, `.wav`)

- **Primary Model:** Gemini 3.8 Flash
- **Escalation Model:** Gemini 4 Argon
- **Allowed Context (Read):**
  - `.antigravity/rules.md`
  - `src/machete/ir/timecode.py`
  - `src/machete/ir/schema.py`
- **Target Outputs (Write):**
  - `tests/fixture_factory.py`
  - `tests/test_fixtures.py`

## 1. OBJECTIVE
Create a deterministic generator (`tests/fixture_factory.py`) that builds lightweight (<15 KB), structurally valid `.prproj` (GZIP-compressed XML), `.sesx` (Audition XML), and 16-bit PCM `.wav` files on disk for automated testing.

## 2. SPECIFICATIONS (`tests/fixture_factory.py`)
Provide function `generate_all_fixtures(base_dir: Path) -> dict[str, Path]` that creates:

1. **`sample_tone.wav`**:
   - Valid 16-bit mono PCM WAV, `48000` Hz, duration `6` seconds (sine wave 440 Hz).
2. **`simple_cut.prproj`** (GZIP XML, 25 fps):
   - Sequence `Main_Edit_25fps` (`EditRate` 25 fps).
   - Video Track `V1` with 2 clips referencing `sample_tone.wav` / `Shot_01.mov`:
     - Clip 1: Timeline `0s..2s` (`0` to `508032000000` ticks), Source In `0s`, plus an unsupported effect `<VideoFilterComponent>` named `"Warp Stabilizer"`.
     - Gap: `2s..3s` (1 second empty space on timeline).
     - Clip 2 (L-Cut): Video Timeline `3s..5s`, Source In `1s`.
   - Audio Track `A1` with corresponding audio clips where Clip 2 audio starts earlier at `2.5s..5s` (J-cut / L-cut offset) and includes 2 volume keyframes (`0s -> 1.0`, `1s -> 0.5`).
   - Sequence Marker at `1s` (`254016000000` ticks) with name `"VFX_Check"` and comment `"Check green screen"`.
3. **`nested_seq.prproj`** (GZIP XML, 25 fps):
   - Contains `Child_Seq` (with 2 cuts of `Shot_A` and `Shot_B`, each 1s long) and `Master_Seq` which places `Child_Seq` as a nested clip on `V1` starting at `1s` with duration `2s`.
4. **`sample_audition.sesx`** (Plain XML, 48000 Hz):
   - Multitrack session `Audition_Mix`, `sampleRate="48000"`.
   - Track `Dialogue_1` with two `<audioClip>` items referencing `sample_tone.wav`:
     - Clip 1: `startPoint="0"`, `endPoint="96000"`, `sourceInPoint="0"`, `sourceOutPoint="96000"`.
     - Clip 2: `startPoint="144000"`, `endPoint="240000"`, `sourceInPoint="24000"`, `sourceOutPoint="120000"`, plus `<fadeIn>` / `<component id="volume">` keyframes.

## 3. ACCEPTANCE TESTS (`tests/test_fixtures.py`)
1. Call `generate_all_fixtures(tmp_path)` and assert all 4 files exist and each XML is `< 15360` bytes.
2. Assert `simple_cut.prproj` and `nested_seq.prproj` decompress cleanly with `gzip.open` and parse via `xml.etree.ElementTree`.
3. Assert `sample_tone.wav` opens with standard library `wave.open` and reports `48000` Hz, `1` channel, `2` bytes sample width.

## 4. STOP RULES
- Run `pytest tests/test_fixtures.py`.
- Stop immediately once all tests pass.
