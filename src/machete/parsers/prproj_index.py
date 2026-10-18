from __future__ import annotations

import gzip
from pathlib import Path
import xml.etree.ElementTree as ET


class PrProjIndex:
    def __init__(self, path: str | Path) -> None:
        file_path = Path(path)
        with open(file_path, "rb") as f:
            magic = f.read(2)

        if magic == b"\x1f\x8b":
            with gzip.open(file_path, "rb") as gz:
                tree = ET.parse(gz)
        else:
            with open(file_path, "rb") as f:
                tree = ET.parse(f)

        self.root: ET.Element = tree.getroot()
        self.by_id: dict[str, ET.Element] = {}
        self.by_uid: dict[str, ET.Element] = {}

        for elem in self.root.iter():
            obj_id = elem.attrib.get("ObjectID")
            if obj_id is not None:
                self.by_id[obj_id] = elem
            obj_uid = elem.attrib.get("ObjectUID")
            if obj_uid is not None:
                self.by_uid[obj_uid] = elem

    def resolve(self, elem_or_ref: ET.Element | None) -> ET.Element | None:
        if elem_or_ref is None:
            return None
        if "ObjectRef" in elem_or_ref.attrib:
            ref_id = elem_or_ref.attrib["ObjectRef"]
            target = self.by_id.get(ref_id)
            if target is not None:
                return self.resolve(target)
        if "ObjectURef" in elem_or_ref.attrib:
            ref_uid = elem_or_ref.attrib["ObjectURef"]
            target = self.by_uid.get(ref_uid)
            if target is not None:
                return self.resolve(target)
        if "ObjectRef" in elem_or_ref.attrib or "ObjectURef" in elem_or_ref.attrib:
            return None
        return elem_or_ref

    def deref(self, parent: ET.Element | None, child_xpath: str) -> ET.Element | None:
        if parent is None:
            return None
        child = parent.find(child_xpath)
        return self.resolve(child)

    def deref_all(self, parent: ET.Element | None, children_xpath: str) -> list[ET.Element]:
        if parent is None:
            return []
        children = parent.findall(children_xpath)
        resolved = [self.resolve(c) for c in children]
        return [r for r in resolved if r is not None]

    def list_sequences(self) -> list[ET.Element]:
        return [
            elem for elem in self.root.iter()
            if (elem.tag == "Sequence" or elem.tag.endswith("Sequence"))
            and "ObjectRef" not in elem.attrib
            and "ObjectURef" not in elem.attrib
        ]

    def list_media(self) -> list[ET.Element]:
        return [
            elem for elem in self.root.iter()
            if (elem.tag == "Media" or elem.tag.endswith("Media"))
            and "ObjectRef" not in elem.attrib
            and "ObjectURef" not in elem.attrib
        ]
