from __future__ import annotations

import gzip
import math
import struct
import wave
from fractions import Fraction
from pathlib import Path
import xml.etree.ElementTree as ET

PPRO_TICKS_PER_SEC: int = 254_016_000_000
TICKS_PER_FRAME_25FPS: int = 10_160_640_000


def generate_sample_tone_wav(output_path: Path) -> Path:
    sample_rate: int = 48000
    duration_sec: int = 6
    num_samples: int = sample_rate * duration_sec
    frequency_hz: int = 440
    amplitude: int = 16000

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.setnframes(num_samples)

        frames = bytearray()
        for i in range(num_samples):
            sample_val = int(amplitude * math.sin(2.0 * math.pi * frequency_hz * i / sample_rate))
            frames.extend(struct.pack("<h", sample_val))
        wav_file.writeframes(frames)

    return output_path


def _build_simple_cut_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<PremiereData Version="3">
  <Project ObjectID="1" ObjectUID="81997d81-b51e-450a-93f4-0d2bf552f901">
    <Name>Simple Cut Project</Name>
    <Sequences>
      <Sequence ObjectRef="2" ObjectURef="99e03d98-100a-42c2-8ae7-b2eb60b73df0"/>
    </Sequences>
  </Project>

  <Sequence ObjectID="2" ObjectUID="99e03d98-100a-42c2-8ae7-b2eb60b73df0">
    <Name>Main_Edit_25fps</Name>
    <EditRate>25</EditRate>
    <TicksPerFrame>10160640000</TicksPerFrame>
    <Rate>
      <Numerator>25</Numerator>
      <Denominator>1</Denominator>
    </Rate>
    <Duration>1270080000000</Duration>
    <Markers>
      <Marker ObjectRef="3" ObjectURef="0e5ff306-69f6-4ef3-92f5-b7787f0b5d20"/>
    </Markers>
    <TrackGroups>
      <TrackGroup ObjectRef="4" ObjectURef="11111111-0000-0000-0000-000000000001"/>
      <TrackGroup ObjectRef="5" ObjectURef="22222222-0000-0000-0000-000000000002"/>
    </TrackGroups>
  </Sequence>

  <Marker ObjectID="3" ObjectUID="0e5ff306-69f6-4ef3-92f5-b7787f0b5d20">
    <Name>VFX_Check</Name>
    <Comment>Check green screen</Comment>
    <Type>Comment</Type>
    <Start>254016000000</Start>
    <Time>254016000000</Time>
    <Duration>10160640000</Duration>
    <Color>red</Color>
  </Marker>

  <TrackGroup ObjectID="4" ObjectUID="11111111-0000-0000-0000-000000000001">
    <Index>0</Index>
    <MediaType>Video</MediaType>
    <Tracks>
      <Track ObjectRef="6" ObjectURef="33333333-0000-0000-0000-000000000003"/>
    </Tracks>
  </TrackGroup>

  <Track ObjectID="6" ObjectUID="33333333-0000-0000-0000-000000000003">
    <Index>0</Index>
    <Name>V1</Name>
    <MediaType>Video</MediaType>
    <ClipItems>
      <TrackItem ObjectRef="7" ObjectURef="44444444-0000-0000-0000-000000000004"/>
      <TrackItem ObjectRef="8" ObjectURef="55555555-0000-0000-0000-000000000005"/>
    </ClipItems>
  </Track>
  <TrackItem ObjectID="7" ObjectUID="44444444-0000-0000-0000-000000000004">
    <Name>Shot_01.mov</Name>
    <MediaType>Video</MediaType>
    <Start>0</Start>
    <End>508032000000</End>
    <In>0</In>
    <Out>508032000000</Out>
    <SubClip ObjectRef="9" ObjectURef="66666666-0000-0000-0000-000000000006"/>
    <Components>
      <VideoFilterComponent ObjectRef="10" ObjectURef="77777777-0000-0000-0000-000000000007">
        <Name>Warp Stabilizer</Name>
        <DisplayName>Warp Stabilizer</DisplayName>
      </VideoFilterComponent>
    </Components>
  </TrackItem>

  <VideoFilterComponent ObjectID="10" ObjectUID="77777777-0000-0000-0000-000000000007">
    <Name>Warp Stabilizer</Name>
    <DisplayName>Warp Stabilizer</DisplayName>
  </VideoFilterComponent>

  <SubClip ObjectID="9" ObjectUID="66666666-0000-0000-0000-000000000006">
    <Name>Shot_01.mov</Name>
    <In>0</In>
    <Out>508032000000</Out>
    <Clip ObjectRef="11" ObjectURef="88888888-0000-0000-0000-000000000008"/>
  </SubClip>

  <Clip ObjectID="11" ObjectUID="88888888-0000-0000-0000-000000000008">
    <Name>Shot_01.mov</Name>
    <Source ObjectRef="12" ObjectURef="99999999-0000-0000-0000-000000000009"/>
  </Clip>

  <Source ObjectID="12" ObjectUID="99999999-0000-0000-0000-000000000009">
    <Media ObjectRef="13" ObjectURef="aaaaaaaa-0000-0000-0000-00000000000a"/>
  </Source>

  <Media ObjectID="13" ObjectUID="aaaaaaaa-0000-0000-0000-00000000000a">
    <Name>Shot_01.mov</Name>
    <FilePath>Shot_01.mov</FilePath>
    <ActualMediaFilePath>Shot_01.mov</ActualMediaFilePath>
    <RelativePath>Shot_01.mov</RelativePath>
  </Media>

  <TrackItem ObjectID="8" ObjectUID="55555555-0000-0000-0000-000000000005">
    <Name>Shot_01.mov</Name>
    <MediaType>Video</MediaType>
    <Start>762048000000</Start>
    <End>1270080000000</End>
    <In>254016000000</In>
    <Out>762048000000</Out>
    <SubClip ObjectRef="14" ObjectURef="bbbbbbbb-0000-0000-0000-00000000000b"/>
  </TrackItem>

  <SubClip ObjectID="14" ObjectUID="bbbbbbbb-0000-0000-0000-00000000000b">
    <Name>Shot_01.mov</Name>
    <In>254016000000</In>
    <Out>762048000000</Out>
    <Clip ObjectRef="15" ObjectURef="cccccccc-0000-0000-0000-00000000000c"/>
  </SubClip>

  <Clip ObjectID="15" ObjectUID="cccccccc-0000-0000-0000-00000000000c">
    <Name>Shot_01.mov</Name>
    <Source ObjectRef="16" ObjectURef="dddddddd-0000-0000-0000-00000000000d"/>
  </Clip>

  <Source ObjectID="16" ObjectUID="dddddddd-0000-0000-0000-00000000000d">
    <Media ObjectRef="13" ObjectURef="aaaaaaaa-0000-0000-0000-00000000000a"/>
  </Source>

  <TrackGroup ObjectID="5" ObjectUID="22222222-0000-0000-0000-000000000002">
    <Index>1</Index>
    <MediaType>Audio</MediaType>
    <Tracks>
      <Track ObjectRef="17" ObjectURef="eeeeeeee-0000-0000-0000-00000000000e"/>
    </Tracks>
  </TrackGroup>

  <Track ObjectID="17" ObjectUID="eeeeeeee-0000-0000-0000-00000000000e">
    <Index>0</Index>
    <Name>A1</Name>
    <MediaType>Audio</MediaType>
    <ClipItems>
      <TrackItem ObjectRef="18" ObjectURef="ffffffff-0000-0000-0000-00000000000f"/>
      <TrackItem ObjectRef="19" ObjectURef="10101010-0000-0000-0000-000000000010"/>
    </ClipItems>
  </Track>

  <TrackItem ObjectID="18" ObjectUID="ffffffff-0000-0000-0000-00000000000f">
    <Name>sample_tone.wav</Name>
    <MediaType>Audio</MediaType>
    <Start>0</Start>
    <End>508032000000</End>
    <In>0</In>
    <Out>508032000000</Out>
    <SubClip ObjectRef="20" ObjectURef="12121212-0000-0000-0000-000000000012"/>
  </TrackItem>

  <SubClip ObjectID="20" ObjectUID="12121212-0000-0000-0000-000000000012">
    <Name>sample_tone.wav</Name>
    <In>0</In>
    <Out>508032000000</Out>
    <Clip ObjectRef="21" ObjectURef="13131313-0000-0000-0000-000000000013"/>
  </SubClip>

  <Clip ObjectID="21" ObjectUID="13131313-0000-0000-0000-000000000013">
    <Name>sample_tone.wav</Name>
    <Source ObjectRef="22" ObjectURef="14141414-0000-0000-0000-000000000014"/>
  </Clip>

  <Source ObjectID="22" ObjectUID="14141414-0000-0000-0000-000000000014">
    <Media ObjectRef="23" ObjectURef="15151515-0000-0000-0000-000000000015"/>
  </Source>

  <Media ObjectID="23" ObjectUID="15151515-0000-0000-0000-000000000015">
    <Name>sample_tone.wav</Name>
    <FilePath>sample_tone.wav</FilePath>
    <ActualMediaFilePath>sample_tone.wav</ActualMediaFilePath>
    <RelativePath>sample_tone.wav</RelativePath>
    <SampleRate>48000</SampleRate>
    <AudioChannels>1</AudioChannels>
  </Media>

  <TrackItem ObjectID="19" ObjectUID="10101010-0000-0000-0000-000000000010">
    <Name>sample_tone.wav</Name>
    <MediaType>Audio</MediaType>
    <Start>635040000000</Start>
    <End>1270080000000</End>
    <In>127008000000</In>
    <Out>762048000000</Out>
    <SubClip ObjectRef="24" ObjectURef="16161616-0000-0000-0000-000000000016"/>
    <Components>
      <AudioFilterComponent ObjectRef="25" ObjectURef="17171717-0000-0000-0000-000000000017">
        <Name>Volume</Name>
        <DisplayName>Volume</DisplayName>
        <Parameter>
          <Name>Level</Name>
          <Keyframes>
            <Keyframe ObjectID="26" ObjectUID="18181818-0000-0000-0000-000000000018" Time="0" Value="1.0">
              <Time>0</Time>
              <Value>1.0</Value>
            </Keyframe>
            <Keyframe ObjectID="27" ObjectUID="19191919-0000-0000-0000-000000000019" Time="254016000000" Value="0.5">
              <Time>254016000000</Time>
              <Value>0.5</Value>
            </Keyframe>
          </Keyframes>
        </Parameter>
      </AudioFilterComponent>
    </Components>
  </TrackItem>

  <AudioFilterComponent ObjectID="25" ObjectUID="17171717-0000-0000-0000-000000000017">
    <Name>Volume</Name>
    <DisplayName>Volume</DisplayName>
    <Parameter>
      <Name>Level</Name>
      <Keyframes>
        <Keyframe ObjectID="26" ObjectUID="18181818-0000-0000-0000-000000000018" Time="0" Value="1.0">
          <Time>0</Time>
          <Value>1.0</Value>
        </Keyframe>
        <Keyframe ObjectID="27" ObjectUID="19191919-0000-0000-0000-000000000019" Time="254016000000" Value="0.5">
          <Time>254016000000</Time>
          <Value>0.5</Value>
        </Keyframe>
      </Keyframes>
    </Parameter>
  </AudioFilterComponent>

  <Keyframe ObjectID="26" ObjectUID="18181818-0000-0000-0000-000000000018" Time="0" Value="1.0">
    <Time>0</Time>
    <Value>1.0</Value>
  </Keyframe>

  <Keyframe ObjectID="27" ObjectUID="19191919-0000-0000-0000-000000000019" Time="254016000000" Value="0.5">
    <Time>254016000000</Time>
    <Value>0.5</Value>
  </Keyframe>

  <SubClip ObjectID="24" ObjectUID="16161616-0000-0000-0000-000000000016">
    <Name>sample_tone.wav</Name>
    <In>127008000000</In>
    <Out>762048000000</Out>
    <Clip ObjectRef="28" ObjectURef="20202020-0000-0000-0000-000000000020"/>
  </SubClip>

  <Clip ObjectID="28" ObjectUID="20202020-0000-0000-0000-000000000020">
    <Name>sample_tone.wav</Name>
    <Source ObjectRef="29" ObjectURef="21212121-0000-0000-0000-000000000021"/>
  </Clip>

  <Source ObjectID="29" ObjectUID="21212121-0000-0000-0000-000000000021">
    <Media ObjectRef="23" ObjectURef="15151515-0000-0000-0000-000000000015"/>
  </Source>
