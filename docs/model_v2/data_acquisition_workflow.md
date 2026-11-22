# ADR-X Model v2 — Data acquisition and audit workflow

Status: workflow specification. No bulk data have been downloaded or added to GitHub by this change.

## Goals

Acquire and audit both (A) population-level curated drug–event evidence and (B) report-level FAERS records. Keep source datasets, target construction, and resulting cohorts separate. The workflow supports data already on the user's Windows computer, data tracked in GitHub, and new public source downloads.

## Repository and local storage policy

- Keep large raw archives and extracted FAERS tables on the user's local machine or an access-controlled data volume. Do not commit raw FAERS data, derived person/case-level data, API keys, or licensed/restricted downloads to GitHub.
- Commit only code, schemas, source manifests, data dictionaries, and appropriately de-identified aggregate audit reports.
- Record SHA-256, byte size, source URL, release/quarter, retrieval date (UTC), license/terms, and processing steps for each source file.
- Keep immutable raw files separate from extracted, normalized, curated, and model-ready outputs.

Recommended local layout:

```text
data/model_v2/
  raw/
    faers/quarterly/
    sider/
    dailymed/
    pharmgkb/
    drugbank/
    string/
    smpdb/
  incoming/local_existing/
  extracted/
  interim/
  curated/
  processed/
reports/model_v2/
  phase1_data_audit.json
  source_manifest.json
  exclusions.csv
```

## Source plan

### 1. FAERS / AEMS quarterly ASCII extracts — report-level task

Primary source: https://fis.fda.gov/extensions/FPD-QDE-FAERS/FPD-QDE-FAERS.html

FDA's quarterly extracts are not cumulative. Download every quarter in the selected study window, not just the latest quarter. Prefer ASCII ZIP extracts for this pipeline. Extract the archive and retain its README/field notes. The usual tables include DEMO, DRUG, REAC, OUTC, INDI, THER and RPSR; verify the exact contents and field definitions in each release.

Start with the complete period already represented in the existing research data, then extend backward/forward only after checking data continuity and schema changes. For temporal validation, preserve quarter/report dates. Do not concatenate quarterly tables without tracking source quarter and case/version identifiers.

Official documentation: https://www.fda.gov/drugs/fda-adverse-event-monitoring-system-aems/faers-quarterly-data-files-documentation

