from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import aaf2

from machete.exporters.aaf_core import deterministic_mob_id, export_project_to_aaf
from machete.ir import (
    ClipIR,
    EffectNoticeIR,
    MarkerIR,
    MediaSourceIR,
    ProjectIR,
    SequenceIR,
    TrackIR,
)


def test_acceptance_aaf_export(tmp_path: Path) -> None:
    """Acceptance test verifying:

    1. Top-level CompositionMob exists with deterministic MobID.
    2. Track V1 has 4 components: SourceClip(50), Filler(25), SourceClip(50), Filler(25) summing to 150.
    3. Re-exporting the same ProjectIR produces identical MobIDs.
    4. Marker comment is present on comp_mob comments.
    """
    media = MediaSourceIR(
        source_id="src_001",
        name="A001_C001.mov",
        file_path="/media/A001_C001.mov",
        reel_name="A001",
        start_tc_frames=0,
        duration_frames=1000,
        edit_rate=Fraction(25, 1),
        sample_rate=48000,
        audio_channels=2,
        has_video=True,
        has_audio=True,
    )

    clip1 = ClipIR(
        clip_id="clip_001",
        name="Shot 1",
        source_id="src_001",
        timeline_in_frames=0,
        timeline_out_frames=50,
        source_in_frames=0,
    )

    clip2 = ClipIR(
        clip_id="clip_002",
        name="Shot 2",
        source_id="src_001",
        timeline_in_frames=75,
        timeline_out_frames=125,
        source_in_frames=100,
    )

    track_v1 = TrackIR(
        track_index=0,
        name="V1",
        kind="picture",
        clips=[clip1, clip2],
    )

    marker = MarkerIR(
        frame_offset=25,
        duration_frames=1,
        name="Check VFX",
        comment="Needs clean plate",
        color="red",
    )

    seq = SequenceIR(
        seq_id="seq_001",
        name="Sequence 1",
        edit_rate=Fraction(25, 1),
        drop_frame=False,
        sample_rate=48000,
        start_tc_frames=0,
        duration_frames=150,
        tracks=[track_v1],
        markers=[marker],
    )

    project = ProjectIR(
        project_name="Acceptance Project",
        source_format="prproj",
        media_sources={"src_001": media},
        sequences=[seq],
    )

    aaf_file_1 = tmp_path / "test.aaf"
    exported_path_1 = export_project_to_aaf(project, aaf_file_1)
    assert exported_path_1 == aaf_file_1
    assert aaf_file_1.exists()

    # Verify contents of exported AAF
    with aaf2.open(str(aaf_file_1), "r") as f:
        # Top-level CompositionMob exists with deterministic MobID
        top_level_mobs = list(f.content.toplevel())
        assert len(top_level_mobs) == 1
        comp_mob = top_level_mobs[0]
        assert isinstance(comp_mob, aaf2.mobs.CompositionMob)
        assert comp_mob.name == "Sequence 1"
        expected_mob_id = deterministic_mob_id("comp:seq_001")
        assert comp_mob.mob_id == expected_mob_id

        # Track V1 has 4 components: SourceClip(50), Filler(25), SourceClip(50), Filler(25) summing to 150
        v1_slot = None
        for slot in comp_mob.slots:
            if slot.name == "V1":
                v1_slot = slot
                break
        assert v1_slot is not None, "Slot V1 not found on CompositionMob"

        sequence_component = v1_slot.segment
        assert isinstance(sequence_component, aaf2.components.Sequence)
        components = sequence_component.components
        assert len(components) == 4

        comp_types = [type(c).__name__ for c in components]
        comp_lengths = [c.length for c in components]

        assert comp_types == ["SourceClip", "Filler", "SourceClip", "Filler"]
        assert comp_lengths == [50, 25, 50, 25]
        assert sum(comp_lengths) == 150

        # Marker comment is present on comp_mob comments
        comments_dict = dict(comp_mob.comments.items())
        assert any(
            "[RED]" in v and "Check VFX" in v and "Needs clean plate" in v
            for v in comments_dict.values()
        )
        assert "MARKER_0_25" in comments_dict

    # Re-exporting the same ProjectIR produces identical MobIDs
    aaf_file_2 = tmp_path / "test_reexport.aaf"
    export_project_to_aaf(project, aaf_file_2)

    with aaf2.open(str(aaf_file_1), "r") as f1, aaf2.open(str(aaf_file_2), "r") as f2:
        mobs1 = [m.mob_id for m in f1.content.mobs]
        mobs2 = [m.mob_id for m in f2.content.mobs]
        assert len(mobs1) == len(mobs2)
        assert mobs1 == mobs2