</PremiereData>
"""


def generate_simple_cut_prproj(output_path: Path) -> Path:
    xml_str = _build_simple_cut_xml()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(output_path, "wb") as gz:
        gz.write(xml_str.encode("utf-8"))
    return output_path


def _build_nested_seq_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<PremiereData Version="3">
  <Project ObjectID="1" ObjectUID="a0000001-0000-0000-0000-000000000001">
    <Name>Nested Sequence Project</Name>
    <Sequences>
      <Sequence ObjectRef="2" ObjectURef="a0000002-0000-0000-0000-000000000002"/>
      <Sequence ObjectRef="3" ObjectURef="a0000003-0000-0000-0000-000000000003"/>
    </Sequences>
  </Project>

  <!-- Master Sequence: duration 3s, nested clip from 1s to 3s (duration 2s) -->
  <Sequence ObjectID="2" ObjectUID="a0000002-0000-0000-0000-000000000002">
    <Name>Master_Seq</Name>
    <EditRate>25</EditRate>
    <TicksPerFrame>10160640000</TicksPerFrame>
    <Rate>
      <Numerator>25</Numerator>
      <Denominator>1</Denominator>
    </Rate>
    <Duration>762048000000</Duration>
    <TrackGroups>
      <TrackGroup ObjectRef="4" ObjectURef="a0000004-0000-0000-0000-000000000004"/>
    </TrackGroups>
  </Sequence>

  <TrackGroup ObjectID="4" ObjectUID="a0000004-0000-0000-0000-000000000004">
    <Index>0</Index>
    <MediaType>Video</MediaType>
    <Tracks>
      <Track ObjectRef="5" ObjectURef="a0000005-0000-0000-0000-000000000005"/>
    </Tracks>
  </TrackGroup>

  <Track ObjectID="5" ObjectUID="a0000005-0000-0000-0000-000000000005">
    <Index>0</Index>
    <Name>V1</Name>
    <MediaType>Video</MediaType>
    <ClipItems>
      <TrackItem ObjectRef="6" ObjectURef="a0000006-0000-0000-0000-000000000006"/>
    </ClipItems>
  </Track>

  <TrackItem ObjectID="6" ObjectUID="a0000006-0000-0000-0000-000000000006">
    <Name>Child_Seq</Name>
    <MediaType>Video</MediaType>
    <Start>254016000000</Start>
    <End>762048000000</End>
    <In>0</In>
    <Out>508032000000</Out>
    <SubClip ObjectRef="7" ObjectURef="a0000007-0000-0000-0000-000000000007"/>
  </TrackItem>

  <SubClip ObjectID="7" ObjectUID="a0000007-0000-0000-0000-000000000007">
    <Name>Child_Seq</Name>
    <In>0</In>
    <Out>508032000000</Out>
    <Clip ObjectRef="8" ObjectURef="a0000008-0000-0000-0000-000000000008"/>
  </SubClip>

  <Clip ObjectID="8" ObjectUID="a0000008-0000-0000-0000-000000000008">
    <Name>Child_Seq</Name>
    <Sequence ObjectRef="3" ObjectURef="a0000003-0000-0000-0000-000000000003"/>
    <Source ObjectRef="9" ObjectURef="a0000009-0000-0000-0000-000000000009"/>
  </Clip>

  <Source ObjectID="9" ObjectUID="a0000009-0000-0000-0000-000000000009">
    <Sequence ObjectRef="3" ObjectURef="a0000003-0000-0000-0000-000000000003"/>
  </Source>

  <!-- Child Sequence: duration 2s, 2 cuts (Shot_A, Shot_B each 1s) -->
  <Sequence ObjectID="3" ObjectUID="a0000003-0000-0000-0000-000000000003">
    <Name>Child_Seq</Name>
    <EditRate>25</EditRate>
    <TicksPerFrame>10160640000</TicksPerFrame>
    <Rate>
      <Numerator>25</Numerator>
      <Denominator>1</Denominator>
    </Rate>
    <Duration>508032000000</Duration>
    <TrackGroups>
      <TrackGroup ObjectRef="10" ObjectURef="a0000010-0000-0000-0000-000000000010"/>
    </TrackGroups>
  </Sequence>

  <TrackGroup ObjectID="10" ObjectUID="a0000010-0000-0000-0000-000000000010">
    <Index>0</Index>
    <MediaType>Video</MediaType>
    <Tracks>
      <Track ObjectRef="11" ObjectURef="a0000011-0000-0000-0000-000000000011"/>
    </Tracks>
  </TrackGroup>

  <Track ObjectID="11" ObjectUID="a0000011-0000-0000-0000-000000000011">
    <Index>0</Index>
    <Name>V1</Name>
    <MediaType>Video</MediaType>
    <ClipItems>
      <TrackItem ObjectRef="12" ObjectURef="a0000012-0000-0000-0000-000000000012"/>
      <TrackItem ObjectRef="13" ObjectURef="a0000013-0000-0000-0000-000000000013"/>
    </ClipItems>
  </Track>

  <!-- Cut 1: Shot_A.mov 0s..1s -->
  <TrackItem ObjectID="12" ObjectUID="a0000012-0000-0000-0000-000000000012">
    <Name>Shot_A.mov</Name>
    <MediaType>Video</MediaType>
    <Start>0</Start>
    <End>254016000000</End>
    <In>0</In>
    <Out>254016000000</Out>
    <SubClip ObjectRef="14" ObjectURef="a0000014-0000-0000-0000-000000000014"/>
  </TrackItem>

  <SubClip ObjectID="14" ObjectUID="a0000014-0000-0000-0000-000000000014">
    <Name>Shot_A.mov</Name>
    <In>0</In>
    <Out>254016000000</Out>
    <Clip ObjectRef="15" ObjectURef="a0000015-0000-0000-0000-000000000015"/>
  </SubClip>

  <Clip ObjectID="15" ObjectUID="a0000015-0000-0000-0000-000000000015">
    <Name>Shot_A.mov</Name>
    <Source ObjectRef="16" ObjectURef="a0000016-0000-0000-0000-000000000016"/>
  </Clip>

  <Source ObjectID="16" ObjectUID="a0000016-0000-0000-0000-000000000016">
    <Media ObjectRef="17" ObjectURef="a0000017-0000-0000-0000-000000000017"/>
  </Source>

  <Media ObjectID="17" ObjectUID="a0000017-0000-0000-0000-000000000017">
    <Name>Shot_A.mov</Name>
    <FilePath>Shot_A.mov</FilePath>
    <ActualMediaFilePath>Shot_A.mov</ActualMediaFilePath>
    <RelativePath>Shot_A.mov</RelativePath>
  </Media>

  <!-- Cut 2: Shot_B.mov 1s..2s -->
  <TrackItem ObjectID="13" ObjectUID="a0000013-0000-0000-0000-000000000013">
    <Name>Shot_B.mov</Name>
    <MediaType>Video</MediaType>
    <Start>254016000000</Start>
    <End>508032000000</End>
    <In>0</In>
    <Out>254016000000</Out>
    <SubClip ObjectRef="18" ObjectURef="a0000018-0000-0000-0000-000000000018"/>
  </TrackItem>

  <SubClip ObjectID="18" ObjectUID="a0000018-0000-0000-0000-000000000018">
    <Name>Shot_B.mov</Name>
    <In>0</In>
    <Out>254016000000</Out>
    <Clip ObjectRef="19" ObjectURef="a0000019-0000-0000-0000-000000000019"/>
  </SubClip>

  <Clip ObjectID="19" ObjectUID="a0000019-0000-0000-0000-000000000019">
    <Name>Shot_B.mov</Name>
    <Source ObjectRef="20" ObjectURef="a0000020-0000-0000-0000-000000000020"/>
  </Clip>

  <Source ObjectID="20" ObjectUID="a0000020-0000-0000-0000-000000000020">
    <Media ObjectRef="21" ObjectURef="a0000021-0000-0000-0000-000000000021"/>
  </Source>

  <Media ObjectID="21" ObjectUID="a0000021-0000-0000-0000-000000000021">
    <Name>Shot_B.mov</Name>
    <FilePath>Shot_B.mov</FilePath>
    <ActualMediaFilePath>Shot_B.mov</ActualMediaFilePath>
    <RelativePath>Shot_B.mov</RelativePath>
  </Media>
</PremiereData>
"""


