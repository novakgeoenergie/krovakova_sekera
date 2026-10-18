# TASK T07: Avid AAF Audio Essence (Embedded/Linked WAV) & Volume Automation

- **Primary Model:** Claude Sonnet 5.5
- **Escalation Model:** Claude Opus 5.5
- **Allowed Context (Read):**
  - `.antigravity/rules.md`
  - `src/machete/ir/timecode.py`
  - `src/machete/ir/schema.py`
  - `src/machete/exporters/aaf_core.py`
- **Target Outputs (Write):**
  - `src/machete/exporters/aaf_audio.py`
  - `src/machete/exporters/aaf_core.py` (hook in audio helper)
  - `tests/test_aaf_audio.py`

## 1. OBJECTIVE
Extend the AAF exporter so Pro Tools and Media Composer receive either embedded PCM `.wav` audio essence (`embed_audio=True`) or linked `PCMDescriptor` sources, along with clip gain and volume keyframes (`VaryingValue`).

## 2. VERIFIED `pyaaf2` AUDIO CHEAT-SHEET
```python
# Option A: Importing/Embedding a real WAV file directly into MasterMob
if embed_audio and src_ir.file_path and Path(src_ir.file_path).exists():
    # pyaaf2 built-in PCM WAV importer creates MasterMob, SourceMob, PCMDescriptor & EssenceData:
    audio_master_mob = f.content.link_external_wav(str(src_ir.file_path))  # or import_audio_essence
```
*(Note: If `import_audio_essence` or `create_empty_pcm_essence` is used, or if `PCMDescriptor` is constructed manually, ensure `SampleRate`, `QuantizationBits`, `Channels`, and `BlockAlign` are set on `PCMDescriptor`).*

For Clip Volume / Keyframe Automation without breaking strict Avid parsers:
Attach clip gain (`gain_db`) and serialized keyframe envelope points to both the `SourceClip` / `OperationGroup` parameters AND a structured `ComponentAttributeList` / `UserComments` entry on the component (or `MasterMob.comments`) so both Avid and the round-trip inspector have 100% lossless access to rational keyframe points.

## 3. SPECIFICATIONS (`src/machete/exporters/aaf_audio.py`)
1. Implement `attach_audio_source_and_essence(f, src_ir: MediaSourceIR, edit_rate: Fraction, embed_audio: bool)`:
   - When `embed_audio=True` and `src_ir.file_path` points to an existing `.wav` file, read the WAV parameters (`wave.open`) and populate a valid `PCMDescriptor` on the `SourceMob` AND write the raw PCM frames into an `EssenceData` object linked to `source_mob.mob_id` in `f.content.essencedata` (or use `master_mob.import_audio_essence(wav_path, edit_rate)` if supported by the installed `pyaaf2` version).
   - When `embed_audio=False`, create a `PCMDescriptor` with `NetworkLocator` pointing to the `.wav` URI.
2. Implement `apply_audio_automation(f, component, clip_ir: ClipIR)`:
   - Record `gain_db` and `volume_keyframes` (`offset_frames`, `value`) on the audio component / mob metadata so volume curves survive round-trip inspection.
3. Implement `split_stereo_tracks_to_mono(seq_ir: SequenceIR) -> SequenceIR`:
   - Helper for Pro Tools / Avid workflows that splits any stereo `TrackIR` into two mono tracks (`A1.L` with `channel_index=1`, `A1.R` with `channel_index=2`).

## 4. ACCEPTANCE TESTS (`tests/test_aaf_audio.py`)
1. Generate `sample_tone.wav` using `tests/fixture_factory.py`.
2. Export a `ProjectIR` referencing `sample_tone.wav` with `embed_audio=True` and 2 volume keyframes.
3. Re-open the resulting `.aaf` file with `aaf2.open(..., "r")` and verify:
   - `PCMDescriptor` exists with `SampleRate == 48000` and `QuantizationBits == 16`.
   - Raw PCM essence data or linked WAV locator is present inside the AAF file.
   - `split_stereo_tracks_to_mono` properly converts 1 stereo track into 2 mono tracks with identical clip timings.

## 5. STOP RULES
- Run `pytest tests/test_aaf_audio.py` and `pytest tests/test_aaf_core.py`. Stop immediately when both pass.
