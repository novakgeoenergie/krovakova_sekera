from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
import re
from typing import Any

import aaf2

from machete.exporters.aaf_core import deterministic_mob_id
from machete.ir import (
    ClipIR,
    ProjectIR,
    SequenceIR,
    TrackIR,
    frames_to_smpte_tc,
)

_WARN_RE = re.compile(
    r"^\[(?P<tc>[^/]+)\s*/\s*frame\s*(?P<frame>\d+)\]\s*(?P<loc>[^:]+):\s*(?P<desc>.*)$"
)


class WarningsList(list):
    """List of warning strings that supports substring matching with the `in` operator."""

    def __contains__(self, item: object) -> bool:
        if super().__contains__(item):
            return True
        if isinstance(item, str):
            return any(item in s for s in self)
        return False


@dataclass
class VerificationReport:
    """AAF Verification Report containing validation status, counts, and error/warning details."""

    is_valid: bool
    sequence_name: str
    total_tracks: int
    total_clips: int
    total_fillers: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=WarningsList)
    warning_details: list[dict[str, Any]] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.warnings, WarningsList):
            self.warnings = WarningsList(self.warnings)

    def to_markdown(self) -> str:
        """Formats a clean summary Markdown table for the editor:

        - Sequence name and status (VALIDNÍ / NEVALIDNÍ)
        - Counts of tracks, clips, fillers, and errors
        - If warnings exist (e.g. unsupported effects / red markers), a table with
          SMPTE timecode (or frame), track/clip info, and description.
        """
        status_text = "VALIDNÍ" if self.is_valid else "NEVALIDNÍ"
        lines: list[str] = [
            f"# Přehled ověření AAF: {self.sequence_name}",
            "",
            "| Vlastnost | Hodnota |",
            "| :--- | :--- |",
            f"| **Sekvence** | {self.sequence_name} |",
            f"| **Stav** | {status_text} |",
            f"| **Počet stop (Tracks)** | {self.total_tracks} |",
            f"| **Počet klipů (Clips)** | {self.total_clips} |",
            f"| **Počet mezer (Fillers)** | {self.total_fillers} |",
            f"| **Chyby (Errors)** | {len(self.errors)} |",
            "",
        ]

        if self.errors:
            lines.extend([
                f"### Chyby ({len(self.errors)})",
                "",
            ])
            for err in self.errors:
                lines.append(f"- ❌ {err}")
            lines.append("")

        if self.warnings:
            lines.extend([
                f"### Upozornění ({len(self.warnings)})",
                "",
                "| SMPTE Timecode | Frame | Stopa / Klip | Popis |",
                "| :--- | :--- | :--- | :--- |",
            ])
            if self.warning_details and len(self.warning_details) == len(self.warnings):
                for w in self.warning_details:
                    tc = w.get("tc", "-")
                    frame = str(w.get("frame", "-"))
                    loc = w.get("location", "-")
                    desc = w.get("description", "-")
                    lines.append(f"| {tc} | {frame} | {loc} | {desc} |")
            else:
                for w in self.warnings:
                    m = _WARN_RE.match(w)
                    if m:
                        d = m.groupdict()
                        lines.append(
                            f"| {d['tc'].strip()} | {d['frame'].strip()} | {d['loc'].strip()} | {d['desc'].strip()} |"
                        )
                    else:
                        lines.append(f"| - | - | - | {w} |")
            lines.append("")

        return "\n".join(lines)


