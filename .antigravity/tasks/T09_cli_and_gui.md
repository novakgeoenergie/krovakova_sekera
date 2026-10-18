# TASK T09: CLI, CMX 3600 EDL Generator & Křovákova Sekera GUI (with Dwarf Progress Monitor)

- **Primary Model:** Gemini 3.8 Flash
- **Escalation Model:** Gemini 4 Argon
- **Allowed Context (Read):**
  - `.antigravity/rules.md`
  - `src/machete/ir/timecode.py`
  - `src/machete/ir/schema.py`
  - `src/machete/parsers/prproj_extract.py`
  - `src/machete/parsers/sesx_extract.py`
  - `src/machete/exporters/aaf_core.py`
  - `src/machete/exporters/aaf_audio.py`
  - `src/machete/verify/aaf_inspector.py`
- **Pre-Built Visual Assets (Reference by Path Only — Do Not Read Into Context):**
  - `src/machete/assets/dwarf_scene.png` (480x270 woodcut illustration on parchment)
  - `src/machete/assets/dwarf_seal.png` (256x256 circular dwarf stonemason icon)
  - `src/machete/assets/dwarf_seal.icns` (macOS application bundle icon)
- **Target Outputs (Write):**
  - `src/machete/exporters/edl_cmx3600.py`
  - `src/machete/cli.py`
  - `src/machete/gui.py`
  - `tests/test_cli_and_edl.py`

## 1. OBJECTIVE
Deliver the final user-facing tools: a backup CMX 3600 EDL exporter (`edl_cmx3600.py`), a full-featured CLI (`cli.py`), and a zero-dependency `tkinter` GUI (`gui.py`) branded as **"Křovákova Sekera"** featuring a parchment-and-ink Tolkien woodcut aesthetic, application seal icon, and an animated Dwarf Stonemason progress monitor.

## 2. SPECIFICATIONS

### A. `src/machete/exporters/edl_cmx3600.py`
Implement `export_sequence_to_edl(seq: SequenceIR, media_sources: dict[str, MediaSourceIR], output_path: str | Path) -> Path`:
- Write standard CMX 3600 header: `TITLE: {seq.name}` and `FCM: DROP FRAME` or `NON-DROP FRAME`.
- For each clip on the primary video track (or first audio track if audio-only), format standard event lines:
  `001  {REEL:<8} V     C        {SRC_IN} {SRC_OUT} {REC_IN} {REC_OUT}`
  `* FROM CLIP NAME: {clip.name}`
- Include markers/unsupported effects as `* LOC: {TC} RED     {marker.name}` lines.

### B. `src/machete/cli.py`
Use `argparse` to provide command `machete`:
- Usage: `machete convert <input_file> -o <output.aaf> [--embed-audio] [--split-mono] [--no-flatten] [--also-edl] [--report <report.md>]`
- Implement a reusable pipeline runner `run_conversion_pipeline(..., progress_callback: Callable[[int, str], None] | None = None) -> VerificationResult` that reports progress across 5 deterministic stages:
  1. `(15, "Průzkum slojí a indexace Adobe XML...")`
  2. `(40, "Osekávání vnořených sekvencí na čisté kvádry...")`
  3. `(70, "Kladení základů Avid AAF stromu...")`
  4. `(85, "Třídění a zalévání audio esencí (PCM WAV)...")`
  5. `(100, "Kamenická inspekce integrity zdiva (Roundtrip Verifier)...")`
- Automatically detect `.prproj` vs `.sesx` by file extension.
- Run `verify_aaf_against_ir` automatically after every export; exit with code 0 if valid, 1 if verification fails.
- Usage: `machete gui` launches the desktop window.

### C. `src/machete/gui.py` (Křovákova Sekera)
Build a `tkinter` window titled `"Křovákova Sekera — Adobe -> Avid Překladač"`:
- **Visual Theme & Icon:**
  - Parchment background (`#F3EBD8`), secondary panel fill (`#E6D9BE`), charcoal ink text/borders (`#1E1E1E`).
  - Load application icon from `Path(__file__).resolve().parent / "assets" / "dwarf_seal.png"` via `root.iconphoto(True, icon_img)` (with graceful fallback if headless/missing).
- **Controls:**
  - File pickers for input (`.prproj` / `.sesx`) and output (`.aaf`).
  - Checkboxes:
    - `[x] Zploštit vnořené sekvence (Flatten Nested Sequences)`
    - `[x] Vložit WAV zvuk přímo do AAF (Embedded Audio pro Pro Tools)`
    - `[x] Rozdělit stereo stopy na mono (A1.L / A2.R)`
    - `[x] Vygenerovat záložní CMX 3600 EDL a kontrolní report`
  - Prominent action button: `"ZATNOUT SEKERU DO ADOBE"`.
- **Animated Dwarf Progress Monitor (`DwarfProgressMonitor` widget on `tk.Canvas`):**
  - Displays the woodcut scene (`src/machete/assets/dwarf_scene.png`) on a `480x270` parchment canvas.
  - Runs conversion asynchronously in a background `threading.Thread(daemon=True)` communicating via `queue.Queue` and `root.after(100, ...)` so the UI never freezes.
  - **States:**
    - `IDLE`: Static scene, status `"Sekera připravena k dílu."` (`0%`).
    - `WORKING`: Animates flying ink stone chips between the Adobe cliff (left) and the rising Avid masonry wall (right), visually filling/highlighting stone blocks and a parchment progress bar proportional to current percentage (`0–100%`) while displaying the active stage message.
    - `SUCCESS`: Full Avid wall completed, status `"DÍLO DOKONÁNO — Kámen sedí na vzorek přesně (100%)"`, outputs full diagnostic Markdown report in the bottom parchment text panel.
    - `ERROR`: Status `"SEKERA NARAZILA NA KŘEMEN (Chyba konverze)"` and displays error details in the report panel.

## 3. ACCEPTANCE TESTS (`tests/test_cli_and_edl.py`)
1. Test `main(["convert", str(prproj_path), "-o", str(aaf_path), "--also-edl", "--report", str(report_path)])` returns exit code 0.
2. Assert `.aaf`, `.edl`, and `.md` report files are created on disk and non-empty.
3. Assert `.edl` contains `TITLE: Main_Edit_25fps` and `001` event line with valid SMPTE timecodes.
4. Test `run_conversion_pipeline` invokes `progress_callback` in strictly non-decreasing percentage order (`15 -> 40 -> 70 -> 85 -> 100`) with Czech stonemason stage messages.

## 4. STOP RULES
- Run full test suite `pytest` across all test files.
- Once 100% of tests pass, stop immediately. Project is complete.
