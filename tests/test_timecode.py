from fractions import Fraction
import pytest
from pydantic import ValidationError

from machete.ir import (
    ClipIR,
    EDIT_RATES,
    EffectNoticeIR,
    KeyframeIR,
    MarkerIR,
    MediaSourceIR,
    ProjectIR,
    SequenceIR,
    TrackIR,
    TransitionIR,
    deterministic_mob_uid,
    frames_to_samples,
    frames_to_smpte_tc,
    frames_to_ticks,
    samples_to_frames,
    ticks_to_frames,
)


def test_ticks_frames_roundtrip_3hours():
    """Test ticks_to_frames and frames_to_ticks round-trip across 10800s (3 hours) at 24, 25, 23.976."""
    test_rates = [
        Fraction(24, 1),
        Fraction(25, 1),
        Fraction(24000, 1001),
    ]

    for rate in test_rates:
        # Test every second across full 3 hours (10800 seconds)
        for sec in range(0, 10801):
            frame = int(rate * sec)
            ticks = frames_to_ticks(frame, rate)
            recovered_frame = ticks_to_frames(ticks, rate)
            assert recovered_frame == frame, f"Frame drift at rate={rate}, sec={sec}: expected {frame}, got {recovered_frame}"


def test_smpte_drop_frame_timecode_29_97():
    """Test SMPTE drop-frame timecode at 30000/1001 with drop_frame=True."""
    rate = Fraction(30000, 1001)

    assert frames_to_smpte_tc(1799, rate, drop_frame=True) == "00:00:59;29"
    assert frames_to_smpte_tc(1800, rate, drop_frame=True) == "00:01:00;02"
    assert frames_to_smpte_tc(17982, rate, drop_frame=True) == "00:10:00;00"


def test_smpte_drop_frame_timecode_59_94():
    """Test SMPTE drop-frame timecode at 60000/1001 (nominal 60fps drops 4 frames)."""
    rate = Fraction(60000, 1001)

    assert frames_to_smpte_tc(3599, rate, drop_frame=True) == "00:00:59;59"
    assert frames_to_smpte_tc(3600, rate, drop_frame=True) == "00:01:00;04"
    assert frames_to_smpte_tc(35964, rate, drop_frame=True) == "00:10:00;00"


def test_smpte_non_drop_frame_timecode():
    """Test SMPTE non-drop-frame timecode at 24 and 25 fps."""
    rate24 = Fraction(24, 1)
    assert frames_to_smpte_tc(0, rate24, drop_frame=False) == "00:00:00:00"
    assert frames_to_smpte_tc(24, rate24, drop_frame=False) == "00:00:01:00"
    assert frames_to_smpte_tc(86400, rate24, drop_frame=False) == "01:00:00:00"

    rate25 = Fraction(25, 1)
    assert frames_to_smpte_tc(0, rate25, drop_frame=False) == "00:00:00:00"
    assert frames_to_smpte_tc(25, rate25, drop_frame=False) == "00:00:01:00"
    assert frames_to_smpte_tc(90000, rate25, drop_frame=False) == "01:00:00:00"


def test_samples_frames_conversion():
    """Test exact rational sample <-> frame conversion."""
    sample_rate = 48000
    rate25 = Fraction(25, 1)

    # 1 second = 48000 samples = 25 frames
    assert samples_to_frames(48000, sample_rate, rate25) == 25
    assert frames_to_samples(25, sample_rate, rate25) == 48000

    # Test round-trip across 1000 frames
    for f in range(0, 1000):
        samples = frames_to_samples(f, sample_rate, rate25)
        rec_frame = samples_to_frames(samples, sample_rate, rate25)
        assert rec_frame == f


def test_deterministic_mob_uid():
    """Test deterministic UUIDv5 generation for AAF relinking."""
    uid1 = deterministic_mob_uid("reel1_clip1")
    uid2 = deterministic_mob_uid("reel1_clip1")
    uid3 = deterministic_mob_uid("reel1_clip2")

    assert uid1 == uid2
    assert uid1 != uid3