def verify_aaf_against_ir(
    aaf_path: str | Path,
    expected_ir: ProjectIR,
) -> VerificationReport:
    """Verify an exported AAF file against an expected ProjectIR representation.

    - Opens `aaf_path` via `aaf2.open(str(aaf_path), 'r')`.
    - Finds CompositionMob corresponding to sequences in `expected_ir`.
    - For each timeline slot / track:
      - Walks `slot.segment.components`.
      - Checks no component has `length <= 0`.
      - Verifies sum of all component lengths equals `seq_ir.duration_frames`.
      - Tracks cursor starting from 0 to verify `SourceClip` positions and lengths
        match the expected `ClipIR`s on that track with zero frame tolerance (delta == 0).
      - If mismatch found, adds to `errors`.
    - Inspects comments / markers on `comp_mob` and/or `expected_ir` clips for
      unsupported effects (e.g. Warp Stabilizer) and collects into `warnings`.
    - Sets `is_valid = len(errors) == 0`.
    - Returns `VerificationReport`.
    """
    path = Path(aaf_path).resolve()
    errors: list[str] = []
    warnings = WarningsList()
    warning_details: list[dict[str, Any]] = []

    if not path.exists():
        return VerificationReport(
            is_valid=False,
            sequence_name=expected_ir.sequences[0].name if expected_ir.sequences else "Unknown",
            total_tracks=0,
            total_clips=0,
            total_fillers=0,
            errors=[f"AAF file does not exist: {path}"],
            warnings=warnings,
            warning_details=warning_details,
        )

    seq_names = [s.name for s in expected_ir.sequences]
    sequence_name = (
        ", ".join(seq_names)
        if len(seq_names) > 1
        else (seq_names[0] if seq_names else expected_ir.project_name or "Unknown")
    )

    total_tracks = 0
    total_clips = 0
    total_fillers = 0

    with aaf2.open(str(path), "r") as f:
        comp_mobs_by_name: dict[str, aaf2.mobs.CompositionMob] = {}
        comp_mobs_by_id: dict[Any, aaf2.mobs.CompositionMob] = {}

        for mob in f.content.mobs:
            if isinstance(mob, aaf2.mobs.CompositionMob):
                comp_mobs_by_name[mob.name] = mob
                comp_mobs_by_id[mob.mob_id] = mob

        for seq_ir in expected_ir.sequences:
            expected_mob_id = deterministic_mob_id(f"comp:{seq_ir.seq_id}")
            comp_mob = comp_mobs_by_name.get(seq_ir.name) or comp_mobs_by_id.get(expected_mob_id)

            if comp_mob is None:
                errors.append(
                    f"CompositionMob for sequence '{seq_ir.name}' (id={seq_ir.seq_id}) not found in AAF"
                )
                continue

            # Build slots lookup
            slots_by_name: dict[str, aaf2.mobslots.TimelineMobSlot] = {}
            timeline_slots: list[aaf2.mobslots.TimelineMobSlot] = []

            for slot in comp_mob.slots:
                if isinstance(slot, aaf2.mobslots.TimelineMobSlot):
                    timeline_slots.append(slot)
                    if slot.name:
                        slots_by_name[slot.name] = slot

            for track_ir in seq_ir.tracks:
                total_tracks += 1
                slot = slots_by_name.get(track_ir.name)
                if slot is None and 0 <= track_ir.track_index < len(timeline_slots):
                    slot = timeline_slots[track_ir.track_index]

                if slot is None:
                    errors.append(
                        f"Sequence '{seq_ir.name}': Track '{track_ir.name}' (index {track_ir.track_index}) "
                        f"not found in CompositionMob slots"
                    )
                    continue

                if slot.media_kind and str(slot.media_kind).lower() != track_ir.kind.lower():
                    errors.append(
                        f"Sequence '{seq_ir.name}', Track '{track_ir.name}': Media kind mismatch - "
                        f"AAF slot has '{slot.media_kind}', expected IR track kind '{track_ir.kind}'"
                    )

                # Extract components
                if hasattr(slot.segment, "components"):
                    components = list(slot.segment.components)
                elif isinstance(slot.segment, aaf2.components.Component):
                    components = [slot.segment]
                else:
                    components = []

                # 1. Check no component has length <= 0
                for comp_idx, comp in enumerate(components):
                    comp_len = comp.length
                    if comp_len <= 0:
                        errors.append(
                            f"Sequence '{seq_ir.name}', Track '{track_ir.name}', component {comp_idx} "
                            f"({type(comp).__name__}) has invalid length {comp_len} <= 0"
                        )

                # 2. Verify sum of all component lengths equals seq_ir.duration_frames
                track_duration = sum(c.length for c in components)
                if track_duration != seq_ir.duration_frames:
                    delta = track_duration - seq_ir.duration_frames
                    errors.append(
                        f"Sequence '{seq_ir.name}', Track '{track_ir.name}': total track length "
                        f"{track_duration} != sequence duration {seq_ir.duration_frames} (delta={delta})"
                    )

                # 3. Count SourceClips and Fillers, track cursor starting from 0
                actual_clips: list[tuple[int, int, aaf2.components.SourceClip]] = []
                cursor = 0
                for comp in components:
                    if isinstance(comp, aaf2.components.SourceClip):
                        total_clips += 1
                        actual_clips.append((cursor, comp.length, comp))
                    elif isinstance(comp, aaf2.components.Filler):
                        total_fillers += 1
                    cursor += comp.length

                # 4. Verify SourceClip positions and lengths match expected ClipIRs with zero tolerance
                expected_clips = sorted(
                    track_ir.clips,
                    key=lambda c: (c.timeline_in_frames, c.timeline_out_frames),
                )

                if len(actual_clips) != len(expected_clips):
                    errors.append(
                        f"Sequence '{seq_ir.name}', Track '{track_ir.name}': clip count mismatch - "
                        f"found {len(actual_clips)} SourceClips in AAF, expected {len(expected_clips)} from IR"
                    )

                for i in range(min(len(actual_clips), len(expected_clips))):
                    actual_start, actual_len, comp = actual_clips[i]
                    exp_clip = expected_clips[i]

                    # Verify start position (timeline_in)
                    start_delta = actual_start - exp_clip.timeline_in_frames
                    if start_delta != 0:
                        errors.append(
                            f"Sequence '{seq_ir.name}', Track '{track_ir.name}', Clip {i} ('{exp_clip.name}'): "
                            f"timeline_in mismatch - AAF has {actual_start}, expected {exp_clip.timeline_in_frames} (delta={start_delta})"
                        )

                    # Verify duration (length)
                    len_delta = actual_len - exp_clip.duration_frames
                    if len_delta != 0:
                        errors.append(
                            f"Sequence '{seq_ir.name}', Track '{track_ir.name}', Clip {i} ('{exp_clip.name}'): "
                            f"duration mismatch - AAF has {actual_len}, expected {exp_clip.duration_frames} (delta={len_delta})"
                        )

                    # Verify source_in
                    if hasattr(comp, "start") and comp.start is not None and comp.start != exp_clip.source_in_frames:
                        src_delta = comp.start - exp_clip.source_in_frames
                        errors.append(
                            f"Sequence '{seq_ir.name}', Track '{track_ir.name}', Clip {i} ('{exp_clip.name}'): "
                            f"source_in mismatch - AAF has {comp.start}, expected {exp_clip.source_in_frames} (delta={src_delta})"
                        )

        # Inspect comments / markers on comp_mob and/or expected_ir clips for unsupported effects
        seen_warn_keys: set[str] = set()

        for seq_ir in expected_ir.sequences:
            for track_ir in seq_ir.tracks:
                for clip_ir in track_ir.clips:
                    # Unsupported effects on clips
                    for eff in clip_ir.unsupported_effects:
                        frame = clip_ir.timeline_in_frames
                        tc = frames_to_smpte_tc(frame, seq_ir.edit_rate, seq_ir.drop_frame)
                        loc = f"Track '{track_ir.name}', Clip '{clip_ir.name}'"
                        desc = f"Unsupported effect: {eff.effect_name}"
                        if eff.parameters_summary:
                            desc += f" ({eff.parameters_summary})"
                        key = f"{tc}:{loc}:{eff.effect_name}"
                        if key not in seen_warn_keys:
                            seen_warn_keys.add(key)
                            warn_str = f"[{tc} / frame {frame}] {loc}: {desc}"
                            warnings.append(warn_str)
                            warning_details.append({
                                "tc": tc,
                                "frame": frame,
                                "location": loc,
                                "description": desc,
                                "effect_name": eff.effect_name,
                            })

                    # Markers on clips (red or unsupported fx)
                    for m in clip_ir.markers:
                        is_red = m.color.lower() == "red"
                        is_fx = (
                            "adobe fx" in m.name.lower()
                            or "unsupported" in m.name.lower()
                            or "warp stabilizer" in m.name.lower()
                        )
                        if is_red or is_fx:
                            frame = clip_ir.timeline_in_frames + m.frame_offset
                            tc = frames_to_smpte_tc(frame, seq_ir.edit_rate, seq_ir.drop_frame)
                            loc = f"Track '{track_ir.name}', Clip '{clip_ir.name}'"
                            desc = f"Marker [{m.color.upper()}]: {m.name}"
                            if m.comment:
                                desc += f" - {m.comment}"
                            key = f"{tc}:{loc}:{m.name}"
                            if key not in seen_warn_keys:
                                seen_warn_keys.add(key)
                                warn_str = f"[{tc} / frame {frame}] {loc}: {desc}"
                                warnings.append(warn_str)
                                warning_details.append({
                                    "tc": tc,
                                    "frame": frame,
                                    "location": loc,
                                    "description": desc,
                                    "effect_name": m.name,
                                })

            # Sequence markers (red or unsupported)
            for m in seq_ir.markers:
                if m.color.lower() == "red" or "unsupported" in m.name.lower():
                    frame = m.frame_offset
                    tc = frames_to_smpte_tc(frame, seq_ir.edit_rate, seq_ir.drop_frame)
                    loc = f"Sequence '{seq_ir.name}'"
                    desc = f"Marker [{m.color.upper()}]: {m.name}"
                    if m.comment:
                        desc += f" - {m.comment}"
                    key = f"{tc}:{loc}:{m.name}"
                    if key not in seen_warn_keys:
                        seen_warn_keys.add(key)
                        warn_str = f"[{tc} / frame {frame}] {loc}: {desc}"
                        warnings.append(warn_str)
                        warning_details.append({
                            "tc": tc,
                            "frame": frame,
                            "location": loc,
                            "description": desc,
                            "effect_name": m.name,
                        })

        # Also inspect comp_mob.comments from AAF
        for seq_ir in expected_ir.sequences:
            expected_mob_id = deterministic_mob_id(f"comp:{seq_ir.seq_id}")
            comp_mob = comp_mobs_by_name.get(seq_ir.name) or comp_mobs_by_id.get(expected_mob_id)
            if comp_mob is not None and hasattr(comp_mob, "comments"):
                for k, v in comp_mob.comments.items():
                    v_str = str(v)
                    is_unsupported = (
                        "Warp Stabilizer" in v_str
                        or "Effect:" in v_str
                        or "ADOBE FX" in v_str
                        or "[RED]" in v_str
                        or "unsupported" in v_str.lower()
                    )
                    if is_unsupported:
                        parts = k.split("_")
                        frame = int(parts[-1]) if len(parts) >= 3 and parts[-1].isdigit() else 0
                        tc = frames_to_smpte_tc(frame, seq_ir.edit_rate, seq_ir.drop_frame)
                        # Check if already covered by an existing warning
                        already_present = any(
                            d["frame"] == frame
                            and (
                                d["description"] in v_str
                                or v_str in d["description"]
                                or any(
                                    sub in d["description"]
                                    for sub in (
                                        v_str.replace("[RED]", "").replace("Effect:", "").strip().split(":")
                                    )
                                    if len(sub.strip()) > 3
                                )
                            )
                            for d in warning_details
                        )
                        if not already_present:
                            key = f"{tc}:comp_mob:{v_str}"
                            if key not in seen_warn_keys:
                                seen_warn_keys.add(key)
                                loc = f"CompositionMob '{comp_mob.name}'"
                                warn_str = f"[{tc} / frame {frame}] {loc}: {v_str}"
                                warnings.append(warn_str)
                                warning_details.append({
                                    "tc": tc,
                                    "frame": frame,
                                    "location": loc,
                                    "description": v_str,
                                    "effect_name": v_str,
                                })

    is_valid = len(errors) == 0

    return VerificationReport(
        is_valid=is_valid,
        sequence_name=sequence_name,
        total_tracks=total_tracks,
        total_clips=total_clips,
        total_fillers=total_fillers,
        errors=errors,
        warnings=warnings,
        warning_details=warning_details,
    )
