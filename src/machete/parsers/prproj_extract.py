from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import xml.etree.ElementTree as ET

from machete.ir.schema import (
    ClipIR,
    EffectNoticeIR,
    KeyframeIR,
    MarkerIR,
    MediaSourceIR,
    ProjectIR,
    SequenceIR,
    TrackIR,
)
from machete.ir.timecode import EDIT_RATES, PPRO_TICKS_PER_SEC, ticks_to_frames
from machete.parsers.prproj_index import PrProjIndex


def _get_obj_id(elem: ET.Element) -> str:
    return elem.attrib.get("ObjectID") or elem.attrib.get("ObjectUID") or str(id(elem))


def _extract_edit_rate(seq_elem: ET.Element) -> Fraction:
    tpf = seq_elem.findtext("TicksPerFrame") or seq_elem.findtext("FrameRate")
    if tpf:
        ticks = int(tpf)
        if ticks > 0:
            return Fraction(PPRO_TICKS_PER_SEC, ticks)

    rate_elem = seq_elem.find("Rate")
    if rate_elem is not None:
        num = rate_elem.findtext("Numerator")
        den = rate_elem.findtext("Denominator")
        if num and den and int(den) > 0:
            return Fraction(int(num), int(den))

    er = seq_elem.findtext("EditRate")
    if er:
        if er in EDIT_RATES:
            return EDIT_RATES[er]
        try:
            return Fraction(er)
        except (ValueError, ZeroDivisionError):
            pass

    return Fraction(25, 1)


def _find_track_groups(seq_elem: ET.Element, index: PrProjIndex) -> list[ET.Element]:
    track_groups: list[ET.Element] = []
    tg_container = seq_elem.find("TrackGroups")
    if tg_container is not None:
        for child in tg_container:
            sec = child.find("Second")
            if sec is not None:
                resolved_sec = index.resolve(sec)
                if resolved_sec is not None and resolved_sec not in track_groups:
                    track_groups.append(resolved_sec)
                    continue
            resolved = index.resolve(child)
            if resolved is not None and resolved not in track_groups:
                track_groups.append(resolved)
    for tag in ("VideoTrackGroup", "AudioTrackGroup"):
        resolved = index.deref(seq_elem, tag)
        if resolved is not None and resolved not in track_groups:
            track_groups.append(resolved)
    return track_groups


def _find_tracks_in_group(tg_elem: ET.Element, index: PrProjIndex) -> list[ET.Element]:
    tracks: list[ET.Element] = []
    sub_tg = tg_elem.find("TrackGroup")
    target_tg = sub_tg if sub_tg is not None else tg_elem
    tracks_elem = target_tg.find("Tracks")
    if tracks_elem is None and target_tg is not tg_elem:
        tracks_elem = tg_elem.find("Tracks")
    if tracks_elem is not None:
        for child in tracks_elem:
            resolved = index.resolve(child)
            if resolved is not None and resolved not in tracks:
                tracks.append(resolved)
    for child in target_tg.findall("Track"):
        resolved = index.resolve(child)
        if resolved is not None and resolved not in tracks:
            tracks.append(resolved)
    return tracks


def _find_track_items(track_elem: ET.Element, index: PrProjIndex) -> list[ET.Element]:
    items: list[ET.Element] = []
    ct = track_elem.find("ClipTrack")
    search_root = ct if ct is not None else track_elem
    for cont_name in ("ClipItems", "TrackItems", "ClipTrackItems"):
        cont = search_root.find(cont_name)
        if cont is not None:
            for child in cont:
                if child.tag == "TrackItems":
                    for sub in child:
                        resolved = index.resolve(sub)
                        if resolved is not None and resolved not in items:
                            items.append(resolved)
                else:
                    resolved = index.resolve(child)
                    if resolved is not None and resolved not in items:
                        items.append(resolved)
    for child in search_root.findall("TrackItem"):
        resolved = index.resolve(child)
        if resolved is not None and resolved not in items:
            items.append(resolved)
    return items


