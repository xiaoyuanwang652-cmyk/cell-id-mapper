"""Command-line interface for quick cell line ID lookups."""

import argparse
import json
import sys

from .mapper import load_mapper


def _format_cell_line(cl, fmt: str) -> str:
    """Format a CellLine for output."""
    if fmt == "json":
        return json.dumps(cl.to_dict(), indent=2)
    if fmt == "tsv":
        return f"{cl.depmap_id}\t{cl.cell_line_name}\t{cl.cosmic_id}\t{cl.sanger_id}\t{cl.lineage}\t{cl.disease}"
    # default: human-readable
    return (
        f"Name:      {cl.cell_line_name}\n"
        f"DepMap:    {cl.depmap_id}\n"
        f"COSMIC:    {cl.cosmic_id or 'N/A'}\n"
        f"Sanger:    {cl.sanger_id or 'N/A'}\n"
        f"Lineage:   {cl.lineage}\n"
        f"Disease:   {cl.disease}\n"
        f"Aliases:   {cl.aliases or 'N/A'}"
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="cell-id-mapper",
        description="Cross-reference cell-line IDs across DepMap, GDSC (COSMIC), and Sanger.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # lookup
    p = sub.add_parser("lookup", help="Exact lookup by name or ID")
    p.add_argument("query", help="Cell-line name, ACH ID, COSMIC ID, or Sanger ID")
    p.add_argument("--format", "-f", choices=["text", "json", "tsv"], default="text")

    # search
    p = sub.add_parser("search", help="Fuzzy search by name or partial ID")
    p.add_argument("query", help="Partial name or ID substring")
    p.add_argument("--limit", "-n", type=int, default=10)
    p.add_argument("--format", "-f", choices=["text", "json", "tsv"], default="text")

    # list-by-lineage
    p = sub.add_parser("lineage", help="List cell lines by lineage")
    p.add_argument("lineage", help="Lineage name (e.g. Lung, Breast, Blood)")
    p.add_argument("--format", "-f", choices=["text", "json", "tsv"], default="text")

    # convert
    p = sub.add_parser("convert", help="Convert between two ID types")
    p.add_argument("id_value", help="The identifier value")
    p.add_argument(
        "--from", "-s", dest="source", required=True,
        choices=["ach", "name", "cosmic", "sanger"],
        help="Source ID type",
    )
    p.add_argument(
        "--to", "-t", dest="target", required=True,
        choices=["ach", "name", "cosmic", "sanger"],
        help="Target ID type",
    )

    # stats
    sub.add_parser("stats", help="Show mapping coverage statistics")

    args = parser.parse_args(argv)
    mapper = load_mapper()

    if args.command == "lookup":
        cl = (
            mapper.from_name(args.query)
            or mapper.from_ach(args.query)
            or mapper.from_cosmic(args.query)
            or mapper.from_sanger(args.query)
        )
        if cl is None:
            print(f"No match for '{args.query}'", file=sys.stderr)
            sys.exit(1)
        print(_format_cell_line(cl, args.format))

    elif args.command == "search":
        results = mapper.search(args.query, limit=args.limit)
        if not results:
            print(f"No matches for '{args.query}'", file=sys.stderr)
            sys.exit(1)
        if args.format == "json":
            print(json.dumps([cl.to_dict() for cl in results], indent=2))
        elif args.format == "tsv":
            for cl in results:
                print(_format_cell_line(cl, "tsv"))
        else:
            for i, cl in enumerate(results, 1):
                print(f"[{i:2d}] {cl.cell_line_name:28s} {cl.depmap_id}  "
                      f"COSMIC={cl.cosmic_id or '?':10s} Sanger={cl.sanger_id or '?':14s} "
                      f"{cl.lineage} / {cl.disease}"
                )

    elif args.command == "lineage":
        results = mapper.by_lineage(args.lineage)
        if not results:
            print(f"No cell lines for lineage '{args.lineage}'", file=sys.stderr)
            sys.exit(1)
        if args.format == "json":
            print(json.dumps([cl.to_dict() for cl in results], indent=2))
        elif args.format == "tsv":
            for cl in results:
                print(_format_cell_line(cl, "tsv"))
        else:
            for cl in results:
                print(f"{cl.cell_line_name:28s}  {cl.depmap_id}  {cl.disease}")

    elif args.command == "convert":
        method_map = {
            ("ach", "name"): mapper.ach_to_name,
            ("ach", "cosmic"): mapper.ach_to_cosmic,
            ("ach", "sanger"): mapper.ach_to_sanger,
            ("name", "ach"): mapper.name_to_ach,
            ("name", "cosmic"): mapper.name_to_cosmic,
            ("name", "sanger"): mapper.name_to_sanger,
            ("cosmic", "ach"): mapper.cosmic_to_ach,
            ("cosmic", "name"): mapper.cosmic_to_name,
            ("sanger", "ach"): mapper.sanger_to_ach,
            ("sanger", "name"): mapper.sanger_to_name,
        }
        fn = method_map.get((args.source, args.target))
        if fn is None:
            print(f"Unsupported conversion: {args.source} → {args.target}", file=sys.stderr)
            sys.exit(1)
        result = fn(args.id_value)
        if result is None:
            print(f"No mapping found for {args.source}='{args.id_value}'", file=sys.stderr)
            sys.exit(1)
        print(result)

    elif args.command == "stats":
        total = len(mapper)
        with_cosmic = sum(1 for cl in mapper.all() if cl.cosmic_id)
        with_sanger = sum(1 for cl in mapper.all() if cl.sanger_id)
        lineages = {cl.lineage for cl in mapper.all()}
        print(f"Total cell lines:    {total}")
        print(f"With COSMIC ID:      {with_cosmic}  ({with_cosmic * 100 // total}%)")
        print(f"With Sanger ID:      {with_sanger}  ({with_sanger * 100 // total}%)")
        print(f"Unique lineages:     {len(lineages)}")
        print(f"Lineages:            {', '.join(sorted(lineages))}")


if __name__ == "__main__":
    main()
