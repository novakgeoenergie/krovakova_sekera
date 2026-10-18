from __future__ import annotations

from pathlib import Path
import aaf2
from aaf2.mobid import MobID

from machete.ir import (
    MediaSourceIR,
    ProjectIR,
    deterministic_mob_uid,
)


def deterministic_mob_id(seed_str: str) -> MobID:
    """Generate a deterministic 32-byte AAF MobID from a seed string using deterministic_mob_uid."""
    uid = deterministic_mob_uid(seed_str)
    m = MobID()
    m.SMPTELabel = [0x06, 0x0a, 0x2b, 0x34, 0x01, 0x01, 0x01, 0x05, 0x01, 0x01, 0x0f, 0x20]
    m.length = 0x13
    m.instanceHigh = 0x00
    m.instanceMid = 0x00
    m.instanceLow = 0x00
    m.material = uid
    return m


def export_project_to_aaf(
    project: ProjectIR,
    output_path: str | Path,
    embed_audio: bool = False,
    split_stereo: bool = False,
) -> Path:
    """Export a ProjectIR canonical intermediate representation to an AAF file.

    Follows the Avid Zero-Gap Law (contiguous tracks starting at frame 0, gaps filled with Filler),
    the No-Float Time Law (only Fractions and exact ints), and uses deterministic MobIDs.
    """
    from machete.exporters.aaf_audio import (
        apply_audio_automation,
        attach_audio_source_and_essence,
        split_stereo_tracks_to_mono,
    )

    out_path = Path(output_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    # Determine sequences to export
    sequences = (
        [split_stereo_tracks_to_mono(s) for s in project.sequences]
        if split_stereo
        else project.sequences
    )

    # Determine default edit rate
    default_edit_rate = sequences[0].edit_rate if sequences else None

    # Collect and ensure all referenced media sources exist
    media_sources: dict[str, MediaSourceIR] = dict(project.media_sources)
    for seq in sequences:
        for track in seq.tracks:
            for clip in track.clips:
                if clip.source_id not in media_sources:
                    media_sources[clip.source_id] = MediaSourceIR(
                        source_id=clip.source_id,
                        name=clip.name or clip.source_id,
                        reel_name="AX",
                        duration_frames=max(clip.source_in_frames + clip.duration_frames, 108000),
                        edit_rate=seq.edit_rate,
                        has_video=(track.kind == "picture"),
                        has_audio=(track.kind == "sound"),
                    )

    with aaf2.open(str(out_path), "w") as f:
        master_mobs: dict[str, aaf2.mobs.MasterMob] = {}
        master_slots: dict[str, dict[str, aaf2.mobslots.TimelineMobSlot]] = {}
        tape_mobs: dict[str, aaf2.mobs.SourceMob] = {}

        for src_id, src_ir in media_sources.items():
            edit_rate = src_ir.edit_rate if src_ir.edit_rate is not None else default_edit_rate
            tape_duration = max(src_ir.duration_frames, 108000)

            slots_dict: dict[str, aaf2.mobslots.TimelineMobSlot] = {}

            # Audio-only source
            if src_ir.has_audio and not src_ir.has_video:
                audio_src_mob, master_mob = attach_audio_source_and_essence(
                    f, src_ir, edit_rate, embed_audio=embed_audio
                )
                master_mobs[src_id] = master_mob
                tape_mobs[src_id] = audio_src_mob
                for s in master_mob.slots:
                    if s.media_kind == "sound":
                        slots_dict["sound"] = s
                master_slots[src_id] = slots_dict
                continue

            tape_mob = f.create.SourceMob(src_ir.reel_name or src_ir.name)
            tape_mob.mob_id = deterministic_mob_id(f"tape:{src_ir.source_id}")
            tape_mob.descriptor = f.create.ImportDescriptor()
            if src_ir.file_path:
                loc = f.create.NetworkLocator()
                loc["URLString"].value = Path(src_ir.file_path).resolve().as_uri()
                tape_mob.descriptor["Locator"].append(loc)
            f.content.mobs.append(tape_mob)
            tape_mobs[src_id] = tape_mob

            tape_slot_pic = None
            tape_slot_snd = None

            if src_ir.has_video:
                tape_slot_pic = tape_mob.create_empty_slot(edit_rate, media_kind="picture")
                tape_slot_pic.segment.length = tape_duration
            if not src_ir.has_video and not src_ir.has_audio:
                tape_slot_pic = tape_mob.create_empty_slot(edit_rate, media_kind="picture")
                tape_slot_pic.segment.length = tape_duration

            master_mob = f.create.MasterMob(src_ir.name)
            master_mob.mob_id = deterministic_mob_id(f"master:{src_ir.source_id}")
            f.content.mobs.append(master_mob)
            master_mobs[src_id] = master_mob

            if tape_slot_pic is not None:
                master_slot_pic = master_mob.create_picture_slot(edit_rate)
                master_slot_pic.segment = tape_mob.create_source_clip(
                    slot_id=tape_slot_pic.slot_id, start=0, length=tape_slot_pic.segment.length
                )
                slots_dict["picture"] = master_slot_pic

            if src_ir.has_audio:
                embedded = False
                if embed_audio and src_ir.file_path:
                    snd_path = Path(src_ir.file_path).resolve()
                    if snd_path.exists() and snd_path.suffix.lower() == ".wav":
                        try:
                            audio_src_mob, _ = attach_audio_source_and_essence(
                                f, src_ir, edit_rate, embed_audio=True
                            )
                            for s in master_mob.slots:
                                if s.media_kind == "sound":
                                    slots_dict["sound"] = s
                                    embedded = True
                                    break
                        except Exception:
                            embedded = False

                if not embedded:
                    tape_slot_snd = tape_mob.create_empty_slot(edit_rate, media_kind="sound")
                    tape_slot_snd.segment.length = tape_duration
                    master_slot_snd = master_mob.create_sound_slot(edit_rate)
                    master_slot_snd.segment = tape_mob.create_source_clip(
                        slot_id=tape_slot_snd.slot_id,
                        start=0,
                        length=tape_slot_snd.segment.length,
                        media_kind="sound",
                    )
                    slots_dict["sound"] = master_slot_snd

            master_slots[src_id] = slots_dict

        # Process sequences
        for seq_ir in sequences:
            comp_mob = f.create.CompositionMob(seq_ir.name)
            comp_mob.mob_id = deterministic_mob_id(f"comp:{seq_ir.seq_id}")
            comp_mob.usage = "Usage_TopLevel"
            f.content.mobs.append(comp_mob)

            for track_ir in seq_ir.tracks:
                slot = comp_mob.create_timeline_slot(seq_ir.edit_rate)
                slot.name = track_ir.name
                seq = f.create.Sequence(media_kind=track_ir.kind)
                cursor_frame = 0

                sorted_clips = sorted(
                    track_ir.clips,
                    key=lambda c: (c.timeline_in_frames, c.timeline_out_frames),
                )
                for clip_ir in sorted_clips:
                    if clip_ir.timeline_in_frames > cursor_frame:
                        gap = clip_ir.timeline_in_frames - cursor_frame
                        seq.components.append(f.create.Filler(track_ir.kind, gap))

                    # Ensure master mob has the required slot
                    src_slots = master_slots.get(clip_ir.source_id, {})
                    if track_ir.kind not in src_slots:
                        m_mob = master_mobs[clip_ir.source_id]
                        t_mob = tape_mobs[clip_ir.source_id]
                        t_slot = t_mob.create_empty_slot(seq_ir.edit_rate, media_kind=track_ir.kind)
                        t_slot.segment.length = 108000
                        if track_ir.kind == "picture":
                            m_slot = m_mob.create_picture_slot(seq_ir.edit_rate)
                        else:
                            m_slot = m_mob.create_sound_slot(seq_ir.edit_rate)
                        m_slot.segment = t_mob.create_source_clip(
                            slot_id=t_slot.slot_id,
                            start=0,
                            length=t_slot.segment.length,
                            media_kind=track_ir.kind,
                        )
                        src_slots[track_ir.kind] = m_slot
                        master_slots[clip_ir.source_id] = src_slots

                    target_slot = src_slots[track_ir.kind]
                    src_clip = master_mobs[clip_ir.source_id].create_source_clip(
                        slot_id=target_slot.slot_id,
                        start=clip_ir.source_in_frames,
                        length=clip_ir.duration_frames,
                    )
                    if track_ir.kind == "sound":
                        apply_audio_automation(f, src_clip, clip_ir)
                    seq.components.append(src_clip)
                    cursor_frame = clip_ir.timeline_out_frames

                if cursor_frame < seq_ir.duration_frames:
                    gap = seq_ir.duration_frames - cursor_frame
                    seq.components.append(f.create.Filler(track_ir.kind, gap))

                slot.segment = seq

            # Markers and Comments on CompositionMob
            marker_idx = 0
            for m in seq_ir.markers:
                comment_text = (
                    f"[{m.color.upper()}] {m.name}: {m.comment}"
                    if m.comment
                    else f"[{m.color.upper()}] {m.name}"
                )
                comp_mob.comments[f"MARKER_{marker_idx}_{m.frame_offset}"] = comment_text
                marker_idx += 1

            for track_ir in seq_ir.tracks:
                for clip_ir in track_ir.clips:
                    for m in clip_ir.markers:
                        frame = clip_ir.timeline_in_frames + m.frame_offset
                        comment_text = (
                            f"[{m.color.upper()}] {m.name}: {m.comment}"
                            if m.comment
                            else f"[{m.color.upper()}] {m.name}"
                        )
                        comp_mob.comments[f"MARKER_{marker_idx}_{frame}"] = comment_text
                        marker_idx += 1

                    for eff in clip_ir.unsupported_effects:
                        frame = clip_ir.timeline_in_frames
                        desc = f"[RED] Effect: {eff.effect_name}"
                        if eff.parameters_summary:
                            desc += f" ({eff.parameters_summary})"
                        comp_mob.comments[f"EFFECT_{marker_idx}_{frame}"] = desc
                        marker_idx += 1

    return out_path