def _extract_sequence(
    seq_elem: ET.Element,
    index: PrProjIndex,
    flatten_nested: bool,
    call_stack: set[str],
) -> SequenceIR:
    seq_id = _get_obj_id(seq_elem)
    if seq_id in call_stack:
        raise ValueError(f"Circular sequence reference detected: {seq_id}")
    call_stack = set(call_stack)
    call_stack.add(seq_id)

    name = seq_elem.findtext("Name") or "Sequence"
    edit_rate = _extract_edit_rate(seq_elem)
    drop_frame = (seq_elem.findtext("DropFrame") or "").lower() == "true"
    sr_text = seq_elem.findtext("SampleRate")
    sample_rate = int(sr_text) if sr_text else 48000

    seq_markers: list[MarkerIR] = []
    markers_container = seq_elem.find("Markers")
    if markers_container is not None:
        for m_elem in index.deref_all(markers_container, "Marker"):
            m_start = int(m_elem.findtext("Start") or m_elem.findtext("Time") or "0")
            m_offset = ticks_to_frames(m_start, edit_rate)
            m_dur_text = m_elem.findtext("Duration")
            m_dur = ticks_to_frames(int(m_dur_text), edit_rate) if m_dur_text else 1
            if m_dur < 1:
                m_dur = 1
            m_name = m_elem.findtext("Name") or "Marker"
            m_comment = m_elem.findtext("Comment") or ""
            m_color = (m_elem.findtext("Color") or "red").lower()
            valid_colors = {"red", "yellow", "green", "blue", "cyan", "magenta", "white", "black"}
            if m_color not in valid_colors:
                m_color = "red"
            seq_markers.append(
                MarkerIR(
                    frame_offset=m_offset,
                    duration_frames=m_dur,
                    name=m_name,
                    comment=m_comment,
                    color=m_color,  # type: ignore
                )
            )

    track_groups = _find_track_groups(seq_elem, index)
    tracks: list[TrackIR] = []
    kind_counts: dict[str, int] = {"picture": 0, "sound": 0}

    for tg in track_groups:
        gmt_raw = tg.findtext("MediaType") or ""
        group_media_type = gmt_raw if gmt_raw else ("Video" if "Video" in tg.tag else ("Audio" if "Audio" in tg.tag else ""))
        group_tracks = _find_tracks_in_group(tg, index)

        for track_elem in group_tracks:
            media_type = track_elem.findtext("MediaType") or group_media_type
            track_name = track_elem.findtext("Name") or ""
            if media_type.lower() == "video" or track_name.startswith("V"):
                kind = "picture"
            elif media_type.lower() == "audio" or track_name.startswith("A"):
                kind = "sound"
            else:
                kind = "picture"

            idx_str = track_elem.findtext("Index")
            if idx_str is not None:
                track_index = int(idx_str)
            else:
                track_index = kind_counts[kind]
            kind_counts[kind] += 1

            track_items = _find_track_items(track_elem, index)
            clips: list[ClipIR] = []

            for item_elem in track_items:
                cti_elem = item_elem.find("ClipTrackItem")
                ti_elem = (cti_elem.find("TrackItem") if cti_elem is not None else None) or item_elem
                subclip_elem = (
                    index.deref(cti_elem, "SubClip")
                    if cti_elem is not None
                    else index.deref(item_elem, "SubClip")
                )
                clip_elem = (
                    index.deref(subclip_elem, "Clip")
                    if subclip_elem is not None
                    else index.deref(item_elem, "Clip")
                )
                if clip_elem is None:
                    clip_elem = subclip_elem if subclip_elem is not None else item_elem

                child_seq_elem = None
                source_elem = index.deref(clip_elem, "Source")
                if source_elem is None and clip_elem is not None:
                    inner_c = clip_elem.find("Clip")
                    if inner_c is not None:
                        source_elem = index.deref(inner_c, "Source")

                candidates = [
                    index.deref(clip_elem, "Sequence"),
                    index.deref(source_elem, "Sequence") if source_elem is not None else None,
                    index.deref(item_elem, "Sequence"),
                    index.deref(subclip_elem, "Sequence") if subclip_elem is not None else None,
                ]
                for cand in candidates:
                    if cand is not None and (cand.tag == "Sequence" or cand.tag.endswith("Sequence")):
                        child_seq_elem = cand
                        break

                p_start_ticks = int(
                    ti_elem.findtext("Start")
                    or ti_elem.findtext("StartPoint")
                    or item_elem.findtext("Start")
                    or item_elem.findtext("StartPoint")
                    or "0"
                )
                p_end_ticks = int(
                    ti_elem.findtext("End")
                    or ti_elem.findtext("EndPoint")
                    or item_elem.findtext("End")
                    or item_elem.findtext("EndPoint")
                    or "0"
                )
                p_in_ticks = int(
                    ti_elem.findtext("In")
                    or ti_elem.findtext("InPoint")
                    or (subclip_elem.findtext("In") if subclip_elem is not None else None)
                    or item_elem.findtext("In")
                    or item_elem.findtext("InPoint")
                    or "0"
                )

                parent_timeline_in = ticks_to_frames(p_start_ticks, edit_rate)
                parent_timeline_out = ticks_to_frames(p_end_ticks, edit_rate)
                child_source_in = ticks_to_frames(p_in_ticks, edit_rate)

                if parent_timeline_out <= parent_timeline_in and child_seq_elem is None:
                    continue

                if child_seq_elem is not None and flatten_nested:
                    child_seq_ir = _extract_sequence(child_seq_elem, index, flatten_nested=True, call_stack=call_stack)
                    matching_child_track = next(
                        (t for t in child_seq_ir.tracks if t.kind == kind and t.track_index == track_index),
                        None,
                    )
                    if matching_child_track is None:
                        matching_child_track = next(
                            (t for t in child_seq_ir.tracks if t.kind == kind and t.name == track_name),
                            None,
                        )
                    if matching_child_track is None:
                        matching_child_track = next(
                            (t for t in child_seq_ir.tracks if t.kind == kind),
                            None,
                        )

                    if matching_child_track is not None:
                        shift = parent_timeline_in - child_source_in
                        for child_clip in matching_child_track.clips:
                            raw_in = child_clip.timeline_in_frames + shift
                            raw_out = child_clip.timeline_out_frames + shift

                            clamped_in = max(raw_in, parent_timeline_in)
                            clamped_out = min(raw_out, parent_timeline_out)

                            if clamped_out <= clamped_in:
                                continue

                            delta_in = clamped_in - raw_in
                            new_source_in = child_clip.source_in_frames + delta_in

                            flattened_clip = child_clip.model_copy(deep=True)
                            flattened_clip.timeline_in_frames = clamped_in
                            flattened_clip.timeline_out_frames = clamped_out
                            flattened_clip.source_in_frames = new_source_in

                            for marker in flattened_clip.markers:
                                marker.frame_offset += shift
                                seq_markers.append(marker.model_copy(deep=True))

                            clips.append(flattened_clip)
                    continue

                clip_id = _get_obj_id(item_elem)
                clip_name = (
                    item_elem.findtext("Name")
                    or (subclip_elem.findtext("Name") if subclip_elem is not None else None)
                    or "Clip"
                )

                if child_seq_elem is not None:
                    source_id = _get_obj_id(child_seq_elem)
                else:
                    media_elem = None
                    if source_elem is not None:
                        media_elem = index.deref(source_elem, "Media")
                        if media_elem is None:
                            ms = source_elem.find("MediaSource")
                            if ms is not None:
                                media_elem = index.deref(ms, "Media")
                    if media_elem is None and clip_elem is not None:
                        media_elem = index.deref(clip_elem, "Media")
                    if media_elem is None and subclip_elem is not None:
                        media_elem = index.deref(subclip_elem, "Media")
                    if media_elem is None:
                        media_elem = index.deref(item_elem, "Media")
                    source_id = _get_obj_id(media_elem) if media_elem is not None else clip_id

                speed_str = item_elem.findtext("Speed") or (clip_elem.findtext("Speed") if clip_elem is not None else None)
                speed_ratio = Fraction(speed_str) if speed_str else Fraction(1, 1)

                clip_markers: list[MarkerIR] = []
                unsupported_effects: list[EffectNoticeIR] = []
                volume_keyframes: list[KeyframeIR] = []
                pan_keyframes: list[KeyframeIR] = []

                components: list[ET.Element] = []
                seen_comp_ids: set[str] = set()
                for container in (item_elem, clip_elem):
                    if container is not None:
                        comps_elem = container.find("Components")
                        if comps_elem is not None:
                            for child in comps_elem:
                                resolved = index.resolve(child)
                                if resolved is None:
                                    resolved = child
                                cid = _get_obj_id(resolved)
                                if cid not in seen_comp_ids:
                                    seen_comp_ids.add(cid)
                                    components.append(resolved)

                for comp in components:
                    comp_name = comp.findtext("DisplayName") or comp.findtext("Name") or comp.tag
                    if comp_name in ("Volume", "Channel Volume"):
                        seen_kf_ids: set[str] = set()
                        for kf in comp.findall(".//Keyframe"):
                            resolved_kf = index.resolve(kf)
                            if resolved_kf is None:
                                resolved_kf = kf
                            kf_id = _get_obj_id(resolved_kf)
                            if kf_id in seen_kf_ids:
                                continue
                            seen_kf_ids.add(kf_id)
                            t_str = resolved_kf.attrib.get("Time") or resolved_kf.findtext("Time")
                            v_str = resolved_kf.attrib.get("Value") or resolved_kf.findtext("Value")
                            if t_str is not None and v_str is not None:
                                kf_offset = ticks_to_frames(int(t_str), edit_rate)
                                volume_keyframes.append(KeyframeIR(offset_frames=kf_offset, value=Fraction(v_str)))
                    elif comp_name == "Panner":
                        seen_kf_ids = set()
                        for kf in comp.findall(".//Keyframe"):
                            resolved_kf = index.resolve(kf)
                            if resolved_kf is None:
                                resolved_kf = kf
                            kf_id = _get_obj_id(resolved_kf)
                            if kf_id in seen_kf_ids:
                                continue
                            seen_kf_ids.add(kf_id)
                            t_str = resolved_kf.attrib.get("Time") or resolved_kf.findtext("Time")
                            v_str = resolved_kf.attrib.get("Value") or resolved_kf.findtext("Value")
                            if t_str is not None and v_str is not None:
                                kf_offset = ticks_to_frames(int(t_str), edit_rate)
                                pan_keyframes.append(KeyframeIR(offset_frames=kf_offset, value=Fraction(v_str)))
                    elif comp_name not in ("Motion", "Opacity"):
                        unsupported_effects.append(
                            EffectNoticeIR(
                                effect_name=comp_name,
                                parameters_summary=f"Unsupported Adobe effect: {comp_name}",
                                requires_manual_recreate=True,
                            )
                        )
                        eff_marker = MarkerIR(
                            frame_offset=parent_timeline_in,
                            duration_frames=1,
                            name=f"ADOBE FX: {comp_name}",
                            comment=f"Adobe effect '{comp_name}' not supported",
                            color="red",
                        )
                        clip_markers.append(eff_marker)
                        seq_markers.append(eff_marker.model_copy(deep=True))

                if speed_ratio != Fraction(1, 1):
                    speed_fx = f"Speed Ramp ({speed_ratio})"
                    unsupported_effects.append(
                        EffectNoticeIR(
                            effect_name=speed_fx,
                            parameters_summary=f"Speed ratio: {speed_ratio}",
                            requires_manual_recreate=True,
                        )
                    )
                    speed_marker = MarkerIR(
                        frame_offset=parent_timeline_in,
                        duration_frames=1,
                        name=f"ADOBE FX: {speed_fx}",
                        comment=f"Speed ratio: {speed_ratio}",
                        color="red",
                    )
                    clip_markers.append(speed_marker)
                    seq_markers.append(speed_marker.model_copy(deep=True))

                volume_keyframes.sort(key=lambda k: k.offset_frames)
                pan_keyframes.sort(key=lambda k: k.offset_frames)

                clip = ClipIR(
                    clip_id=clip_id,
                    name=clip_name,
                    source_id=source_id,
                    timeline_in_frames=parent_timeline_in,
                    timeline_out_frames=parent_timeline_out,
                    source_in_frames=child_source_in,
                    source_channel=0,
                    speed_ratio=speed_ratio,
                    gain_db=Fraction(0, 1),
                    volume_keyframes=volume_keyframes,
                    pan_keyframes=pan_keyframes,
                    unsupported_effects=unsupported_effects,
                    markers=clip_markers,
                )
                clips.append(clip)

            clips.sort(key=lambda c: (c.timeline_in_frames, c.timeline_out_frames))
            track = TrackIR(
                track_index=track_index,
                name=track_name,
                kind=kind,
                channel_index=0,
                clips=clips,
            )
            tracks.append(track)

    max_out = max((c.timeline_out_frames for t in tracks for c in t.clips), default=0)
    dur_text = seq_elem.findtext("Duration")
    dur_frames = ticks_to_frames(int(dur_text), edit_rate) if dur_text else 0
    duration_frames = max(max_out, dur_frames)

    seq_markers.sort(key=lambda m: (m.frame_offset, m.name))

    seq_ir = SequenceIR(
        seq_id=seq_id,
        name=name,
        edit_rate=edit_rate,
        drop_frame=drop_frame,
        sample_rate=sample_rate,
        start_tc_frames=0,
        duration_frames=duration_frames,
        tracks=tracks,
        markers=seq_markers,
    )
    seq_ir.validate_no_overlaps()
    return seq_ir


