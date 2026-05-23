#!/usr/bin/env python3
"""Built-in data builder: merge local DepMap and Cell Model Passports files.

How to use:
    1. Download Model.csv from https://depmap.org/portal/download
       → put it in the data/ folder (optional — model_list alone works too)
    2. Download model_list_*.csv from https://cellmodelpassports.sanger.ac.uk/downloads
       → put it in the data/ folder
    3. Run: python scripts/build_bundled_data.py

No network access needed — all files are read locally.
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT = ROOT / "src" / "cell_id_mapper" / "data" / "mappings.csv"

FIELDS = [
    "depmap_id", "cell_line_name", "stripped_name",
    "cosmic_id", "sanger_id", "lineage", "disease", "aliases",
]

# --- helpers ---

def _clean_cosmic(val: str) -> str:
    """Strip .0 suffix from COSMIC IDs stored as floats."""
    val = val.strip()
    if val.endswith(".0") and val.replace(".0", "").isdigit():
        return val[:-2]
    return val


def _strip(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", name)


def _find_model_list() -> Path | None:
    """Find a model_list_*.csv file in the data directory."""
    candidates = sorted(DATA_DIR.glob("model_list_*.csv"), reverse=True)
    return candidates[0] if candidates else None


def _find_model_csv() -> Path | None:
    """Find Model.csv in the data directory."""
    p = DATA_DIR / "Model.csv"
    return p if p.exists() else None


# Lineages to exclude (non-cancer, normal, or ambiguous)
_EXCLUDE_LINEAGES = {
    "normal", "fibroblast", "hair", "embryonal", "other",
    "unknown", "placenta", "", "unspecified",
}

_EXCLUDE_DISEASES = {
    "normal", "fibroblast", "unknown", "unspecified", "",
}


def _keep_entry(entry: dict) -> bool:
    """Return True if this entry should be included in the final dataset."""
    # Must have at least one cross-reference ID
    if not entry["depmap_id"] and not entry["cosmic_id"] and not entry["sanger_id"]:
        return False

    lineage = entry["lineage"].strip().lower()
    disease = entry["disease"].strip().lower()

    if lineage in _EXCLUDE_LINEAGES:
        return False
    if "normal" in lineage and "tumour" not in lineage:
        return False

    return True


def _dedup(rows: list[dict]) -> list[dict]:
    """Remove duplicates by stripped_name, keeping the entry with more IDs."""
    best: dict[str, dict] = {}
    for r in rows:
        key = r["stripped_name"].lower()
        if not key:
            continue
        if key not in best:
            best[key] = r
        else:
            # keep the entry with more non-empty ID fields
            old_score = sum(1 for k in ("depmap_id", "cosmic_id", "sanger_id") if best[key][k])
            new_score = sum(1 for k in ("depmap_id", "cosmic_id", "sanger_id") if r[k])
            if new_score > old_score:
                best[key] = r
            elif new_score == old_score and r["lineage"]:
                if not best[key]["lineage"]:
                    best[key] = r

    return sorted(best.values(), key=lambda r: r["stripped_name"].lower())


def load_model_list(path: Path) -> dict[str, dict]:
    """Load Cell Model Passports model_list CSV.

    Returns dict keyed by cell line name (lowercase), with all cross-refs.
    """
    by_name: dict[str, dict] = {}
    count = 0
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            name = (row.get("model_name") or "").strip()
            if not name or name.lower() == "unknown":
                continue
            count += 1
            aliases = row.get("synonyms", "").strip()
            entry = {
                "depmap_id": (row.get("BROAD_ID") or "").strip(),
                "cell_line_name": name,
                "stripped_name": _strip(name),
                "cosmic_id": _clean_cosmic((row.get("COSMIC_ID") or "").strip()),
                "sanger_id": (row.get("model_id") or "").strip(),
                "lineage": (row.get("tissue") or "").strip(),
                "disease": (row.get("cancer_type") or "").strip(),
                "aliases": aliases,
            }
            by_name[name.lower()] = entry
            # also index by stripped name
            stripped = _strip(name).lower()
            if stripped != name.lower():
                by_name.setdefault(stripped, entry)
    print(f"  → Loaded {count} entries from {path.name}")
    return by_name


def load_model_csv(path: Path, enrich: dict[str, dict] | None = None) -> list[dict]:
    """Load DepMap Model.csv and optionally enrich with model_list data."""
    rows: list[dict] = []
    seen_names: set[str] = set()
    count = 0

    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            name = (row.get("CellLineName") or "").strip()
            if not name:
                continue
            count += 1
            seen_names.add(name.lower())
            cosmic = _clean_cosmic((row.get("COSMICID") or "").strip())

            # enrich from model_list if COSMIC ID is missing
            if (not cosmic) and enrich:
                ml = enrich.get(name.lower())
                if ml:
                    cosmic = ml.get("cosmic_id", "")

            aliases = (row.get("Aliases") or "").strip()

            rows.append({
                "depmap_id": (row.get("ModelID") or "").strip(),
                "cell_line_name": name,
                "stripped_name": (row.get("StrippedCellLineName") or "").strip(),
                "cosmic_id": cosmic,
                "sanger_id": (row.get("SangerModelID") or "").strip(),
                "lineage": (row.get("OncotreeLineage") or "").strip(),
                "disease": (row.get("PrimaryDisease") or "").strip(),
                "aliases": aliases,
            })
    print(f"  → Loaded {count} entries from {path.name}")
    return rows, seen_names


# --- main ---

def main():
    model_list_path = _find_model_list()
    model_csv_path = _find_model_csv()

    if not model_list_path and not model_csv_path:
        print("No data files found in data/ folder.")
        print("Download at least one of:")
        print("  - Model.csv from https://depmap.org/portal/download")
        print("  - model_list_*.csv from https://cellmodelpassports.sanger.ac.uk/downloads")
        print(f"Place them in: {DATA_DIR}")
        sys.exit(1)

    # Step 1: Load model_list as enrichment source
    ml_data: dict[str, dict] = {}
    if model_list_path:
        ml_data = load_model_list(model_list_path)

    # Step 2: Load Model.csv (primary) or fall back to model_list
    rows: list[dict]
    if model_csv_path:
        rows, seen = load_model_csv(model_csv_path, enrich=ml_data)
        # Step 3: Add any model_list entries not already in Model.csv
        added = 0
        for name_lower, entry in ml_data.items():
            if name_lower not in seen and entry.get("depmap_id"):
                rows.append(entry)
                added += 1
        if added:
            print(f"  → Added {added} extra entries from model_list")
    else:
        print("Model.csv not found — building from model_list alone.")
        rows = list(ml_data.values())

    # Step 4: Filter and deduplicate
    before = len(rows)
    rows = [r for r in rows if _keep_entry(r)]
    print(f"\n  Filtered: {before} → {len(rows)} (removed {before - len(rows)} non-cancer/empty entries)")

    before = len(rows)
    rows = _dedup(rows)
    print(f"  Deduped: {before} → {len(rows)} (merged {before - len(rows)} duplicates)")

    # Step 5: Write output
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    # Stats
    with_cosmic = sum(1 for r in rows if r["cosmic_id"])
    with_sanger = sum(1 for r in rows if r["sanger_id"])
    lineages = len({r["lineage"] for r in rows if r["lineage"]})

    print(f"\n✓ Built {len(rows)} cell line mappings")
    print(f"  COSMIC coverage: {with_cosmic}/{len(rows)} ({with_cosmic*100//len(rows)}%)")
    print(f"  Sanger coverage: {with_sanger}/{len(rows)} ({with_sanger*100//len(rows)}%)")
    print(f"  Unique lineages: {lineages}")
    print(f"  Output: {OUTPUT}")


if __name__ == "__main__":
    main()
