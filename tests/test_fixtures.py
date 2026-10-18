from __future__ import annotations

import gzip
from pathlib import Path
import wave
import xml.etree.ElementTree as ET

import pytest
try:
    from tests.fixture_factory import generate_all_fixtures
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from fixture_factory import generate_all_fixtures


def test_fixture_generation_and_size_limits(tmp_path: Path) -> None:
    fixtures = generate_all_fixtures(tmp_path)

    expected_keys = {
        "sample_tone.wav",
        "simple_cut.prproj",
        "nested_seq.prproj",
        "sample_audition.sesx",
    }
    assert set(fixtures.keys()) == expected_keys

    for key, path in fixtures.items():
        assert path.exists(), f"Fixture {key} does not exist at {path}"

    xml_keys = ["simple_cut.prproj", "nested_seq.prproj", "sample_audition.sesx"]
    for key in xml_keys:
        path = fixtures[key]
        size = path.stat().st_size
        assert size < 15360, f"Fixture {key} size {size} exceeds 15360 bytes"


def test_prproj_gzip_decompression_and_xml_validity(tmp_path: Path) -> None:
    fixtures = generate_all_fixtures(tmp_path)

    for prproj_key in ["simple_cut.prproj", "nested_seq.prproj"]:
        prproj_path = fixtures[prproj_key]
        with gzip.open(prproj_path, "rb") as gz:
            content = gz.read()
        root = ET.fromstring(content)
        assert root.tag == "PremiereData"


def test_sample_tone_wav_format(tmp_path: Path) -> None:
    fixtures = generate_all_fixtures(tmp_path)
    wav_path = fixtures["sample_tone.wav"]

    with wave.open(str(wav_path), "rb") as wf:
        assert wf.getframerate() == 48000
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getnframes() == 48000 * 6


def test_simple_cut_structure_and_dereference(tmp_path: Path) -> None:
    fixtures = generate_all_fixtures(tmp_path)
    simple_cut_path = fixtures["simple_cut.prproj"]

    with gzip.open(simple_cut_path, "rb") as gz:
        root = ET.fromstring(gz.read())

    id_map = {elem.attrib["ObjectID"]: elem for elem in root if "ObjectID" in elem.attrib}

    # Sequence check
    seq = next(elem for elem in root if elem.tag == "Sequence" and elem.findtext("Name") == "Main_Edit_25fps")
    assert seq.findtext("EditRate") == "25"
    assert seq.findtext("TicksPerFrame") == "10160640000"

    # Sequence marker check
    marker_ref = seq.find("Markers/Marker")
    assert marker_ref is not None
    marker = id_map[marker_ref.attrib["ObjectRef"]]
    assert marker.findtext("Name") == "VFX_Check"
    assert marker.findtext("Comment") == "Check green screen"
    assert marker.findtext("Start") == "254016000000"

    # Dereference chain: Sequence -> TrackGroups -> TrackGroup -> Tracks -> Track -> ClipItems -> TrackItem -> SubClip -> Clip -> Source -> Media
    tg_refs = seq.findall("TrackGroups/TrackGroup")
    assert len(tg_refs) == 2

    video_tg = id_map[tg_refs[0].attrib["ObjectRef"]]
    assert video_tg.findtext("MediaType") == "Video"

    video_track = id_map[video_tg.find("Tracks/Track").attrib["ObjectRef"]]
    assert video_track.findtext("Name") == "V1"

    ti_refs = video_track.findall("ClipItems/TrackItem")
    assert len(ti_refs) == 2

    # Clip 1
    ti_1 = id_map[ti_refs[0].attrib["ObjectRef"]]
    assert ti_1.findtext("Start") == "0"
    assert ti_1.findtext("End") == "508032000000"
    vfc_ref = ti_1.find("Components/VideoFilterComponent")
    assert vfc_ref is not None
    vfc = id_map[vfc_ref.attrib["ObjectRef"]]
    assert vfc.findtext("Name") == "Warp Stabilizer"

    # Dereference Clip 1 down to Media
    sc_1 = id_map[ti_1.find("SubClip").attrib["ObjectRef"]]
    clip_1 = id_map[sc_1.find("Clip").attrib["ObjectRef"]]
    src_1 = id_map[clip_1.find("Source").attrib["ObjectRef"]]
    media_1 = id_map[src_1.find("Media").attrib["ObjectRef"]]
    assert media_1.findtext("Name") == "Shot_01.mov"

    # Clip 2 (L-Cut video at 3s..5s)
    ti_2 = id_map[ti_refs[1].attrib["ObjectRef"]]
    assert ti_2.findtext("Start") == "762048000000"
    assert ti_2.findtext("End") == "1270080000000"
    assert ti_2.findtext("In") == "254016000000"

    # Audio Track A1
    audio_tg = id_map[tg_refs[1].attrib["ObjectRef"]]
    assert audio_tg.findtext("MediaType") == "Audio"
    audio_track = id_map[audio_tg.find("Tracks/Track").attrib["ObjectRef"]]
    assert audio_track.findtext("Name") == "A1"

    audio_ti_refs = audio_track.findall("ClipItems/TrackItem")
    assert len(audio_ti_refs) == 2

    # Audio Clip 2 (J/L cut starts at 2.5s)
    ti_a2 = id_map[audio_ti_refs[1].attrib["ObjectRef"]]
    assert ti_a2.findtext("Start") == "635040000000"
    assert ti_a2.findtext("End") == "1270080000000"

    vol_comp_ref = ti_a2.find("Components/AudioFilterComponent")
    assert vol_comp_ref is not None
    vol_comp = id_map[vol_comp_ref.attrib["ObjectRef"]]
    assert vol_comp.findtext("Name") == "Volume"
    keyframes = vol_comp.findall("Parameter/Keyframes/Keyframe")
    assert len(keyframes) == 2
    assert keyframes[0].findtext("Value") == "1.0"
    assert keyframes[1].findtext("Value") == "0.5"


def test_nested_seq_structure(tmp_path: Path) -> None:
    fixtures = generate_all_fixtures(tmp_path)
    nested_path = fixtures["nested_seq.prproj"]

    with gzip.open(nested_path, "rb") as gz:
        root = ET.fromstring(gz.read())

    seq_names = {elem.findtext("Name") for elem in root.findall("Sequence")}
    assert "Master_Seq" in seq_names
    assert "Child_Seq" in seq_names


def test_sample_audition_structure(tmp_path: Path) -> None:
    fixtures = generate_all_fixtures(tmp_path)
    sesx_path = fixtures["sample_audition.sesx"]

    root = ET.fromstring(sesx_path.read_text(encoding="utf-8"))
    assert root.tag == "session"
    assert root.attrib["sampleRate"] == "48000"
    assert root.attrib["title"] == "Audition_Mix"

    track = root.find("tracks/audioTrack")
    assert track is not None
    assert track.attrib["name"] == "Dialogue_1"

    clips = track.findall("audioClip")
    assert len(clips) == 2
    assert clips[0].attrib["startPoint"] == "0"
    assert clips[0].attrib["endPoint"] == "96000"
    assert clips[0].attrib["sourceInPoint"] == "0"
    assert clips[0].attrib["sourceOutPoint"] == "96000"

    assert clips[1].attrib["startPoint"] == "144000"
    assert clips[1].attrib["endPoint"] == "240000"
    assert clips[1].attrib["sourceInPoint"] == "24000"
    assert clips[1].attrib["sourceOutPoint"] == "120000"

    env = clips[1].find("envelope")
    assert env is not None
    assert len(env.findall("keyframe")) == 2
