# TASK T03: Low-Level `.prproj` GZIP Reader & Pointer Graph Indexer

- **Primary Model:** Gemini 3.8 Flash
- **Escalation Model:** Gemini 4 Argon
- **Allowed Context (Read):**
  - `.antigravity/rules.md`
  - `tests/fixture_factory.py`
- **Target Outputs (Write):**
  - `src/machete/parsers/__init__.py`
  - `src/machete/parsers/prproj_index.py`
  - `tests/test_prproj_index.py`

## 1. OBJECTIVE
Build a fast, memory-safe indexer for Adobe Premiere `.prproj` files that decompresses the GZIP XML stream, indexes every element by `ObjectID` and `ObjectUID`, and resolves arbitrary pointer chains (`ObjectRef` and `ObjectURef`).

## 2. SPECIFICATIONS (`src/machete/parsers/prproj_index.py`)
Create class `PrProjIndex`:
- `__init__(self, path: str | Path)`:
  - Automatically detect if the file is GZIP-compressed (magic bytes `1f 8b`) or plain XML.
  - Parse into `xml.etree.ElementTree.Element`.
  - Build two lookup dictionaries in a single pass over `root.iter()`:
    - `self.by_id: dict[str, ET.Element]` (from attribute `ObjectID`)
    - `self.by_uid: dict[str, ET.Element]` (from attribute `ObjectUID`)
- `resolve(self, elem_or_ref: ET.Element | None) -> ET.Element | None`:
  - If `elem_or_ref` has `ObjectRef` attribute, return `self.by_id.get(elem_or_ref.attrib["ObjectRef"])`.
  - If `elem_or_ref` has `ObjectURef` attribute, return `self.by_uid.get(elem_or_ref.attrib["ObjectURef"])`.
  - Otherwise return `elem_or_ref`.
- `deref(self, parent: ET.Element, child_xpath: str) -> ET.Element | None`:
  - Find child at `child_xpath` and return `self.resolve(child)`.
- `deref_all(self, parent: ET.Element, children_xpath: str) -> list[ET.Element]`:
  - Find all matching elements at `children_xpath`, resolve each via `self.resolve()`, and filter out `None`.
- `list_sequences(self) -> list[ET.Element]`:
  - Return all `<Sequence>` elements in document order.
- `list_media(self) -> list[ET.Element]`:
  - Return all `<Media>` elements in document order.

## 3. ACCEPTANCE TESTS (`tests/test_prproj_index.py`)
1. Generate fixtures via `generate_all_fixtures(tmp_path)`.
2. Load `simple_cut.prproj` with `PrProjIndex` and verify:
   - `len(index.list_sequences()) == 1`
   - Following `Sequence -> TrackGroups/TrackGroup -> Tracks/Track -> ClipItems -> TrackItems/TrackItem -> SubClip -> Clip -> Source -> Media` via `deref()` and `deref_all()` reaches the `<Media>` element and extracts `<FilePath>`.

## 4. STOP RULES
- Do NOT convert to `ProjectIR` in this task (that belongs to `T04`).
- Run `pytest tests/test_prproj_index.py` and stop immediately when green.
