#!/usr/bin/env python3
"""Streaming, read-only first-pass inventory and profiling for ADR-X Model v2."""
from __future__ import annotations
import argparse, csv, json, re, sqlite3, tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SUPPORTED_SUFFIXES = {'.csv', '.tsv', '.txt', '.tab'}
ALIASES = {
 'case_id': {'caseid','case_id','case'}, 'primary_id': {'primaryid','primary_id','report_id'},
 'report_date': {'fda_dt','fda_date','report_date','date'}, 'age': {'age','age_yr','age_years'},
 'sex': {'sex','gender'}, 'drug_name': {'drugname','drug_name','prod_ai','ingredient'},
 'drug_role': {'role_cod','role_code','drug_role','role'},
 'event_term': {'pt','preferred_term','event_term','reaction'},
 'event_code': {'pt_code','meddra_pt_code','event_code'},
 'outcome_code': {'outc_cod','outcome_code','outcome'}, 'label': {'label','target','y'}
}

def normalize_column(value: Any) -> str:
 return re.sub(r'[^a-z0-9]+', '', str(value).strip().lower())

def sniff_delimiter(path: Path) -> str:
 with path.open('r', encoding='utf-8-sig', errors='replace', newline='') as handle:
  sample = handle.read(20000)
 try:
  return csv.Sniffer().sniff(sample, delimiters='\t,$|;').delimiter
 except csv.Error:
  counts = {d: sample.count(d) for d in ('$', '\t', ',', '|', ';')}
  return max(counts, key=counts.get) if max(counts.values(), default=0) else ','

def discover_files(root: Path) -> list[Path]:
 return sorted(p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
               and not any(part.startswith('.') for part in p.parts))

def read_chunks(path: Path, delimiter: str, chunksize: int):
 import pandas as pd
 return pd.read_csv(path, sep=delimiter, dtype='string', encoding='utf-8-sig',
                    encoding_errors='replace', low_memory=False, on_bad_lines='warn', chunksize=chunksize)

def profile_file(path: Path, root: Path, chunksize: int = 100_000) -> dict[str, Any]:
 delimiter = sniff_delimiter(path)
 totals, value_counts = Counter(), {}
 detected, columns = {}, []
 date_min = date_max = None
 date_unparsed = sertraline_matches = 0
 with tempfile.TemporaryDirectory(prefix='adrx_audit_') as tmp:
  with sqlite3.connect(Path(tmp) / 'keys.sqlite') as conn:
   conn.execute('CREATE TABLE case_keys (value TEXT PRIMARY KEY)')
   conn.execute('CREATE TABLE primary_keys (value TEXT PRIMARY KEY)')
   for frame in read_chunks(path, delimiter, chunksize):
    if not columns:
     columns = [str(c) for c in frame.columns]
     normalized = {normalize_column(c): str(c) for c in frame.columns}
     for canonical, aliases in ALIASES.items():
      matches = sorted(set(normalized) & {normalize_column(a) for a in aliases})
      if matches: detected[canonical] = normalized[matches[0]]
    totals['rows'] += len(frame)
    for col in frame.columns: totals[f'missing::{col}'] += int(frame[col].isna().sum())
    for key in ('case_id','primary_id'):
     col = detected.get(key)
     if col and col in frame.columns:
      table = 'case_keys' if key == 'case_id' else 'primary_keys'
      for value in frame[col].dropna().astype(str):
       cur = conn.execute(f'INSERT OR IGNORE INTO {table}(value) VALUES (?)', (value,))
       if cur.rowcount == 0: totals[f'duplicate::{key}'] += 1
    for key in ('sex','drug_role','outcome_code','label'):
     col = detected.get(key)
     if col and col in frame.columns:
      value_counts.setdefault(key, Counter()).update(frame[col].fillna('<MISSING>').astype(str).value_counts().to_dict())
    date_col = detected.get('report_date')
    if date_col and date_col in frame.columns:
     import pandas as pd
     parsed = pd.to_datetime(frame[date_col], errors='coerce', dayfirst=False)
     valid = parsed.dropna()
     if not valid.empty:
      lo, hi = valid.min(), valid.max()
      date_min = lo if date_min is None or lo < date_min else date_min
      date_max = hi if date_max is None or hi > date_max else date_max
     date_unparsed += int(parsed.isna().sum())
    drug_col = detected.get('drug_name')
    if drug_col and drug_col in frame.columns:
     sertraline_matches += int(frame[drug_col].fillna('').str.contains(r'sertraline', case=False, regex=True).sum())
   conn.commit()
 rows = int(totals['rows'])
 missing = {str(col): {'missing_count': int(totals[f'missing::{col}']),
           'missing_fraction': float(totals[f'missing::{col}']/rows) if rows else 0.0} for col in columns}
 dates = {'min': date_min.isoformat(), 'max': date_max.isoformat(), 'unparsed_count': int(date_unparsed)} if date_min is not None else None
 return {'path': str(path.relative_to(root)), 'bytes': path.stat().st_size, 'delimiter': delimiter,
  'rows': rows, 'columns': columns, 'detected_fields': detected, 'missingness': missing,
  'duplicate_key_rows': {'case_id': int(totals['duplicate::case_id']), 'primary_id': int(totals['duplicate::primary_id'])},
  'report_date': dates, 'value_counts_top_100': {k: dict(v.most_common(100)) for k,v in value_counts.items()},
  'sertraline_name_matches': int(sertraline_matches) if 'drug_name' in detected else None,
  'warnings': ['Alias detection is provisional; confirm against the source release data dictionary.',
   'Duplicate counts are repeated key occurrences beyond the first, not all rows in duplicate groups.',
   'FAERS follow-up version resolution and ingredient normalization require separate reviewed rules.']}

def main() -> int:
 parser = argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--data-dir', type=Path, default=Path('data'))
 parser.add_argument('--output', type=Path, default=Path('reports/model_v2/phase1_data_audit.json'))
 parser.add_argument('--chunksize', type=int, default=100_000)
 args = parser.parse_args()
 root = args.data_dir.resolve()
 if not root.is_dir(): parser.error(f'Data directory does not exist or is not a directory: {root}')
 if args.chunksize < 1: parser.error('--chunksize must be a positive integer')
 files = discover_files(root)
 report = {'audit_name':'ADR-X Model v2 Phase 1 data inventory', 'generated_at_utc':datetime.now(timezone.utc).isoformat(),
  'data_root':str(root), 'read_only':True, 'chunksize':args.chunksize, 'files_discovered':len(files),
  'files':[], 'errors':[], 'limitations':['No source data are modified, labels generated, or records deduplicated.',
  'Compressed archives must be extracted before table profiling.',
  'This first-pass audit does not establish source validity or label independence.']}
 for path in files:
  try: report['files'].append(profile_file(path, root, args.chunksize))
  except Exception as exc: report['errors'].append({'path':str(path.relative_to(root)), 'error_type':type(exc).__name__, 'message':str(exc)})
 output = args.output.resolve()
 output.parent.mkdir(parents=True, exist_ok=True)
 output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
 print(f"Audited {len(files)} file(s); errors: {len(report['errors'])}")
 print(f'Report: {output}')
 return 1 if report['errors'] else 0

if __name__ == '__main__': raise SystemExit(main())