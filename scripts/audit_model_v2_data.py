#!/usr/bin/env python3
"""Read-only first-pass inventory and profiling for ADR-X Model v2 data.

This script does not alter source files, deduplicate records, construct labels,
or train models. It writes a JSON audit report only.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

SUPPORTED_SUFFIXES = {".csv", ".tsv", ".txt", ".tab"}
ALIASES = {
    "case_id": {"caseid", "case_id", "case"},
    "primary_id": {"primaryid", "primary_id", "report_id"},
    "report_date": {"fda_dt", "fda_date", "report_date", "date"},
    "age": {"age", "age_yr", "age_years"},
    "sex": {"sex", "gender"},
    "drug_name": {"drugname", "drug_name", "prod_ai", "ingredient"},
    "drug_role": {"role_cod", "role_code", "drug_role", "role"},
    "event_term": {"pt", "preferred_term", "event_term", "reaction"},
    "event_code": {"pt_code", "meddra_pt_code", "event_code"},
    "outcome_code": {"outc_cod", "outcome_code", "outcome"},
    "label": {"label", "target", "y"},
}


def normalize_column(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def sniff_delimiter(path: Path) -> str:
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:20000]
    try:
        return csv.Sniffer().sniff(sample, delimiters="\t,$|;").delimiter
    except csv.Error:
        # FAERS ASCII extracts commonly use '$'; this fallback is only a guess
        # and is explicitly recorded in the audit output.
        counts = {d: sample.count(d) for d in ("$", "\t", ",", "|", ";")}
        return max(counts, key=counts.get) if max(counts.values(), default=0) else ","


def read_table(path: Path) -> tuple[pd.DataFrame, str]:
    delimiter = sniff_delimiter(path)
    frame = pd.read_csv(
        path,
        sep=delimiter,
        dtype="string",
        encoding="utf-8-sig",
        encoding_errors="replace",
        low_memory=False,
        on_bad_lines="warn",
    )
    return frame, delimiter


def discover_files(root: Path) -> list[Path]:
    return sorted(
        p for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
        and not any(part.startswith(".") for part in p.parts)
    )


def profile_file(path: Path, root: Path) -> dict[str, Any]:
    frame, delimiter = read_table(path)
    normalized = {normalize_column(c): str(c) for c in frame.columns}
    detected = {
        canonical: normalized[next(iter(matches))]
        for canonical, aliases in ALIASES.items()
        if (matches := sorted(set(normalized) & {normalize_column(a) for a in aliases}))
    }
    missingness = {
        str(column): {
            "missing_count": int(frame[column].isna().sum()),
            "missing_fraction": float(frame[column].isna().mean()) if len(frame) else 0.0,
        }
        for column in frame.columns
    }
    duplicate_keys: dict[str, int] = {}
    for key in ("case_id", "primary_id"):
        column = detected.get(key)
        if column:
            duplicate_keys[key] = int(frame[column].duplicated(keep=False).sum())

    date_summary = None
    date_column = detected.get("report_date")
    if date_column:
        parsed = pd.to_datetime(frame[date_column], errors="coerce", dayfirst=False)
        valid = parsed.dropna()
        if not valid.empty:
            date_summary = {"min": valid.min().isoformat(), "max": valid.max().isoformat(),
                            "unparsed_count": int(parsed.isna().sum())}

    value_counts: dict[str, dict[str, int]] = {}
    for key in ("sex", "drug_role", "outcome_code", "label"):
        column = detected.get(key)
        if column:
            counts = frame[column].fillna("<MISSING>").astype(str).value_counts().head(100)
            value_counts[key] = {str(k): int(v) for k, v in counts.items()}

    sertraline_matches = None
    drug_column = detected.get("drug_name")
    if drug_column:
        mask = frame[drug_column].fillna("").str.contains(r"sertraline", case=False, regex=True)
        sertraline_matches = int(mask.sum())

    return {
        "path": str(path.relative_to(root)),
        "bytes": path.stat().st_size,
        "delimiter": delimiter,
        "rows": int(len(frame)),
        "columns": [str(c) for c in frame.columns],
        "detected_fields": detected,
        "missingness": missingness,
        "duplicate_key_rows": duplicate_keys,
        "report_date": date_summary,
        "value_counts_top_100": value_counts,
        "sertraline_name_matches": sertraline_matches,
        "warnings": [
            "Alias detection is provisional; confirm against the source release data dictionary.",
            "Duplicate row counts are not a substitute for FAERS follow-up-version deduplication.",
            "Sertraline text matching is a discovery aid; ingredient normalization requires review.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"),
                        help="Root directory containing source CSV/TSV/TXT files.")
    parser.add_argument("--output", type=Path,
                        default=Path("reports/model_v2/phase1_data_audit.json"),
                        help="Path for the JSON report.")
    args = parser.parse_args()

    root = args.data_dir.resolve()
    output = args.output.resolve()
    if not root.exists() or not root.is_dir():
        parser.error(f"Data directory does not exist or is not a directory: {root}")

    files = discover_files(root)
    report: dict[str, Any] = {
        "audit_name": "ADR-X Model v2 Phase 1 data inventory",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_root": str(root),
        "read_only": True,
        "files_discovered": len(files),
        "files": [],
        "errors": [],
        "limitations": [
            "No source data are modified.",
            "No labels are generated and no records are deduplicated.",
            "This first-pass audit does not establish source validity or label independence.",
            "Compressed archives and Excel workbooks are not parsed by this initial utility.",
        ],
    }

    for path in files:
        try:
            report["files"].append(profile_file(path, root))
        except Exception as exc:  # keep auditing other files
            report["errors"].append({
                "path": str(path.relative_to(root)),
                "error_type": type(exc).__name__,
                "message": str(exc),
            })

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Audited {len(files)} file(s); errors: {len(report['errors'])}")
    print(f"Report: {output}")
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
