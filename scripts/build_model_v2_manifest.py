#!/usr/bin/env python3
"""Build a SHA-256 inventory for locally held ADR-X Model v2 source files."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

INCLUDED_SUFFIXES = {'.csv', '.tsv', '.txt', '.tab', '.zip', '.gz', '.xml', '.json', '.xlsx'}
EXCLUDED_PARTS = {'.git', '__pycache__', '.venv', 'venv'}


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b''):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(root: Path) -> list[dict]:
    records = []
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in INCLUDED_SUFFIXES:
            continue
        if any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        records.append({
            'source_id': path.stem,
            'local_relative_path': path.relative_to(root).as_posix(),
            'sha256': sha256_file(path),
            'byte_size': path.stat().st_size,
            'file_type': path.suffix.lower().lstrip('.'),
            'source_url': None,
            'source_release_or_quarter': None,
            'retrieved_at_utc': None,
            'license_or_terms': 'REVIEW_REQUIRED',
            'data_stage': 'raw_or_existing_unclassified',
            'source_notes': 'Complete provenance fields manually before dataset construction.'
        })
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path('data'))
    parser.add_argument('--output', type=Path, default=Path('reports/model_v2/source_manifest.json'))
    args = parser.parse_args()
    root = args.data_dir.resolve()
    if not root.is_dir():
        parser.error(f'Data directory does not exist: {root}')
    report = {
        'manifest_version': '1.0',
        'project': 'ADR-X Model v2',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'data_root': str(root),
        'files': inventory(root),
        'notes': [
            'SHA-256 and byte sizes are computed from local file bytes.',
            'Source URL, release, retrieval date, license and data stage require human verification.',
            'Do not commit raw or restricted data to GitHub.'
        ]
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\\n', encoding='utf-8')
    print(f"Manifest contains {len(report['files'])} file(s): {output}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())