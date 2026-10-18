# TASK T04: Premiere Timeline Extractor, Nested Sequence Flattener & Effect Mapper

- **Primary Model:** Gemini 4 Argon
- **Escalation Model:** Claude Sonnet 5.5
- **Allowed Context (Read):**
  - `.antigravity/rules.md`
  - `src/machete/ir/timecode.py`
  - `src/machete/ir/schema.py`
  - `src/machete/parsers/prproj_index.py`
  - `tests/fixture_factory.py`
- **Target Outputs (Write):**
  - `src/machete/parsers/prproj_extract.py`
  - `tests/test_prproj_extract.py`

## 1. OBJECTIVE
Transform indexed `.prproj` XML graphs into a strictly validated `ProjectIR`, handling rational tick-to-frame conversion, L/J-cuts, recursive nested sequence flattening, volume keyframes, and converting unsupported Adobe effects into editor notices/markers.

## 2. SPECIFICATIONS (`src/machete/parsers/prproj_extract.py`)
Implement function `parse_prproj(path: str | Path, flatten_nested: bool = True) -> ProjectIR`:
1. **Media Sources Extraction:**
   - Extract all `<Media>` objects into `MediaSourceIR` entries keyed by `ObjectID`/`ObjectUID`.
2. **Sequence & Track Extraction:**
   - Determine sequence `edit_rate` (default `Fraction(25, 1)` if not explicitly specified in `<FrameRate>` ticks, where ticks-per-frame `10160640000` = `25` fps).
   - Extract Video (`VideoTrackGroup` / `VideoClipTrack`) as `kind="picture"` and Audio (`AudioTrackGroup` / `AudioClipTrack`) as `kind="sound"`.
3. **Clips & Nested Sequences (Flattening):**
   - Convert `<Start>`, `<End>`, and `<InPoint>` from Premiere Ticks to integer frames using `ticks_to_frames(ticks, edit_rate)`.
   - **Nested Sequence Detection:** If a clip's `<SubClip>/<Clip>/<Source>` points to another `<Sequence>` (instead of `<Media>`) and `flatten_nested=True`:
     - Recursively splice the child sequence's clips onto the parent track, shifting their `timeline_in_frames` and `timeline_out_frames` by the parent clip's timeline start minus child `source_in_frames`, and clamping to the parent clip's bounds.
4. **Unsupported Effects -> Red Markers:**
   - Inspect clip filter components (`<VideoFilterComponent>`, `<AudioFilterComponent>`, or non-100% `<Speed>`).
   - Populate `ClipIR.unsupported_effects` AND append a red `MarkerIR` (`color="red"`) at the clip's `timeline_in_frames` with `name=f"ADOBE FX: {effect_name}"`.
5. **Keyframes & Markers:**
   - Extract clip volume keyframes into `ClipIR.volume_keyframes` as `KeyframeIR(offset_frames=..., value=Fraction(...))`.
   - Extract sequence markers into `SequenceIR.markers`.
6. **Validation:**
   - Sort clips on every track by `timeline_in_frames` and call `seq.validate_no_overlaps()`.

## 3. ACCEPTANCE TESTS (`tests/test_prproj_extract.py`)
1. Parse `simple_cut.prproj`:
   - Verify `V1` has 2 clips at frames `0..50` and `75..125` (confirming the 25-frame gap between `50` and `75`).
   - Verify `A1` reflects the J-cut (`timeline_in_frames == 62` or `63` for 2.5s at 25fps) and contains 2 volume keyframes.
   - Verify the `"Warp Stabilizer"` effect produced both an `EffectNoticeIR` and a red `MarkerIR`.
2. Parse `nested_seq.prproj` with `flatten_nested=True`:
   - Verify `Master_Seq` contains the two underlying shots from `Child_Seq` shifted to start at frame `25` (`1s`) and `50` (`2s`).

## 4. STOP RULES
- Do NOT import `aaf2`. Output must be pure `ProjectIR`.
- Run `pytest tests/test_prproj_extract.py` and stop immediately when green.
