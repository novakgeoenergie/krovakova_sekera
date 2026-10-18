from __future__ import annotations

from pathlib import Path

from machete.parsers.prproj_index import PrProjIndex
from tests.fixture_factory import generate_all_fixtures


def test_simple_cut_prproj_indexing(tmp_path: Path) -> None:
    fixtures = generate_all_fixtures(tmp_path)
    simple_cut_path = fixtures["simple_cut.prproj"]

    index = PrProjIndex(simple_cut_path)

    sequences = index.list_sequences()
    assert len(sequences) >= 1
    seq = sequences[0]
    assert seq.findtext("Name") == "Main_Edit_25fps"

    track_groups = index.deref_all(seq, "TrackGroups/TrackGroup")
    assert len(track_groups) == 2

    # Video track group
    video_tg = track_groups[0]
    tracks = index.deref_all(video_tg, "Tracks/Track")
    assert len(tracks) == 1
    track = tracks[0]
    assert track.findtext("Name") == "V1"

    track_items = index.deref_all(track, "ClipItems/TrackItem")
    assert len(track_items) == 2
    item = track_items[0]
    assert item.findtext("Name") == "Shot_01.mov"

    subclip = index.deref(item, "SubClip")
    assert subclip is not None

    clip = index.deref(subclip, "Clip")
    assert clip is not None

    source = index.deref(clip, "Source")
    assert source is not None

    media = index.deref(source, "Media")
    assert media is not None

    file_path = media.findtext("FilePath")
    assert file_path == "Shot_01.mov"

    media_list = index.list_media()
    assert len(media_list) == 2
    media_paths = {m.findtext("FilePath") for m in media_list}
    assert media_paths == {"Shot_01.mov", "sample_tone.wav"}


def test_nested_seq_prproj_indexing(tmp_path: Path) -> None:
    fixtures = generate_all_fixtures(tmp_path)
    nested_seq_path = fixtures["nested_seq.prproj"]

    index = PrProjIndex(nested_seq_path)

    sequences = index.list_sequences()
    assert len(sequences) == 2

    seq_names = {s.findtext("Name") for s in sequences}
    assert seq_names == {"Child_Seq", "Master_Seq"}


def test_uncompressed_xml(tmp_path: Path) -> None:
    raw_xml = """<?xml version="1.0" encoding="UTF-8"?>
<PremiereData Version="3">
  <Project ObjectID="1">
    <Name>Test</Name>
  </Project>
  <Sequence ObjectID="2">
    <Name>Seq_1</Name>
  </Sequence>
</PremiereData>
"""
    xml_path = tmp_path / "plain.prproj"
    xml_path.write_text(raw_xml, encoding="utf-8")

    index = PrProjIndex(xml_path)
    sequences = index.list_sequences()
    assert len(sequences) == 1
    assert sequences[0].findtext("Name") == "Seq_1"