def test_project_ir_json_roundtrip():
    """Test ProjectIR serialization round-trip: model_dump_json() -> model_validate_json() preserving exact Fraction values."""
    media = MediaSourceIR(
        source_id="src_001",
        name="interview_a.mov",
        file_path="/media/interview_a.mov",
        reel_name="REEL_01",
        start_tc_frames=86400,
        duration_frames=72000,
        edit_rate=Fraction(24000, 1001),
        sample_rate=48000,
        audio_channels=2,
    )

    clip = ClipIR(
        clip_id="clip_001",
        name="Soundbyte 1",
        source_id="src_001",
        timeline_in_frames=100,
        timeline_out_frames=350,
        source_in_frames=1000,
        source_channel=0,
        speed_ratio=Fraction(1, 1),
        gain_db=Fraction(-3, 1),
        volume_keyframes=[
            KeyframeIR(offset_frames=0, value=Fraction(1, 1)),
            KeyframeIR(offset_frames=50, value=Fraction(1, 2)),
        ],
        pan_keyframes=[
            KeyframeIR(offset_frames=0, value=Fraction(-1, 2)),
        ],
        transition_in=TransitionIR(duration_frames=24, alignment="start", kind="cross_dissolve"),
        transition_out=TransitionIR(duration_frames=12, alignment="end", kind="audio_crossfade"),
        unsupported_effects=[
            EffectNoticeIR(effect_name="LumetriColor", parameters_summary="LUT applied", requires_manual_recreate=True)
        ],
        markers=[
            MarkerIR(frame_offset=150, duration_frames=1, name="Check Cut", comment="Fix sync", color="red")
        ],
    )

    assert clip.duration_frames == 250

    track_v = TrackIR(track_index=0, name="V1", kind="picture", clips=[clip])
    track_a = TrackIR(track_index=1, name="A1", kind="sound", clips=[])

    seq = SequenceIR(
        seq_id="seq_main",
        name="Feature Sequence",
        edit_rate=Fraction(24000, 1001),
        drop_frame=False,
        sample_rate=48000,
        start_tc_frames=86400,
        duration_frames=10000,
        tracks=[track_v, track_a],
        markers=[MarkerIR(frame_offset=0, name="Start", color="green")],
    )

    project = ProjectIR(
        project_name="Feature Film",
        source_format="prproj",
        media_sources={"src_001": media},
        sequences=[seq],
    )

    json_payload = project.model_dump_json()
    recovered = ProjectIR.model_validate_json(json_payload)

    # Verify root project attributes
    assert recovered.project_name == "Feature Film"
    assert recovered.source_format == "prproj"

    # Verify exact Fraction types and values
    rec_media = recovered.media_sources["src_001"]
    assert rec_media.edit_rate == Fraction(24000, 1001)
    assert isinstance(rec_media.edit_rate, Fraction)

    rec_seq = recovered.sequences[0]
    assert rec_seq.edit_rate == Fraction(24000, 1001)
    assert isinstance(rec_seq.edit_rate, Fraction)

    rec_clip = rec_seq.tracks[0].clips[0]
    assert rec_clip.speed_ratio == Fraction(1, 1)
    assert isinstance(rec_clip.speed_ratio, Fraction)
    assert rec_clip.gain_db == Fraction(-3, 1)
    assert isinstance(rec_clip.gain_db, Fraction)

    assert rec_clip.volume_keyframes[1].value == Fraction(1, 2)
    assert isinstance(rec_clip.volume_keyframes[1].value, Fraction)

    assert rec_clip.pan_keyframes[0].value == Fraction(-1, 2)
    assert isinstance(rec_clip.pan_keyframes[0].value, Fraction)

    assert rec_clip.duration_frames == 250


