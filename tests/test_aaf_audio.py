from __future__ import annotations

from fractions import Fraction
import json
from pathlib import Path
import aaf2

from machete.exporters import (
    apply_audio_automation,
    attach_audio_source_and_essence,
    deterministic_mob_id,
    export_project_to_aaf,
    split_stereo_tracks_to_mono,
)
from machete.ir import (
    ClipIR,
    KeyframeIR,
    MediaSourceIR,
    ProjectIR,
    SequenceIR,
    TrackIR,
)
from tests.fixture_factory import generate_sample_tone_wav


def test_acceptance_embedded_audio_export(tmp_path: Path) -> None:
    """Acceptance test verifying:

    1. Generate sample_tone.wav via fixture_factory.
    2. Export a ProjectIR referencing sample_tone.wav with embed_audio=True and 2 volume keyframes.
    3. Re-open resulting .aaf and assert:
       - PCMDescriptor exists with QuantizationBits == 16 and SampleRate == 48000.
       - Raw PCM essence data exists in f.content.essencedata.
       - Volume automation comments are stored on clip component.
    """
    # 1. Generate sample_tone.wav
    wav_path = generate_sample_tone_wav(tmp_path / "sample_tone.wav")
    assert wav_path.exists()

    # 2. Build ProjectIR with 2 volume keyframes
    kf1 = KeyframeIR(offset_frames=0, value=Fraction(1, 1))
    kf2 = KeyframeIR(offset_frames=25, value=Fraction(1, 2))

    media = MediaSourceIR(
        source_id="src_tone_01",
        name="sample_tone.wav",
        file_path=str(wav_path),
        reel_name="TONE",
        start_tc_frames=0,
        duration_frames=150,
        edit_rate=Fraction(25, 1),
        sample_rate=48000,
        audio_channels=1,
        has_video=False,
        has_audio=True,
    )

    clip = ClipIR(
        clip_id="clip_tone_01",
        name="Tone Clip",
        source_id="src_tone_01",
        timeline_in_frames=0,
        timeline_out_frames=100,
        source_in_frames=0,
        gain_db=Fraction(-6, 1),
        volume_keyframes=[kf1, kf2],
    )

    track_a1 = TrackIR(
        track_index=0,
        name="A1",
        kind="sound",
        channel_index=1,
        clips=[clip],
    )

    seq = SequenceIR(
        seq_id="seq_tone_01",
        name="Tone Sequence",
        edit_rate=Fraction(25, 1),
        drop_frame=False,
        sample_rate=48000,
        start_tc_frames=0,
        duration_frames=150,
        tracks=[track_a1],
    )

    project = ProjectIR(
        project_name="Tone Acceptance Project",
        source_format="sesx",
        media_sources={"src_tone_01": media},
        sequences=[seq],
    )

    aaf_path = tmp_path / "embedded_tone.aaf"
    export_project_to_aaf(project, aaf_path, embed_audio=True)
    assert aaf_path.exists()

    # 3. Re-open resulting .aaf and verify
    with aaf2.open(str(aaf_path), "r") as f:
        # Assert PCMDescriptor exists with QuantizationBits == 16 and SampleRate == 48000
        pcm_descs = [
            m.descriptor
            for m in f.content.mobs
            if isinstance(m, aaf2.mobs.SourceMob)
            and isinstance(getattr(m, "descriptor", None), aaf2.essence.PCMDescriptor)
        ]
        assert len(pcm_descs) >= 1, "PCMDescriptor not found on any SourceMob"
        desc = pcm_descs[0]
        assert desc["QuantizationBits"].value == 16
        assert desc["SampleRate"].value == 48000

        # Assert raw PCM essence data exists in f.content.essencedata
        essence_list = list(f.content.essencedata)
        assert len(essence_list) >= 1, "EssenceData not found in f.content.essencedata"
        essence = essence_list[0]
        stream = essence.open("r")
        raw_pcm_bytes = stream.read()
        assert len(raw_pcm_bytes) > 0, "Essence stream is empty"

        # Assert volume automation comments are present on clip component
        comp_mob = list(f.content.toplevel())[0]
        a1_slot = [s for s in comp_mob.slots if s.name == "A1"][0]
        clip_comp = a1_slot.segment.components[0]
        assert clip_comp.comments["GAIN_DB"] == str(clip.gain_db)
        keyframes_data = json.loads(clip_comp.comments["VOLUME_KEYFRAMES"])
        assert len(keyframes_data) == 2
        assert keyframes_data[0] == {"offset": 0, "value": str(kf1.value)}
        assert keyframes_data[1] == {"offset": 25, "value": str(kf2.value)}


