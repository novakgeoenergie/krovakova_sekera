from __future__ import annotations

from pathlib import Path

from machete.ir.schema import MediaSourceIR, SequenceIR
from machete.ir.timecode import frames_to_smpte_tc


def export_sequence_to_edl(
    seq: SequenceIR,
    media_sources: dict[str, MediaSourceIR],
    output_path: str | Path,
) -> Path:
    """Export a SequenceIR to a CMX 3600 format EDL text file."""
    out_path = Path(output_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Determine primary track: first picture track, else first sound track
    primary_track = None
    for track in seq.tracks:
        if track.kind == "picture":
            primary_track = track
            break
    if primary_track is None:
        for track in seq.tracks:
            if track.kind == "sound":
                primary_track = track
                break

    lines: list[str] = [
        f"TITLE: {seq.name}",
        "FCM: DROP FRAME" if seq.drop_frame else "FCM: NON-DROP FRAME",
        "",
    ]

    seen_markers: set[tuple[int, str]] = set()

    if primary_track is not None:
        sorted_clips = sorted(primary_track.clips, key=lambda c: c.timeline_in_frames)
        event_num = 1
        track_type = "V" if primary_track.kind == "picture" else "A"
        edit_type = "C"

        for clip in sorted_clips:
            source = media_sources.get(clip.source_id)
            reel_name = source.reel_name if (source and source.reel_name) else "AX"
            reel = reel_name[:8].ljust(8)

            src_in_tc = frames_to_smpte_tc(clip.source_in_frames, seq.edit_rate, seq.drop_frame)
            src_out_tc = frames_to_smpte_tc(
                clip.source_in_frames + clip.duration_frames, seq.edit_rate, seq.drop_frame
            )
            rec_in_tc = frames_to_smpte_tc(clip.timeline_in_frames, seq.edit_rate, seq.drop_frame)
            rec_out_tc = frames_to_smpte_tc(clip.timeline_out_frames, seq.edit_rate, seq.drop_frame)

            lines.append(
                f"{event_num:03d}  {reel} {track_type:<5} {edit_type:<8} {src_in_tc} {src_out_tc} {rec_in_tc} {rec_out_tc}"
            )
            lines.append(f"* FROM CLIP NAME: {clip.name}")

            for marker in clip.markers:
                marker_tc = frames_to_smpte_tc(marker.frame_offset, seq.edit_rate, seq.drop_frame)
                color_str = (marker.color or "red").upper()
                lines.append(f"* LOC: {marker_tc} {color_str:<7} {marker.name}")
                seen_markers.add((marker.frame_offset, marker.name))

            marker_names = {m.name for m in clip.markers}
            for eff in clip.unsupported_effects:
                eff_name = f"ADOBE FX: {eff.effect_name}"
                if eff_name not in marker_names and eff.effect_name not in marker_names:
                    eff_tc = frames_to_smpte_tc(clip.timeline_in_frames, seq.edit_rate, seq.drop_frame)
                    lines.append(f"* LOC: {eff_tc} RED     {eff_name}")
                    seen_markers.add((clip.timeline_in_frames, eff_name))

            event_num += 1

    for marker in seq.markers:
        if (marker.frame_offset, marker.name) not in seen_markers:
            marker_tc = frames_to_smpte_tc(marker.frame_offset, seq.edit_rate, seq.drop_frame)
            color_str = (marker.color or "red").upper()
            lines.append(f"* LOC: {marker_tc} {color_str:<7} {marker.name}")
            seen_markers.add((marker.frame_offset, marker.name))

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
