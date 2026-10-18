# TASK T08: Round-Trip AAF Inspector & Editor Diagnostic Report

- **Primary Model:** Gemini 4 Argon
- **Escalation Model:** Claude Sonnet 5.5
- **Allowed Context (Read):**
  - `.antigravity/rules.md`
  - `src/machete/ir/timecode.py`
  - `src/machete/ir/schema.py`
  - `src/machete/exporters/aaf_core.py`
- **Target Outputs (Write):**
  - `src/machete/verify/__init__.py`
  - `src/machete/verify/aaf_inspector.py`
  - `tests/test_roundtrip.py`

## 1. OBJECTIVE
Create an independent verification engine (`aaf_inspector.py`) that opens any generated `.aaf` file in read-only mode, checks every Avid invariant (Zero-Gap Law, non-negative lengths, unique MobIDs, exact frame counts against `ProjectIR`), and generates a human-readable diagnostic report for Křovák.

## 2. SPECIFICATIONS (`src/machete/verify/aaf_inspector.py`)
- Dataclass `VerificationReport`:
  - `is_valid: bool`
  - `sequence_name: str`
  - `total_tracks: int`
  - `total_clips: int`
  - `total_fillers: int`
  - `errors: list[str]`
  - `warnings: list[str]` (including all unsupported Adobe effects converted to red markers)
  - Method `to_markdown(self) -> str`: Formats a clear Czech/English summary table for the editor (showing exact SMPTE timecode of every red marker / unsupported Adobe effect).
- Function `verify_aaf_against_ir(aaf_path: str | Path, expected_ir: ProjectIR) -> VerificationReport`:
  - Open `aaf_path` via `aaf2.open(str(aaf_path), "r")`.
  - Verify every `CompositionMob` matches a `SequenceIR` in `expected_ir`.
  - For every timeline slot:
    - Walk `slot.segment.components`.
    - Verify no component has length `<= 0`.
    - Verify sum of all `SourceClip` and `Filler` lengths equals `seq_ir.duration_frames`.
    - Verify every `SourceClip` start frame and length on the timeline matches the corresponding `ClipIR` in `expected_ir` with 0 frames tolerance.

## 3. ACCEPTANCE TESTS (`tests/test_roundtrip.py`)
1. Full End-to-End test 1: `simple_cut.prproj` -> `parse_prproj` -> `export_project_to_aaf` -> `verify_aaf_against_ir`. Assert `report.is_valid` is `True` and `"Warp Stabilizer"` appears in `report.warnings` / `report.to_markdown()`.
2. Full End-to-End test 2: `nested_seq.prproj` -> `parse_prproj(flatten_nested=True)` -> `export_project_to_aaf` -> `verify_aaf_against_ir`. Assert `report.is_valid` is `True`.
3. Full End-to-End test 3: `sample_audition.sesx` -> `parse_sesx` -> `export_project_to_aaf(embed_audio=True)` -> `verify_aaf_against_ir`. Assert `report.is_valid` is `True`.

## 4. STOP RULES
- Run `pytest tests/test_roundtrip.py` and stop immediately when green.