def test_split_stereo_tracks_to_mono() -> None:
    """Assert split_stereo_tracks_to_mono converts 1 stereo track into 2 mono tracks

    with identical clip timings while keeping picture and mono tracks untouched.
    """
    pic_clip = ClipIR(
        clip_id="c_pic",
        name="Shot 1",
        source_id="src_pic",
        timeline_in_frames=0,
        timeline_out_frames=50,
        source_in_frames=0,
    )
    track_v1 = TrackIR(
        track_index=0,
        name="V1",
        kind="picture",
        clips=[pic_clip],
    )

    clip1 = ClipIR(
        clip_id="c_stereo_1",
        name="Music Intro",
        source_id="src_music",
        timeline_in_frames=0,
        timeline_out_frames=50,
        source_in_frames=0,
        source_channel=0,
        volume_keyframes=[
            KeyframeIR(offset_frames=0, value=Fraction(1, 1)),
            KeyframeIR(offset_frames=25, value=Fraction(1, 2)),
        ],
    )
    clip2 = ClipIR(
        clip_id="c_stereo_2",
        name="Music Chorus",
        source_id="src_music",
        timeline_in_frames=75,
        timeline_out_frames=125,
        source_in_frames=60,
        source_channel=0,
    )
    track_stereo = TrackIR(
        track_index=1,
        name="A1",
        kind="sound",
        channel_index=0,  # stereo
        clips=[clip1, clip2],
    )

    mono_clip = ClipIR(
        clip_id="c_dialog",
        name="Dialog 1",
        source_id="src_dia",
        timeline_in_frames=10,
        timeline_out_frames=70,
        source_in_frames=0,
        source_channel=1,
    )
    track_mono = TrackIR(
        track_index=2,
        name="A2",
        kind="sound",
        channel_index=1,  # already mono
        clips=[mono_clip],
    )

    seq = SequenceIR(
        seq_id="seq_split_test",
        name="Split Test Sequence",
        edit_rate=Fraction(25, 1),
        duration_frames=150,
        tracks=[track_v1, track_stereo, track_mono],
    )

    split_seq = split_stereo_tracks_to_mono(seq)
    split_seq.validate_no_overlaps()

    assert len(split_seq.tracks) == 4

    # Picture track untouched
    t0 = split_seq.tracks[0]
    assert t0.name == "V1"
    assert t0.kind == "picture"
    assert len(t0.clips) == 1

    # Track 1: Left mono track
    t1 = split_seq.tracks[1]
    assert t1.name == "A1.L"
    assert t1.kind == "sound"
    assert t1.channel_index == 1
    assert len(t1.clips) == 2
    assert t1.clips[0].source_channel == 1
    assert t1.clips[1].source_channel == 1
    assert t1.clips[0].timeline_in_frames == clip1.timeline_in_frames
    assert t1.clips[0].timeline_out_frames == clip1.timeline_out_frames
    assert t1.clips[0].source_in_frames == clip1.source_in_frames
    assert t1.clips[1].timeline_in_frames == clip2.timeline_in_frames
    assert t1.clips[1].timeline_out_frames == clip2.timeline_out_frames
    assert t1.clips[1].source_in_frames == clip2.source_in_frames
    assert len(t1.clips[0].volume_keyframes) == 2

    # Track 2: Right mono track
    t2 = split_seq.tracks[2]
    assert t2.name == "A1.R"
    assert t2.kind == "sound"
    assert t2.channel_index == 2
    assert len(t2.clips) == 2
    assert t2.clips[0].source_channel == 2
    assert t2.clips[1].source_channel == 2
    assert t2.clips[0].timeline_in_frames == clip1.timeline_in_frames
    assert t2.clips[0].timeline_out_frames == clip1.timeline_out_frames
    assert t2.clips[0].source_in_frames == clip1.source_in_frames
    assert t2.clips[1].timeline_in_frames == clip2.timeline_in_frames
    assert t2.clips[1].timeline_out_frames == clip2.timeline_out_frames
    assert t2.clips[1].source_in_frames == clip2.source_in_frames
    assert len(t2.clips[0].volume_keyframes) == 2

    # Track 3: Existing mono sound track untouched
    t3 = split_seq.tracks[3]
    assert t3.name == "A2"
    assert t3.kind == "sound"
    assert t3.channel_index == 1
    assert len(t3.clips) == 1
    assert t3.clips[0].source_channel == 1


def test_non_embedded_audio_export(tmp_path: Path) -> None:
    """Verify non-embedded audio export creates PCMDescriptor with NetworkLocator."""
    wav_path = generate_sample_tone_wav(tmp_path / "sample_tone_linked.wav")

    media = MediaSourceIR(
        source_id="src_tone_linked",
        name="sample_tone_linked.wav",
        file_path=str(wav_path),
        duration_frames=150,
        edit_rate=Fraction(25, 1),
        sample_rate=48000,
        audio_channels=1,
        has_video=False,
        has_audio=True,
    )

    clip = ClipIR(
        clip_id="c_tone_linked",
        name="Tone Linked Clip",
        source_id="src_tone_linked",
        timeline_in_frames=10,
        timeline_out_frames=60,
        source_in_frames=0,
    )

    track = TrackIR(track_index=0, name="A1", kind="sound", channel_index=1, clips=[clip])
    seq = SequenceIR(
        seq_id="seq_linked",
        name="Linked Seq",
        edit_rate=Fraction(25, 1),
        duration_frames=100,
        tracks=[track],
    )

    project = ProjectIR(
        project_name="Linked Audio Project",
        source_format="sesx",
        media_sources={"src_tone_linked": media},
        sequences=[seq],
    )

    aaf_path = tmp_path / "linked_tone.aaf"
    export_project_to_aaf(project, aaf_path, embed_audio=False)

    with aaf2.open(str(aaf_path), "r") as f:
        assert len(f.content.essencedata) == 0

        pcm_descs = [
            m.descriptor
            for m in f.content.mobs
            if isinstance(m, aaf2.mobs.SourceMob)
            and isinstance(getattr(m, "descriptor", None), aaf2.essence.PCMDescriptor)
        ]
        assert len(pcm_descs) >= 1
        desc = pcm_descs[0]
        assert desc["QuantizationBits"].value == 16
        assert desc["SampleRate"].value == 48000
        loc = desc["Locator"].value[0]
        assert loc["URLString"].value == wav_path.resolve().as_uri()
