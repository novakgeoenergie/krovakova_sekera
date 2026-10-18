from __future__ import annotations

from fractions import Fraction
import json
from pathlib import Path
from typing import Any
import wave

import aaf2
from aaf2.misc import TaggedValueHelper
from aaf2.mobs import MasterMob, SourceMob

from machete.ir import (
    ClipIR,
    MediaSourceIR,
    SequenceIR,
    TrackIR,
)
from machete.exporters.aaf_core import deterministic_mob_id

# Ensure pyaaf2 Component objects support dictionary-like UserComments via .comments
if not hasattr(aaf2.components.Component, "comments"):
    aaf2.components.Component.comments = property(
        lambda self: TaggedValueHelper(self["UserComments"])
    )


def attach_audio_source_and_essence(
    f: aaf2.file.AAFFile,
    src_ir: MediaSourceIR,
    edit_rate: Fraction,
    embed_audio: bool = False,
) -> tuple[SourceMob, MasterMob]:
    """Attach audio SourceMob, PCMDescriptor, and optional EssenceData or Locator,
    and link to a MasterMob.

    Follows the No-Float Time Law (only Fractions and exact ints) and deterministic MobIDs.
    """
    if not isinstance(edit_rate, Fraction):
        edit_rate = Fraction(edit_rate)

    # 1. SourceMob (File / Essence SourceMob)
    source_mob_id = deterministic_mob_id(f"source:audio:{src_ir.source_id}")
    if source_mob_id in f.content.mobs:
        source_mob = f.content.mobs[source_mob_id]
    else:
        source_mob = f.create.SourceMob(src_ir.reel_name or src_ir.name)
        source_mob.mob_id = source_mob_id
        f.content.mobs.append(source_mob)

    file_path = Path(src_ir.file_path).resolve() if src_ir.file_path else None
    file_exists = file_path is not None and file_path.exists()

    sample_rate: int = int(src_ir.sample_rate) if src_ir.sample_rate else 48000
    channels: int = int(src_ir.audio_channels) if src_ir.audio_channels else 2
    sampwidth: int = 2
    nframes: int = (src_ir.duration_frames * sample_rate * edit_rate.denominator) // edit_rate.numerator
    raw_pcm_bytes: bytes | None = None

    if file_exists and file_path.suffix.lower() == ".wav":
        try:
            with wave.open(str(file_path), "rb") as wav:
                sample_rate = wav.getframerate()
                channels = wav.getnchannels()
                sampwidth = wav.getsampwidth()
                nframes = wav.getnframes()
                if embed_audio:
                    raw_pcm_bytes = wav.readframes(nframes)
        except Exception:
            pass

    # Create and attach PCMDescriptor
    desc = f.create.PCMDescriptor()
    desc["SampleRate"].value = Fraction(sample_rate, 1)
    desc["AudioSamplingRate"].value = Fraction(sample_rate, 1)
    desc["Channels"].value = channels
    desc["QuantizationBits"].value = sampwidth * 8
    desc["BlockAlign"].value = channels * sampwidth
    desc["AverageBPS"].value = sample_rate * channels * sampwidth
    desc["Length"].value = nframes

    if embed_audio and raw_pcm_bytes is not None:
        essence = f.create.EssenceData()
        essence.mob_id = source_mob.mob_id
        f.content.essencedata.append(essence)
        stream = essence.open("w")
        stream.write(raw_pcm_bytes)
    else:
        if file_path is not None:
            loc = f.create.NetworkLocator()
            loc["URLString"].value = file_path.as_uri()
            desc["Locator"].append(loc)

    source_mob.descriptor = desc

    # Slot on SourceMob
    source_slot = None
    for s in source_mob.slots:
        if s.media_kind == "sound":
            source_slot = s
            break
    if source_slot is None:
        source_slot = source_mob.create_empty_slot(edit_rate, media_kind="sound", slot_id=1)

    duration_in_edit_rate = (nframes * edit_rate.numerator) // (sample_rate * edit_rate.denominator)
    source_slot.segment.length = max(src_ir.duration_frames, duration_in_edit_rate, 108000)

    # 2. MasterMob
    master_mob_id = deterministic_mob_id(f"master:{src_ir.source_id}")
    if master_mob_id in f.content.mobs:
        master_mob = f.content.mobs[master_mob_id]
    else:
        master_mob = f.create.MasterMob(src_ir.name)
        master_mob.mob_id = master_mob_id
        f.content.mobs.append(master_mob)

    master_slot = None
    for s in master_mob.slots:
        if s.media_kind == "sound":
            master_slot = s
            break
    if master_slot is None:
        master_slot = master_mob.create_sound_slot(edit_rate)

    master_slot.segment = source_mob.create_source_clip(
        slot_id=source_slot.slot_id,
        start=0,
        length=source_slot.segment.length,
        media_kind="sound",
    )

    return source_mob, master_mob


def apply_audio_automation(
    f: aaf2.file.AAFFile,
    component: Any,
    clip_ir: ClipIR,
) -> None:
    """Store gain and volume keyframes as structured metadata comments on component or its mob."""
    if hasattr(component, "comments"):
        comments = component.comments
    elif "UserComments" in getattr(component, "classdef", {}):
        comments = TaggedValueHelper(component["UserComments"])
    elif hasattr(component, "mob") and component.mob and hasattr(component.mob, "comments"):
        comments = component.mob.comments
    else:
        comments = None

    if comments is not None:
        if clip_ir.gain_db is not None:
            comments["GAIN_DB"] = str(clip_ir.gain_db)
        if clip_ir.volume_keyframes:
            comments["VOLUME_KEYFRAMES"] = json.dumps(
                [{"offset": k.offset_frames, "value": str(k.value)} for k in clip_ir.volume_keyframes]
            )
        if clip_ir.pan_keyframes:
            comments["PAN_KEYFRAMES"] = json.dumps(
                [{"offset": k.offset_frames, "value": str(k.value)} for k in clip_ir.pan_keyframes]
            )


def split_stereo_tracks_to_mono(seq_ir: SequenceIR) -> SequenceIR:
    """Split stereo sound tracks (channel_index == 0) into .L and .R mono tracks.

    Keep non-stereo sound tracks and picture tracks untouched.
    """
    new_tracks: list[TrackIR] = []
    for track in seq_ir.tracks:
        if track.kind == "sound" and track.channel_index == 0:
            left_clips = [
                c.model_copy(deep=True, update={"source_channel": 1})
                for c in track.clips
            ]
            right_clips = [
                c.model_copy(deep=True, update={"source_channel": 2})
                for c in track.clips
            ]
            track_l = TrackIR(
                track_index=len(new_tracks),
                name=f"{track.name}.L",
                kind="sound",
                channel_index=1,
                clips=left_clips,
            )
            new_tracks.append(track_l)
            track_r = TrackIR(
                track_index=len(new_tracks),
                name=f"{track.name}.R",
                kind="sound",
                channel_index=2,
                clips=right_clips,
            )
            new_tracks.append(track_r)
        else:
            copied_track = track.model_copy(deep=True, update={"track_index": len(new_tracks)})
            new_tracks.append(copied_track)

    return seq_ir.model_copy(deep=True, update={"tracks": new_tracks})


__all__ = [
    "attach_audio_source_and_essence",
    "apply_audio_automation",
    "split_stereo_tracks_to_mono",
]