def parse_prproj(path: str | Path, flatten_nested: bool = True) -> ProjectIR:
    file_path = Path(path)
    index = PrProjIndex(file_path)

    project_elem = None
    for e in index.root.iter():
        if e.tag == "Project" or e.tag.endswith("Project"):
            project_elem = e
            break

    project_name = (
        project_elem.findtext("Name") if project_elem is not None else None
    ) or file_path.stem

    seq_elems = index.list_sequences()
    default_edit_rate = _extract_edit_rate(seq_elems[0]) if seq_elems else Fraction(25, 1)

    media_sources: dict[str, MediaSourceIR] = {}
    for elem in index.list_media():
        source_id = _get_obj_id(elem)
        file_path_text = (
            elem.findtext("FilePath")
            or elem.findtext("AbsoluteFilePath")
            or elem.findtext("ActualMediaFilePath")
            or elem.findtext("RelativePath")
        )
        name = (
            elem.findtext("Name")
            or elem.findtext("OriginalPath")
            or (Path(file_path_text).name if file_path_text else None)
            or "Media"
        )
        dur_text = elem.findtext("Duration")
        if dur_text:
            dur_frames = ticks_to_frames(int(dur_text), default_edit_rate)
            duration_frames = dur_frames if dur_frames > 0 else 108000
        else:
            duration_frames = 108000

        ac_text = elem.findtext("AudioChannels")
        audio_channels = int(ac_text) if ac_text else 2
        sr_text = elem.findtext("SampleRate")
        sample_rate = int(sr_text) if sr_text else 48000

        media_sources[source_id] = MediaSourceIR(
            source_id=source_id,
            name=name,
            file_path=file_path_text,
            reel_name="AX",
            start_tc_frames=0,
            duration_frames=duration_frames,
            edit_rate=default_edit_rate,
            sample_rate=sample_rate,
            audio_channels=audio_channels,
            has_video=True,
            has_audio=True,
        )

    sequences: list[SequenceIR] = []
    for seq_elem in seq_elems:
        seq_ir = _extract_sequence(
            seq_elem=seq_elem,
            index=index,
            flatten_nested=flatten_nested,
            call_stack=set(),
        )
        sequences.append(seq_ir)

    return ProjectIR(
        project_name=project_name,
        source_format="prproj",
        media_sources=media_sources,
        sequences=sequences,
    )