def generate_nested_seq_prproj(output_path: Path) -> Path:
    xml_str = _build_nested_seq_xml()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(output_path, "wb") as gz:
        gz.write(xml_str.encode("utf-8"))
    return output_path


def _build_sample_audition_sesx_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<session version="1.0" title="Audition_Mix" sampleRate="48000">
  <name>Audition_Mix</name>
  <sampleRate>48000</sampleRate>
  <files>
    <file id="1" relativePath="sample_tone.wav" mediaPath="sample_tone.wav" name="sample_tone.wav">
      <sampleRate>48000</sampleRate>
      <channels>1</channels>
      <duration>288000</duration>
    </file>
  </files>
  <tracks>
    <audioTrack name="Dialogue_1" id="1" trackIndex="0">
      <name>Dialogue_1</name>
      <trackIndex>0</trackIndex>
      <audioClip name="sample_tone.wav" startPoint="0" endPoint="96000" sourceInPoint="0" sourceOutPoint="96000" fileID="1" relativePath="sample_tone.wav">
        <name>sample_tone.wav</name>
        <startPoint>0</startPoint>
        <endPoint>96000</endPoint>
        <sourceInPoint>0</sourceInPoint>
        <sourceOutPoint>96000</sourceOutPoint>
        <source fileID="1" relativePath="sample_tone.wav"/>
      </audioClip>
      <audioClip name="sample_tone.wav" startPoint="144000" endPoint="240000" sourceInPoint="24000" sourceOutPoint="120000" fileID="1" relativePath="sample_tone.wav">
        <name>sample_tone.wav</name>
        <startPoint>144000</startPoint>
        <endPoint>240000</endPoint>
        <sourceInPoint>24000</sourceInPoint>
        <sourceOutPoint>120000</sourceOutPoint>
        <source fileID="1" relativePath="sample_tone.wav"/>
        <envelope parameter="volume">
          <keyframe sample="0" position="0" time="0" value="1.0"/>
          <keyframe sample="48000" position="48000" time="1" value="0.5"/>
        </envelope>
        <volumeAutomation>
          <keyframe sample="0" value="1.0"/>
          <keyframe sample="48000" value="0.5"/>
        </volumeAutomation>
        <keyframes>
          <keyframe sample="0" offset="0" time="0" value="1.0"/>
          <keyframe sample="48000" offset="48000" time="1" value="0.5"/>
        </keyframes>
      </audioClip>
    </audioTrack>
  </tracks>
</session>
"""


def generate_sample_audition_sesx(output_path: Path) -> Path:
    xml_str = _build_sample_audition_sesx_xml()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(xml_str, encoding="utf-8")
    return output_path


def generate_all_fixtures(base_dir: Path) -> dict[str, Path]:
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    wav_path = generate_sample_tone_wav(base_dir / "sample_tone.wav")
    simple_cut_path = generate_simple_cut_prproj(base_dir / "simple_cut.prproj")
    nested_seq_path = generate_nested_seq_prproj(base_dir / "nested_seq.prproj")
    sesx_path = generate_sample_audition_sesx(base_dir / "sample_audition.sesx")

    return {
        "sample_tone.wav": wav_path,
        "simple_cut.prproj": simple_cut_path,
        "nested_seq.prproj": nested_seq_path,
        "sample_audition.sesx": sesx_path,
    }
