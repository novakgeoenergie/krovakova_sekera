from __future__ import annotations

from fractions import Fraction
from typing import Annotated, Literal
from pydantic import BaseModel, BeforeValidator, Field, PlainSerializer


def _validate_fraction(v: object) -> Fraction:
    if isinstance(v, bool):
        raise TypeError("Boolean cannot be converted to Fraction")
    if isinstance(v, float):
        raise ValueError("Floats are not permitted in Machete IR (NO-FLOAT TIME LAW). Use Fraction or int.")
    if isinstance(v, Fraction):
        return v
    if isinstance(v, int):
        return Fraction(v, 1)
    if isinstance(v, str):
        try:
            return Fraction(v)
        except (ValueError, ZeroDivisionError) as e:
            raise ValueError(f"Invalid fraction string: {v!r}") from e
    if isinstance(v, dict) and "numerator" in v and "denominator" in v:
        return Fraction(v["numerator"], v["denominator"])
    raise TypeError(f"Cannot convert {type(v).__name__} to Fraction")


def _serialize_fraction(v: Fraction) -> str:
    return f"{v.numerator}/{v.denominator}"


FractionField = Annotated[
    Fraction,
    BeforeValidator(_validate_fraction),
    PlainSerializer(_serialize_fraction, return_type=str),
]


class MediaSourceIR(BaseModel):
    source_id: str
    name: str
    file_path: str | None = None
    reel_name: str = "AX"
    start_tc_frames: int = 0
    duration_frames: int
    edit_rate: FractionField
    sample_rate: int = 48000
    audio_channels: int = 2
    has_video: bool = True
    has_audio: bool = True


class KeyframeIR(BaseModel):
    offset_frames: int
    value: FractionField


class TransitionIR(BaseModel):
    duration_frames: int
    alignment: Literal["center", "start", "end"] = "center"
    kind: Literal["cross_dissolve", "audio_crossfade"] = "cross_dissolve"


class EffectNoticeIR(BaseModel):
    effect_name: str
    parameters_summary: str = ""
    requires_manual_recreate: bool = True


class MarkerIR(BaseModel):
    frame_offset: int
    duration_frames: int = 1
    name: str
    comment: str = ""
    color: Literal["red", "yellow", "green", "blue", "cyan", "magenta", "white", "black"] = "red"


class ClipIR(BaseModel):
    clip_id: str
    name: str
    source_id: str
    timeline_in_frames: int
    timeline_out_frames: int
    source_in_frames: int
    source_channel: int = 0
    speed_ratio: FractionField = Fraction(1, 1)
    gain_db: FractionField = Fraction(0, 1)
    volume_keyframes: list[KeyframeIR] = Field(default_factory=list)
    pan_keyframes: list[KeyframeIR] = Field(default_factory=list)
    transition_in: TransitionIR | None = None
    transition_out: TransitionIR | None = None
    unsupported_effects: list[EffectNoticeIR] = Field(default_factory=list)
    markers: list[MarkerIR] = Field(default_factory=list)

    @property
    def duration_frames(self) -> int:
        return self.timeline_out_frames - self.timeline_in_frames


class TrackIR(BaseModel):
    track_index: int
    name: str
    kind: Literal["picture", "sound"]
    channel_index: int = 0
    clips: list[ClipIR] = Field(default_factory=list)


class SequenceIR(BaseModel):
    seq_id: str
    name: str
    edit_rate: FractionField = Fraction(25, 1)
    drop_frame: bool = False
    sample_rate: int = 48000
    start_tc_frames: int = 0
    duration_frames: int
    tracks: list[TrackIR] = Field(default_factory=list)
    markers: list[MarkerIR] = Field(default_factory=list)

    def validate_no_overlaps(self) -> None:
        """
        Validate that clips on each track have valid intervals and do not overlap.
        Raises ValueError if:
        - Any clip has timeline_out_frames <= timeline_in_frames
        - Any clip has timeline_in_frames < 0
        - On any track, clips sorted by timeline_in_frames have overlaps where
          clip[i].timeline_out_frames > clip[i+1].timeline_in_frames.
        """
        for track in self.tracks:
            for clip in track.clips:
                if clip.timeline_in_frames < 0:
                    raise ValueError(
                        f"Clip {clip.clip_id!r} on track {track.track_index} has negative "
                        f"timeline_in_frames={clip.timeline_in_frames}"
                    )
                if clip.timeline_out_frames <= clip.timeline_in_frames:
                    raise ValueError(
                        f"Clip {clip.clip_id!r} on track {track.track_index} has invalid interval: "
                        f"timeline_out_frames={clip.timeline_out_frames} <= "
                        f"timeline_in_frames={clip.timeline_in_frames}"
                    )

            sorted_clips = sorted(track.clips, key=lambda c: (c.timeline_in_frames, c.timeline_out_frames))
            for i in range(len(sorted_clips) - 1):
                if sorted_clips[i].timeline_out_frames > sorted_clips[i + 1].timeline_in_frames:
                    raise ValueError(
                        f"Clips overlap on track {track.track_index}: clip {sorted_clips[i].clip_id!r} "
                        f"(out={sorted_clips[i].timeline_out_frames}) overlaps with clip "
                        f"{sorted_clips[i + 1].clip_id!r} (in={sorted_clips[i + 1].timeline_in_frames})"
                    )


class ProjectIR(BaseModel):
    project_name: str
    source_format: Literal["prproj", "sesx"]
    media_sources: dict[str, MediaSourceIR] = Field(default_factory=dict)
    sequences: list[SequenceIR] = Field(default_factory=list)


__all__ = [
    "FractionField",
    "MediaSourceIR",
    "KeyframeIR",
    "TransitionIR",
    "EffectNoticeIR",
    "MarkerIR",
    "ClipIR",
    "TrackIR",
    "SequenceIR",
    "ProjectIR",
]
