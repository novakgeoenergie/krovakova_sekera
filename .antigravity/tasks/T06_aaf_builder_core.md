# TASK T06: Avid AAF Core Exporter (Mobs, Cuts, Fillers, Transitions & Markers)

- **Primary Model:** Claude Sonnet 5.5
- **Escalation Model:** Claude Opus 5.5
- **Allowed Context (Read):**
  - `.antigravity/rules.md`
  - `src/machete/ir/timecode.py`
  - `src/machete/ir/schema.py`
  - *(FORBIDDEN: Do NOT read `src/machete/parsers/*`)*
- **Target Outputs (Write):**
  - `src/machete/exporters/__init__.py`
  - `src/machete/exporters/aaf_core.py`
  - `tests/test_aaf_core.py`

## 1. OBJECTIVE
Build the core Avid AAF binary writer (`aaf_core.py`) from `ProjectIR` using `pyaaf2`, strictly enforcing the Avid Zero-Gap Law, deterministic `MobID` generation, transitions, and timeline markers.

## 2. VERIFIED `pyaaf2` CHEAT-SHEET (USE DIRECTLY — DO NOT GUESS API)
```python
import aaf2
from aaf2.mobid import MobID
from pathlib import Path

with aaf2.open(str(output_path), "w") as f:
    # 1. Deterministic MobID
    comp_mob = f.create.CompositionMob(seq_ir.name)
    comp_mob.mob_id = MobID(bytes_le=deterministic_mob_uid(f"comp:{seq_ir.seq_id}").bytes_le)
    comp_mob.usage_code = "Usage_TopLevel"
    f.content.mobs.append(comp_mob)

    # 2. SourceMob (Tape / Import Descriptor) + MasterMob per MediaSourceIR
    tape_mob = f.create.SourceMob(src_ir.reel_name or src_ir.name)
    tape_mob.descriptor = f.create.ImportDescriptor()
    if src_ir.file_path:
        loc = f.create.NetworkLocator()
        loc["URLString"].value = Path(src_ir.file_path).resolve().as_uri()
        tape_mob.descriptor["Locator"].append(loc)
    f.content.mobs.append(tape_mob)
    tape_slot = tape_mob.create_source_slot(seq_ir.edit_rate)
    tape_slot.segment.length = max(src_ir.duration_frames, 108000)

    master_mob = f.create.MasterMob(src_ir.name)
    master_mob.mob_id = MobID(bytes_le=deterministic_mob_uid(f"master:{src_ir.source_id}").bytes_le)
    f.content.mobs.append(master_mob)
    master_slot = master_mob.create_picture_slot(seq_ir.edit_rate)  # or create_sound_slot
    master_slot.segment = tape_mob.create_source_clip(
        slot_id=tape_slot.slot_id, start=0, length=tape_slot.segment.length
    )

    # 3. Sequence Track + Zero-Gap Fillers + Clips
    slot = comp_mob.create_timeline_slot(seq_ir.edit_rate)
    slot.name = track_ir.name
    seq = f.create.Sequence(media_kind=track_ir.kind)  # "picture" or "sound"
    filler = f.create.Filler(track_ir.kind, gap_length)
    seq.components.append(filler)
    clip = master_mob.create_source_clip(
        slot_id=master_slot.slot_id, start=clip_ir.source_in_frames, length=clip_ir.duration_frames
    )
    seq.components.append(clip)
    slot.segment = seq
```

## 3. SPECIFICATIONS (`src/machete/exporters/aaf_core.py`)
Implement `export_project_to_aaf(project: ProjectIR, output_path: str | Path, embed_audio: bool = False) -> Path`:
1. Create a `MasterMob` + `SourceMob` pair for every `MediaSourceIR` with deterministic MobIDs.
2. For each `SequenceIR`, create a top-level `CompositionMob`.
3. For each `TrackIR`:
   - Maintain `cursor_frame = 0`.
   - For each `ClipIR` (sorted by `timeline_in_frames`):
     - If `clip.timeline_in_frames > cursor_frame`, insert a `Filler(track.kind, clip.timeline_in_frames - cursor_frame)`.
     - Append the `SourceClip` referencing the corresponding MasterMob slot.
     - Advance `cursor_frame = clip.timeline_out_frames`.
   - If `cursor_frame < seq_ir.duration_frames`, append a trailing `Filler(track.kind, seq_ir.duration_frames - cursor_frame)` so all tracks match `seq_ir.duration_frames`.
4. Markers / Effect Notices:
   - Collect all `SequenceIR.markers` and clip-level `ClipIR.markers` (including red markers generated for unsupported Adobe effects).
   - Attach them as metadata comments on `comp_mob.comments` (e.g., `comp_mob.comments[f"MARKER_{idx}_{m.frame_offset}"] = f"[{m.color.upper()}] {m.name}: {m.comment}"`) AND, if supported by the slot setup, a dedicated `DescriptiveMarker` / comment entry so both Avid and our inspector can read them deterministically.

## 4. ACCEPTANCE TESTS (`tests/test_aaf_core.py`)
1. Build a `ProjectIR` with 1 picture track (`0..50`, gap `50..75`, clip `75..125`, sequence duration `150`) and 1 red marker.
2. Export to `tmp_path / "test.aaf"`.
3. Re-open with `aaf2.open(str(path), "r")` and assert:
   - Top-level `CompositionMob` exists with deterministic MobID.
   - Track `V1` has 4 components: `SourceClip(50)`, `Filler(25)`, `SourceClip(50)`, `Filler(25)` summing to `150`.
   - Re-exporting the same `ProjectIR` produces identical MobIDs.

## 5. STOP RULES
- Run `pytest tests/test_aaf_core.py` and stop immediately when green.