openFDA drug event API (https://open.fda.gov/apis/drug/event/) is useful for targeted exploration and cross-checking, but it is derived from FAERS and must not be treated as an independent validation source. API coverage and refresh timing may lag quarterly extracts. Do not combine API rows with quarterly extracts without deduplication and provenance.

### 2. SIDER 4.1 — population evidence candidate

Resource: https://sideeffects.embl.de/ ; processing/reference repository: https://github.com/dhimmel/SIDER4

SIDER contains side effects extracted from drug labels. It is useful as curated association evidence, but its absence of a drug–event pair does not establish a true negative. Verify the download's version, license, DrugBank identifier mapping, and MedDRA term mapping before use. The SIDER 4.1 processed data repository reports CC BY-NC-SA 4.0 for its derivatives; review the exact terms for the specific artifact downloaded.

### 3. DailyMed — label evidence and curation

Resource: https://dailymed.nlm.nih.gov/dailymed/ and bulk resources: https://dailymed.nlm.nih.gov/dailymed/spl-resources-all-drug-labels.cfm

Use sertraline-specific current/in-use labels and preserve SPL set ID, version, effective date, manufacturer/product, and section provenance. Extract adverse reactions only as label evidence; do not infer a negative label from an absent term. Full bulk label archives are multi-gigabyte; prefer targeted sertraline label retrieval for Phase 1 rather than downloading every product label.

### 4. PharmGKB — extended pharmacogenomic evidence

Resource: https://www.pharmgkb.org/downloads

Use only annotations relevant to sertraline and relevant genes, preserving evidence level, annotation ID, source publication, version and download date. Treat annotations as biological evidence, not measured genotype/expression for individual FAERS cases.

### 5. DrugBank, STRING and SMPDB — mechanistic features

Use only sources whose access terms permit the intended research use. Record identifiers, versions, organism, confidence thresholds and mapping logic. Do not assume DrugBank access is unrestricted. STRING network features and SMPDB pathway membership are evidence layers, not patient-level observations.

## Acquisition sequence

1. Clone or update the approved branch on Windows.
2. Copy existing local source files into data/model_v2/incoming/local_existing/ without overwriting originals.
3. Inventory Git-tracked datasets from the repository checkout and record their Git path, commit/ref and SHA-256.
4. Download selected FAERS/AEMS ASCII quarterly ZIP files from the official FDA page. Record each quarter and retrieval date. Extract each quarter to its own directory.
5. Obtain SIDER 4.1 files and targeted sertraline DailyMed labels. Obtain PharmGKB/DrugBank/STRING/SMPDB evidence only where terms and access permit.
6. Generate a source manifest with file hashes, versions, URLs, license/terms and source dates.
7. Run the read-only audit utility on the combined local data root. Do not build targets or train yet.
8. Review the report and field mappings manually against the source release documentation.
9. Approve deduplication rules, target eligibility, curated positive/negative evidence rules, and temporal cut-offs before constructing any model-ready table.

## Windows PowerShell starter commands

Run from a working directory with Git and Python installed:

```powershell
git clone --branch model-v2-rebuild https://github.com/adarshdubey804/ADR-X-Sertraline-Signal-Explorer.git
cd ADR-X-Sertraline-Signal-Explorer
git pull origin model-v2-rebuild

New-Item -ItemType Directory -Force data/model_v2/incoming/local_existing | Out-Null
New-Item -ItemType Directory -Force data/model_v2/raw/faers/quarterly | Out-Null
New-Item -ItemType Directory -Force data/model_v2/raw/sider | Out-Null
New-Item -ItemType Directory -Force data/model_v2/raw/dailymed | Out-Null

# Copy your existing local CSV/TSV files into incoming/local_existing.
# Do not move or overwrite the originals.

python scripts/audit_model_v2_data.py --data-dir data --output reports/model_v2/phase1_data_audit.json
```

Download quarterly FAERS/AEMS ASCII ZIPs manually from the official FDA page into data/model_v2/raw/faers/quarterly/. Extract each ZIP into a quarter-specific subfolder, for example 2025Q4/. Do not rename internal source tables unless the original name is preserved in the manifest.

## Required source manifest fields

Each file record must include: source_id, source_name, source_url, source_release_or_quarter, retrieved_at_utc, local_relative_path, sha256, byte_size, license_or_terms, table_name, date_coverage, source_notes, and whether the file is raw, extracted, normalized, curated, or derived.

## Label integrity rules

- SIDER/DailyMed presence can support a curated positive association after manual terminology and ingredient review.
- Absence from SIDER or a product label is not a negative label.
- A negative population label requires an explicit, documented review rule and evidence supporting the negative-with-evidence designation.
- Keep conflicting and unknown evidence as unknown; do not coerce it to zero.
- FAERS outcome target is serious versus explicitly non-serious. Missing or conflicting outcome information remains excluded/unknown.
- The OUTC-derived serious target and any transformations of it must never enter report-level model predictors.
- Population label evidence and any FAERS-derived predictors must have their dependence documented. If labels are based on FAERS, do not call the resulting test set independent of FAERS.

## Phase 1 exit criteria

Phase 1 is complete only when the audit report has actual row/column counts, source release metadata, case/version and primary-ID diagnostics, sertraline drug-role counts, event/outcome distributions, missingness, date coverage, and a documented curated label manifest. The data owner must approve mappings and exclusions. No model training is permitted before these checks pass.

## Scientific caveat

FAERS is a spontaneous-reporting system subject to under-reporting, stimulated reporting, duplicate/follow-up reports, confounding and missing denominators. These data support signal and reported-outcome analyses, not incidence estimates, causal conclusions, or validated individual risk prediction.