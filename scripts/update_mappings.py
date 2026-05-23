#!/usr/bin/env python3
"""Update the bundled cell-line mappings from DepMap and GDSC sources.

Downloads the latest Model.csv from DepMap and Cell_Lines_Details from
GDSC, then regenerates ``mappings.csv``.

Usage::

    python scripts/update_mappings.py

Requires internet access to depmap.org and the Sanger FTP server.
"""

import csv
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEPMAP_MODEL_URL = "https://depmap.org/portal/api/download/custom"
GDSC_FTP = "ftp://ftp.sanger.ac.uk/pub4/cancerrxgene/releases/release-8.2/Cell_Lines_Details.xlsx"

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "src" / "cell_id_mapper" / "data" / "mappings.csv"

# ---------------------------------------------------------------------------
# Helper: Download DepMap Model.csv
# ---------------------------------------------------------------------------

def fetch_depmap_models() -> list[dict]:
    """Fetch the latest DepMap Model.csv and return parsed rows."""
    print("[1/2] Fetching DepMap Model.csv ...")
    try:
        import requests
        from io import StringIO

        # First get the signed download URL
        listing_resp = requests.get("https://depmap.org/portal/api/download/files")
        listing_resp.raise_for_status()
        files_csv = listing_resp.text

        # Find the Model.csv URL in the listing
        model_url = None
        for line in files_csv.splitlines():
            if "Model.csv" in line:
                # The format is: filename,url
                parts = line.split(",")
                if len(parts) >= 2:
                    model_url = parts[1].strip('"').strip()
                    break

        if model_url is None:
            print("WARNING: Could not find Model.csv in the DepMap download listing.", file=sys.stderr)
            return []

        resp = requests.get(model_url)
        resp.raise_for_status()
        reader = csv.DictReader(StringIO(resp.text))

        models = []
        for row in reader:
            models.append({
                "depmap_id": row.get("ModelID", ""),
                "cell_line_name": row.get("CellLineName", ""),
                "stripped_name": row.get("StrippedCellLineName", ""),
                "cosmic_id": row.get("COSMICID", ""),
                "sanger_id": row.get("SangerModelID", ""),
                "lineage": row.get("OncotreeLineage", ""),
                "disease": row.get("PrimaryDisease", ""),
            })
        print(f"  → {len(models)} cell lines from DepMap")
        return models

    except ImportError:
        print("WARNING: 'requests' not installed. Skipping DepMap fetch.", file=sys.stderr)
        return []
    except Exception as e:
        print(f"WARNING: Failed to fetch DepMap data: {e}", file=sys.stderr)
        return []


# ---------------------------------------------------------------------------
# Helper: Download GDSC Cell_Lines_Details
# ---------------------------------------------------------------------------

def fetch_gdsc_details() -> dict[str, dict]:
    """Fetch GDSC Cell_Lines_Details and return a COSMIC_ID → details dict."""
    print("[2/2] Fetching GDSC Cell_Lines_Details ...")
    try:
        import requests
        from io import BytesIO
        from zipfile import ZipFile

        # Try the bulk download zip → contains Cell_Lines_Details.xlsx
        # Fallback: try pandas to read the xlsx directly
        pass
    except ImportError:
        pass

    try:
        import pandas as pd

        # Try known URLs
        urls = [
            GDSC_FTP,
            "https://www.cancerrxgene.org/downloads/Cell_Lines_Details.xlsx",
        ]
        for url in urls:
            try:
                df = pd.read_excel(url)
                print(f"  → {len(df)} cell lines from GDSC ({url})")
                result: dict[str, dict] = {}
                for _, row in df.iterrows():
                    cosmic = str(row.get("COSMIC_ID", "")).strip()
                    if cosmic:
                        result[cosmic] = {
                            "gdsc_name": str(row.get("Cell line Name", row.get("Cell Line Name", ""))),
                            "tissue": str(row.get("Tissue", "")),
                        }
                return result
            except Exception:
                continue
    except ImportError:
        print("WARNING: 'pandas' or 'openpyxl' not installed. Skipping GDSC fetch.", file=sys.stderr)
    except Exception as e:
        print(f"WARNING: Failed to fetch GDSC data: {e}", file=sys.stderr)

    return {}


# ---------------------------------------------------------------------------
# Merge & write
# ---------------------------------------------------------------------------

def merge_and_write(depmap_models: list[dict], gdsc_details: dict[str, dict]) -> None:
    """Combine DepMap + GDSC data and write the unified mappings.csv."""
    existing: list[dict] = []
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, newline="", encoding="utf-8") as fh:
            existing = list(csv.DictReader(fh))

    # Build a name-index of existing rows
    existing_by_ach: dict[str, dict] = {r["depmap_id"]: r for r in existing}

    rows: list[dict] = []
    for dm in depmap_models or existing:
        ach = dm.get("depmap_id", "")
        # enrich with GDSC data if available
        cosmic = dm.get("cosmic_id", "")
        gdsc_name = ""
        tissue_extra = ""
        if cosmic and cosmic in gdsc_details:
            gdsc_name = gdsc_details[cosmic].get("gdsc_name", "")
            tissue_extra = gdsc_details[cosmic].get("tissue", "")

        row = {
            "depmap_id": ach,
            "cell_line_name": dm.get("cell_line_name", ""),
            "stripped_name": dm.get("stripped_name", ""),
            "cosmic_id": cosmic,
            "sanger_id": dm.get("sanger_id", ""),
            "lineage": dm.get("lineage", "") or tissue_extra,
            "disease": dm.get("disease", ""),
            "aliases": gdsc_name if gdsc_name and gdsc_name != dm.get("cell_line_name", "") else "",
        }
        rows.append(row)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=[
            "depmap_id", "cell_line_name", "stripped_name",
            "cosmic_id", "sanger_id", "lineage", "disease", "aliases",
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✓ Updated mappings.csv with {len(rows)} cell lines → {OUTPUT_PATH}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("cell-id-mapper: update mappings\n")
    depmap_models = fetch_depmap_models()
    gdsc_details = fetch_gdsc_details()
    merge_and_write(depmap_models, gdsc_details)


if __name__ == "__main__":
    main()