def test_sound_track_zero_gap_law(tmp_path: Path) -> None:
    """Verify sound tracks follow the Avid Zero-Gap Law."""
    media = MediaSourceIR(
        source_id="src_audio",
        name="voiceover.wav",
        file_path="/media/voiceover.wav",
        reel_name="VO",
        start_tc_frames=0,
        duration_frames=500,
        edit_rate=Fraction(25, 1),
        sample_rate=48000,
        audio_channels=1,
        has_video=False,
        has_audio=True,
    )

    clip = ClipIR(
        clip_id="c_vo",
        name="VO Line 1",
        source_id="src_audio",
        timeline_in_frames=20,
        timeline_out_frames=80,
        source_in_frames=0,
    )

    track_a1 = TrackIR(
        track_index=0,
        name="A1",
        kind="sound",
        clips=[clip],
    )

    seq = SequenceIR(
        seq_id="seq_audio",
        name="Audio Sequence",
        edit_rate=Fraction(25, 1),
        duration_frames=100,
        tracks=[track_a1],
    )

    project = ProjectIR(
        project_name="Audio Test",
        source_format="prproj",
        media_sources={"src_audio": media},
        sequences=[seq],
    )

    aaf_path = tmp_path / "audio_test.aaf"
    export_project_to_aaf(project, aaf_path)

    with aaf2.open(str(aaf_path), "r") as f:
        comp_mob = list(f.content.toplevel())[0]
        slot = [s for s in comp_mob.slots if s.name == "A1"][0]
        components = slot.segment.components

        # Should be Filler(20), SourceClip(60), Filler(20) summing to 100
        comp_types = [type(c).__name__ for c in components]
        comp_lengths = [c.length for c in components]

        assert comp_types == ["Filler", "SourceClip", "Filler"]
        assert comp_lengths == [20, 60, 20]
        assert sum(comp_lengths) == 100


def test_unsupported_effects_and_clip_markers_as_comments(tmp_path: Path) -> None:
    """Verify clip markers and unsupported effects are stored as comments on the CompositionMob."""
    media = MediaSourceIR(
        source_id="src_fx",
        name="fx_shot.mov",
        duration_frames=300,
        edit_rate=Fraction(25, 1),
    )

    clip = ClipIR(
        clip_id="c_fx",
        name="Shot with FX",
        source_id="src_fx",
        timeline_in_frames=10,
        timeline_out_frames=60,
        source_in_frames=0,
        unsupported_effects=[
            EffectNoticeIR(
                effect_name="LumetriColor",
                parameters_summary="LUT applied",
                requires_manual_recreate=True,
            )
        ],
        markers=[
            MarkerIR(
                frame_offset=15,
                duration_frames=1,
                name="Clip Note",
                comment="Check saturation",
                color="blue",
            )
        ],
    )

    track_v1 = TrackIR(track_index=0, name="V1", kind="picture", clips=[clip])

    seq = SequenceIR(
        seq_id="seq_fx",
        name="FX Sequence",
        edit_rate=Fraction(25, 1),
        duration_frames=100,
        tracks=[track_v1],
    )

    project = ProjectIR(
        project_name="FX Test",
        source_format="prproj",
        media_sources={"src_fx": media},
        sequences=[seq],
    )

    aaf_path = tmp_path / "fx_test.aaf"
    export_project_to_aaf(project, aaf_path)

    with aaf2.open(str(aaf_path), "r") as f:
        comp_mob = list(f.content.toplevel())[0]
        comments_dict = dict(comp_mob.comments.items())

        # Check clip marker (at timeline frame 10 + 15 = 25)
        assert any(
            "[BLUE]" in v and "Clip Note" in v and "Check saturation" in v
            for v in comments_dict.values()
        )
        assert "MARKER_0_25" in comments_dict

        # Check unsupported effect (at timeline frame 10)
        assert any(
            "LumetriColor" in v and "LUT applied" in v
            for v in comments_dict.values()
        )
        assert "EFFECT_1_10" in comments_dict


def test_empty_track_zero_gap_law(tmp_path: Path) -> None:
    """Verify an empty track of duration 200 is filled with a single Filler of length 200."""
    track_empty = TrackIR(track_index=0, name="V1", kind="picture", clips=[])
    seq = SequenceIR(
        seq_id="seq_empty",
        name="Empty Track Sequence",
        edit_rate=Fraction(25, 1),
        duration_frames=200,
        tracks=[track_empty],
    )
    project = ProjectIR(
        project_name="Empty Track Project",
        source_format="prproj",
        media_sources={},
        sequences=[seq],
    )

    aaf_path = tmp_path / "empty_track.aaf"
    export_project_to_aaf(project, aaf_path)

    with aaf2.open(str(aaf_path), "r") as f:
        comp_mob = list(f.content.toplevel())[0]
        slot = comp_mob.slots[0]
        components = slot.segment.components
        assert len(components) == 1
        assert type(components[0]).__name__ == "Filler"
        assert components[0].length == 200
