from __future__ import annotations

import math
from fractions import Fraction
from pathlib import Path
import xml.etree.ElementTree as ET

from machete.ir.schema import (
    ClipIR,
    KeyframeIR,
    MediaSourceIR,
    ProjectIR,
    SequenceIR,
    TrackIR,
)
from machete.ir.timecode import samples_to_frames


def _extract_volume_keyframes(
    clip_elem: ET.Element,
    sample_rate: int,
    edit_rate: Fraction,
    clip_duration_frames: int,
) -> list[KeyframeIR]:
    containers: list[ET.Element] = []

    for env in clip_elem.findall(".//envelope"):
        param = (env.get("parameter") or env.get("type") or "").lower()
        if "volume" in param or "fade" in param or not param:
            containers.append(env)

    for va in clip_elem.findall(".//volumeAutomation"):
        containers.append(va)

    for comp in clip_elem.findall(".//component"):
        cid = (comp.get("id") or comp.get("name") or "").lower()
        if "volume" in cid:
            containers.append(comp)

    for vol in clip_elem.findall(".//volume"):
        containers.append(vol)

    for kfs in clip_elem.findall(".//keyframes"):
        containers.append(kfs)

    seen_offsets: set[int] = set()
    keyframes: list[KeyframeIR] = []

    for container in containers:
        for kf_elem in container.findall(".//keyframe"):
            sample_str = (
                kf_elem.get("sample")
                or kf_elem.get("position")
                or kf_elem.get("offset")
                or (kf_elem.findtext("sample") if kf_elem.find("sample") is not None else None)
                or (kf_elem.findtext("position") if kf_elem.find("position") is not None else None)
                or (kf_elem.findtext("offset") if kf_elem.find("offset") is not None else None)
            )
            if sample_str is not None:
                offset_samples = int(sample_str)
                offset_frames = samples_to_frames(offset_samples, sample_rate, edit_rate)
            else:
                time_str = kf_elem.get("time") or (
                    kf_elem.findtext("time") if kf_elem.find("time") is not None else None
                )
                if time_str is not None:
                    offset_frames = math.floor(Fraction(time_str) * edit_rate + Fraction(1, 2))
                else:
                    continue

            if offset_frames in seen_offsets:
                continue
            seen_offsets.add(offset_frames)

            val_str = (
                kf_elem.get("value")
                or (kf_elem.findtext("value") if kf_elem.find("value") is not None else None)
                or "1.0"
            )
            val_frac = Fraction(val_str)
            keyframes.append(KeyframeIR(offset_frames=offset_frames, value=val_frac))

    fade_in = clip_elem.find(".//fadeIn")
    if fade_in is not None and not keyframes:
        dur_str = fade_in.get("duration") or fade_in.text
        if dur_str:
            fade_samples = int(dur_str)
            fade_frames = samples_to_frames(fade_samples, sample_rate, edit_rate)
            if 0 not in seen_offsets:
                seen_offsets.add(0)
                keyframes.append(KeyframeIR(offset_frames=0, value=Fraction(0, 1)))
            if fade_frames not in seen_offsets:
                seen_offsets.add(fade_frames)
                keyframes.append(KeyframeIR(offset_frames=fade_frames, value=Fraction(1, 1)))

    fade_out = clip_elem.find(".//fadeOut")
    if fade_out is not None:
        dur_str = fade_out.get("duration") or fade_out.text
        if dur_str:
            fade_samples = int(dur_str)
            fade_frames = samples_to_frames(fade_samples, sample_rate, edit_rate)
            start_fade_frame = max(0, clip_duration_frames - fade_frames)
            if start_fade_frame not in seen_offsets:
                seen_offsets.add(start_fade_frame)
                keyframes.append(KeyframeIR(offset_frames=start_fade_frame, value=Fraction(1, 1)))
            if clip_duration_frames not in seen_offsets:
                seen_offsets.add(clip_duration_frames)
                keyframes.append(KeyframeIR(offset_frames=clip_duration_frames, value=Fraction(0, 1)))

    keyframes.sort(key=lambda k: k.offset_frames)
    return keyframes


