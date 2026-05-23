"""Core mapper: cross-reference cell line identifiers across databases."""

import csv
import os
from dataclasses import dataclass, asdict, fields
from pathlib import Path
from typing import Optional


@dataclass
class CellLine:
    """A cell line with identifiers from multiple databases."""

    depmap_id: str
    cell_line_name: str
    stripped_name: str
    cosmic_id: str
    sanger_id: str
    lineage: str
    disease: str
    aliases: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    def __repr__(self) -> str:
        return f"<CellLine: {self.cell_line_name} (ACH={self.depmap_id}, COSMIC={self.cosmic_id}, Sanger={self.sanger_id})>"


class CellLineMapper:
    """Look up and cross-reference cell line identifiers.

    Usage::

        mapper = CellLineMapper()
        mapper.from_name("A549")          # -> CellLine
        mapper.from_ach("ACH-000024")     # -> CellLine
        mapper.from_cosmic("905952")      # -> CellLine
        mapper.search("A5")               # -> list[CellLine] (fuzzy)
    """

    def __init__(self, data_path: Optional[str] = None):
        """Load the mapping table.

        Args:
            data_path: Path to mappings.csv. Defaults to the bundled data file.
        """
        if data_path is None:
            data_path = Path(__file__).parent / "data" / "mappings.csv"
        self._data: list[CellLine] = []
        self._by_ach: dict[str, CellLine] = {}
        self._by_name: dict[str, CellLine] = {}
        self._by_stripped: dict[str, CellLine] = {}
        self._by_cosmic: dict[str, CellLine] = {}
        self._by_sanger: dict[str, CellLine] = {}
        self._load(data_path)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self, path: str | Path) -> None:
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                cl = CellLine(
                    depmap_id=row["depmap_id"].strip(),
                    cell_line_name=row["cell_line_name"].strip(),
                    stripped_name=row["stripped_name"].strip(),
                    cosmic_id=row["cosmic_id"].strip(),
                    sanger_id=row["sanger_id"].strip(),
                    lineage=row["lineage"].strip(),
                    disease=row["disease"].strip(),
                    aliases=row.get("aliases", "").strip(),
                )
                self._data.append(cl)
                self._by_ach[cl.depmap_id] = cl
                self._by_name[cl.cell_line_name.lower()] = cl
                self._by_stripped[cl.stripped_name.lower()] = cl
                if cl.cosmic_id:
                    self._by_cosmic[cl.cosmic_id] = cl
                if cl.sanger_id:
                    self._by_sanger[cl.sanger_id] = cl

    # ------------------------------------------------------------------
    # Exact lookups
    # ------------------------------------------------------------------

    def from_ach(self, ach_id: str) -> Optional[CellLine]:
        """Look up by DepMap ACH ID (e.g. 'ACH-000024')."""
        return self._by_ach.get(ach_id)

    def from_name(self, name: str) -> Optional[CellLine]:
        """Look up by cell line name (case-insensitive, e.g. 'A549')."""
        return self._by_name.get(name.lower())

    def from_cosmic(self, cosmic_id: str) -> Optional[CellLine]:
        """Look up by COSMIC ID (e.g. '905952')."""
        return self._by_cosmic.get(cosmic_id)

    def from_sanger(self, sanger_id: str) -> Optional[CellLine]:
        """Look up by Sanger Model ID (e.g. 'SIDM000218')."""
        return self._by_sanger.get(sanger_id)

    # ------------------------------------------------------------------
    # Fuzzy search
    # ------------------------------------------------------------------

    def search(self, query: str, limit: int = 10) -> list[CellLine]:
        """Fuzzy search by name, ACH, COSMIC, or Sanger ID.

        Matches if *query* appears anywhere in the cell-line name
        (case-insensitive) or matches the start of an ID field.
        """
        q = query.lower().strip()
        results: list[CellLine] = []

        # exact prefix matches first
        if q in self._by_name:
            results.append(self._by_name[q])
        if q in self._by_ach:
            cl = self._by_ach[q]
            if cl not in results:
                results.append(cl)
        if q in self._by_cosmic:
            cl = self._by_cosmic[q]
            if cl not in results:
                results.append(cl)
        if q in self._by_sanger:
            cl = self._by_sanger[q]
            if cl not in results:
                results.append(cl)

        # substring search on name and aliases
        for cl in self._data:
            if cl in results:
                continue
            if q in cl.cell_line_name.lower() or q in cl.stripped_name.lower() or q in cl.aliases.lower():
                results.append(cl)
            if len(results) >= limit:
                break

        return results[:limit]

    # ------------------------------------------------------------------
    # Bulk & filtering
    # ------------------------------------------------------------------

    def by_lineage(self, lineage: str) -> list[CellLine]:
        """Return all cell lines matching a lineage (case-insensitive)."""
        l = lineage.lower().strip()
        return [cl for cl in self._data if l in cl.lineage.lower()]

    def by_disease(self, disease: str) -> list[CellLine]:
        """Return all cell lines matching a disease string (case-insensitive)."""
        d = disease.lower().strip()
        return [cl for cl in self._data if d in cl.disease.lower()]

    def all(self) -> list[CellLine]:
        """Return all cell lines in the mapping."""
        return list(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return f"<CellLineMapper: {len(self)} cell lines>"

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------

    def ach_to_name(self, ach_id: str) -> Optional[str]:
        """ACH ID → cell line name."""
        cl = self.from_ach(ach_id)
        return cl.cell_line_name if cl else None

    def ach_to_cosmic(self, ach_id: str) -> Optional[str]:
        """ACH ID → COSMIC ID."""
        cl = self.from_ach(ach_id)
        return cl.cosmic_id if cl else None

    def ach_to_sanger(self, ach_id: str) -> Optional[str]:
        """ACH ID → Sanger Model ID."""
        cl = self.from_ach(ach_id)
        return cl.sanger_id if cl else None

    def name_to_ach(self, name: str) -> Optional[str]:
        """Cell line name → ACH ID."""
        cl = self.from_name(name)
        return cl.depmap_id if cl else None

    def name_to_cosmic(self, name: str) -> Optional[str]:
        """Cell line name → COSMIC ID."""
        cl = self.from_name(name)
        return cl.cosmic_id if cl else None

    def name_to_sanger(self, name: str) -> Optional[str]:
        """Cell line name → Sanger Model ID."""
        cl = self.from_name(name)
        return cl.sanger_id if cl else None

    def cosmic_to_ach(self, cosmic_id: str) -> Optional[str]:
        """COSMIC ID → ACH ID."""
        cl = self.from_cosmic(cosmic_id)
        return cl.depmap_id if cl else None

    def cosmic_to_name(self, cosmic_id: str) -> Optional[str]:
        """COSMIC ID → cell line name."""
        cl = self.from_cosmic(cosmic_id)
        return cl.cell_line_name if cl else None

    def sanger_to_ach(self, sanger_id: str) -> Optional[str]:
        """Sanger ID → ACH ID."""
        cl = self.from_sanger(sanger_id)
        return cl.depmap_id if cl else None

    def sanger_to_name(self, sanger_id: str) -> Optional[str]:
        """Sanger ID → cell line name."""
        cl = self.from_sanger(sanger_id)
        return cl.cell_line_name if cl else None


def load_mapper(data_path: Optional[str] = None) -> CellLineMapper:
    """Convenience function: load a CellLineMapper from the bundled data."""
    return CellLineMapper(data_path)