def test_sequence_validate_no_overlaps_success():
    """Test validate_no_overlaps succeeds when clips are contiguous or have gaps."""
    clip1 = ClipIR(
        clip_id="c1",
        name="Clip 1",
        source_id="s1",
        timeline_in_frames=0,
        timeline_out_frames=100,
        source_in_frames=0,
    )
    clip2 = ClipIR(
        clip_id="c2",
        name="Clip 2",
        source_id="s1",
        timeline_in_frames=100,  # Abutting clip1
        timeline_out_frames=200,
        source_in_frames=0,
    )
    clip3 = ClipIR(
        clip_id="c3",
        name="Clip 3",
        source_id="s1",
        timeline_in_frames=250,  # Gap after clip2
        timeline_out_frames=300,
        source_in_frames=0,
    )

    track = TrackIR(track_index=0, name="V1", kind="picture", clips=[clip1, clip2, clip3])
    seq = SequenceIR(seq_id="s1", name="Seq", duration_frames=500, tracks=[track])

    # Should not raise
    seq.validate_no_overlaps()


def test_sequence_validate_no_overlaps_raises_on_overlap():
    """Test SequenceIR.validate_no_overlaps() raises ValueError on overlapping clips."""
    clip1 = ClipIR(
        clip_id="c1",
        name="Clip 1",
        source_id="s1",
        timeline_in_frames=50,
        timeline_out_frames=150,
        source_in_frames=0,
    )
    clip2 = ClipIR(
        clip_id="c2",
        name="Clip 2",
        source_id="s1",
        timeline_in_frames=120,  # Overlaps clip1 (120 < 150)
        timeline_out_frames=200,
        source_in_frames=0,
    )

    track = TrackIR(track_index=0, name="V1", kind="picture", clips=[clip1, clip2])
    seq = SequenceIR(seq_id="s1", name="Seq", duration_frames=500, tracks=[track])

    with pytest.raises(ValueError, match="overlap"):
        seq.validate_no_overlaps()


def test_sequence_validate_no_overlaps_raises_on_invalid_intervals():
    """Test validate_no_overlaps raises ValueError on invalid clip intervals."""
    # Negative timeline_in_frames
    clip_neg = ClipIR(
        clip_id="c_neg",
        name="Neg",
        source_id="s1",
        timeline_in_frames=-10,
        timeline_out_frames=50,
        source_in_frames=0,
    )
    seq_neg = SequenceIR(
        seq_id="s_neg",
        name="Seq Neg",
        duration_frames=100,
        tracks=[TrackIR(track_index=0, name="V1", kind="picture", clips=[clip_neg])],
    )
    with pytest.raises(ValueError, match="negative"):
        seq_neg.validate_no_overlaps()

    # timeline_out <= timeline_in
    clip_zero = ClipIR(
        clip_id="c_zero",
        name="ZeroLen",
        source_id="s1",
        timeline_in_frames=50,
        timeline_out_frames=50,
        source_in_frames=0,
    )
    seq_zero = SequenceIR(
        seq_id="s_zero",
        name="Seq Zero",
        duration_frames=100,
        tracks=[TrackIR(track_index=0, name="V1", kind="picture", clips=[clip_zero])],
    )
    with pytest.raises(ValueError, match="invalid interval"):
        seq_zero.validate_no_overlaps()


def test_no_float_time_law_enforcement():
    """Enforce NO-FLOAT TIME LAW: Passing floats to schema models must raise ValidationError."""
    with pytest.raises(ValidationError):
        MediaSourceIR(
            source_id="s1",
            name="clip.mov",
            duration_frames=100,
            edit_rate=23.976,  # Float must be rejected
        )

    with pytest.raises(ValidationError):
        ClipIR(
            clip_id="c1",
            name="clip",
            source_id="s1",
            timeline_in_frames=0,
            timeline_out_frames=100,
            source_in_frames=0,
            speed_ratio=1.5,  # Float must be rejected
        )