def parse_sesx(path: str | Path, target_edit_rate: Fraction = Fraction(25, 1)) -> ProjectIR:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"SESX file not found: {path}")

    tree = ET.parse(path)
    root = tree.getroot()

    if root.tag == "session":
        session_elem = root
    else:
        found_session = root.find(".//session")
        session_elem = found_session if found_session is not None else root

    sample_rate_str = (
        session_elem.get("sampleRate")
        or (session_elem.findtext("sampleRate") if session_elem.find("sampleRate") is not None else None)
    )
    session_sample_rate = int(sample_rate_str) if sample_rate_str else 48000

    session_duration_str = (
        session_elem.get("duration")
        or (session_elem.findtext("duration") if session_elem.find("duration") is not None else None)
    )
    session_duration_frames = 0
    if session_duration_str:
        session_duration_frames = samples_to_frames(
            int(session_duration_str), session_sample_rate, target_edit_rate
        )

    session_name = (
        session_elem.get("title")
        or session_elem.get("name")
        or (session_elem.findtext("title") if session_elem.find("title") is not None else None)
        or (session_elem.findtext("name") if session_elem.find("name") is not None else None)
        or path.stem
    )

    media_sources: dict[str, MediaSourceIR] = {}
    for file_elem in session_elem.findall(".//file"):
        source_id = file_elem.get("id") or (
            file_elem.findtext("id") if file_elem.find("id") is not None else ""
        )
        if not source_id:
            continue

        sr_str = (
            file_elem.get("sampleRate")
            or (file_elem.findtext("sampleRate") if file_elem.find("sampleRate") is not None else None)
        )
        file_sample_rate = int(sr_str) if sr_str else session_sample_rate

        channels_str = (
            file_elem.get("channels")
            or (file_elem.findtext("channels") if file_elem.find("channels") is not None else None)
        )
        audio_channels = int(channels_str) if channels_str else 2

        dur_str = (
            file_elem.get("duration")
            or (file_elem.findtext("duration") if file_elem.find("duration") is not None else None)
        )
        if dur_str:
            duration_frames = samples_to_frames(int(dur_str), file_sample_rate, target_edit_rate)
        else:
            duration_frames = 108000

        file_path = (
            file_elem.get("absolutePath")
            or (file_elem.findtext("absolutePath") if file_elem.find("absolutePath") is not None else None)
            or file_elem.get("mediaPath")
            or (file_elem.findtext("mediaPath") if file_elem.find("mediaPath") is not None else None)
            or file_elem.get("relativePath")
            or (file_elem.findtext("relativePath") if file_elem.find("relativePath") is not None else None)
        )

        name = (
            file_elem.get("name")
            or (file_elem.findtext("name") if file_elem.find("name") is not None else None)
            or (Path(file_path).name if file_path else f"source_{source_id}")
        )

        media_sources[source_id] = MediaSourceIR(
            source_id=source_id,
            name=name,
            file_path=file_path,
            sample_rate=file_sample_rate,
            audio_channels=audio_channels,
            has_video=False,
            has_audio=True,
            duration_frames=duration_frames,
            edit_rate=target_edit_rate,
        )

    tracks: list[TrackIR] = []
    audio_track_elems = session_elem.findall(".//audioTrack")
    if not audio_track_elems:
        audio_track_elems = [
            t
            for t in session_elem.findall(".//track")
            if t.get("type", "audio").lower() in ("audio", "sound")
        ]

    for track_idx, track_elem in enumerate(audio_track_elems):
        track_name = (
            track_elem.get("name")
            or (track_elem.findtext("name") if track_elem.find("name") is not None else None)
            or f"A{track_idx + 1}"
        )
        t_idx_str = (
            track_elem.get("trackIndex")
            or (track_elem.findtext("trackIndex") if track_elem.find("trackIndex") is not None else None)
        )
        if t_idx_str is not None:
            try:
                track_index = int(t_idx_str)
            except ValueError:
                track_index = track_idx
        else:
            track_index = track_idx

        track_clips: list[ClipIR] = []
        clip_elems = track_elem.findall(".//audioClip")
        if not clip_elems:
            clip_elems = track_elem.findall(".//clip")

        for clip_idx, clip_elem in enumerate(clip_elems):
            clip_name = (
                clip_elem.get("name")
                or (clip_elem.findtext("name") if clip_elem.find("name") is not None else None)
                or f"Clip_{clip_idx + 1}"
            )
            clip_id = (
                clip_elem.get("id")
                or (clip_elem.findtext("id") if clip_elem.find("id") is not None else None)
                or f"clip_{track_index}_{clip_idx + 1}"
            )
            source_id = clip_elem.get("fileID") or ""
            if not source_id:
                src_tag = clip_elem.find("source")
                if src_tag is not None:
                    source_id = src_tag.get("fileID") or (
                        src_tag.findtext("fileID") if src_tag.find("fileID") is not None else ""
                    )
            if not source_id:
                source_id = clip_elem.findtext("fileID") or ""

            if not source_id:
                source_id = f"gen_source_{track_index}_{clip_idx + 1}"

            if source_id not in media_sources:
                media_sources[source_id] = MediaSourceIR(
                    source_id=source_id,
                    name=clip_name,
                    file_path=clip_elem.get("relativePath") or clip_elem.get("mediaPath"),
                    sample_rate=session_sample_rate,
                    audio_channels=2,
                    has_video=False,
                    has_audio=True,
                    duration_frames=108000,
                    edit_rate=target_edit_rate,
                )

            clip_sample_rate = media_sources[source_id].sample_rate

            start_str = (
                clip_elem.get("startPoint")
                or (clip_elem.findtext("startPoint") if clip_elem.find("startPoint") is not None else None)
                or "0"
            )
            end_str = (
                clip_elem.get("endPoint")
                or (clip_elem.findtext("endPoint") if clip_elem.find("endPoint") is not None else None)
                or "0"
            )
            source_in_str = (
                clip_elem.get("sourceInPoint")
                or (
                    clip_elem.findtext("sourceInPoint")
                    if clip_elem.find("sourceInPoint") is not None
                    else None
                )
                or "0"
            )

            start_point = int(start_str)
            end_point = int(end_str)
            source_in_point = int(source_in_str)

            timeline_in_frames = samples_to_frames(start_point, clip_sample_rate, target_edit_rate)
            timeline_out_frames = samples_to_frames(end_point, clip_sample_rate, target_edit_rate)
            source_in_frames = samples_to_frames(source_in_point, clip_sample_rate, target_edit_rate)

            volume_keyframes = _extract_volume_keyframes(
                clip_elem=clip_elem,
                sample_rate=clip_sample_rate,
                edit_rate=target_edit_rate,
                clip_duration_frames=timeline_out_frames - timeline_in_frames,
            )

            clip_ir = ClipIR(
                clip_id=clip_id,
                name=clip_name,
                source_id=source_id,
                timeline_in_frames=timeline_in_frames,
                timeline_out_frames=timeline_out_frames,
                source_in_frames=source_in_frames,
                source_channel=0,
                speed_ratio=Fraction(1, 1),
                gain_db=Fraction(0, 1),
                volume_keyframes=volume_keyframes,
            )
            track_clips.append(clip_ir)

        track_clips.sort(key=lambda c: (c.timeline_in_frames, c.timeline_out_frames))

        tracks.append(
            TrackIR(
                track_index=track_index,
                name=track_name,
                kind="sound",
                channel_index=0,
                clips=track_clips,
            )
        )

    tracks.sort(key=lambda t: t.track_index)

    max_clip_out = max((c.timeline_out_frames for t in tracks for c in t.clips), default=0)
    seq_duration_frames = max(session_duration_frames, max_clip_out)

    seq = SequenceIR(
        seq_id="seq_1",
        name=session_name,
        edit_rate=target_edit_rate,
        drop_frame=False,
        sample_rate=session_sample_rate,
        start_tc_frames=0,
        duration_frames=seq_duration_frames,
        tracks=tracks,
    )
    seq.validate_no_overlaps()

    return ProjectIR(
        project_name=session_name,
        source_format="sesx",
        media_sources=media_sources,
        sequences=[seq],
    )
