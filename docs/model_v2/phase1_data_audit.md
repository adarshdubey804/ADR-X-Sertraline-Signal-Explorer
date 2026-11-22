# ADR-X Model v2 — Phase 1 Data Audit

Status: audit protocol committed; source-data audit pending execution against the actual source files.

## Scope

Phase 1 establishes whether the repository's available data can support two distinct tasks:

1. Population-level sertraline–event signal classification using independently curated reference labels.
2. Report-level serious-outcome classification among eligible, deduplicated FAERS reports involving sertraline.

No model is trained in Phase 1. No labels or clinical measurements are synthesized.

## Current evidence and unresolved items

The earlier repository review confirmed the presence of training and validation dataset references, a LightGBM training script, a validation-dataset builder, feature-building code, and a small omics summary file. The complete large dataset CSV could not be retrieved through the GitHub file inspection interface. Consequently, its schema, actual row count, duplicate-case structure, outcome coverage, target prevalence, missingness, and date range remain unverified.

The existing training script constructs a binary label from `a_count / total_count > 0.05`, while the validation builder uses a `label` column. These are not accepted as the v2 targets. Their equivalence has not been established.

The existing training script also generates random dose and polypharmacy values when columns are absent, and derives biological proxy features from molecular descriptors. Those practices are not acceptable for v2 evidence-bearing features.

## Required source files

### FAERS core tables

| Table | Required fields (actual source aliases must be mapped) | Use |
|---|---|---|
| DEMO | CASEID, PRIMARYID, FDA_DT, age, sex | Case versioning, time, demographics |
| DRUG | CASEID, PRIMARYID, DRUGNAME, ROLE_COD | Sertraline identification and drug role |
| REAC | CASEID, PRIMARYID, PT | Reported event terms |
| OUTC | CASEID, PRIMARYID, OUTC_COD | Reported outcome |
| THER | CASEID, PRIMARYID, start/end dates | Optional exposure timing |
| INDI | CASEID, PRIMARYID, indication | Context and sensitivity analyses |

FAERS releases and file formats differ. The audit must record the source release, quarter, source filename, delimiter, encoding, and field mapping. Do not assume every table has every identifier or field.

### Curated population-level reference labels

Required fields:

- Canonical active ingredient or drug identifier.
- Standardized event identifier (preferably MedDRA PT code and version).
- Binary reference label or evidence class.
- Source name, source version, evidence URL or persistent identifier.
- Evidence publication/retrieval date and applicable observation period.
- Inclusion/exclusion rationale and curator decision.
- Independent evidence provenance sufficient to distinguish a curated association from a label derived from the same FAERS counts used as predictors.

A curated association is an evidence-backed reference label, not proof of causality. Unlabelled pairs are not automatically negatives. The dataset must explicitly distinguish positive, negative-with-evidence, and unknown/unlabelled pairs. Primary binary training must use only defensibly labelled positive and negative examples.

### Extended biological evidence

- DrugBank: verified sertraline identifier and licensed/authorized structure record where applicable.
- RDKit: reproducible descriptors computed from the verified structure and recorded RDKit version.
- STRING: species, protein identifiers, confidence threshold, release/version, and interaction provenance.
- SMPDB: pathway identifiers, version, and drug/target mapping evidence.
- PharmGKB: gene–drug annotation identifiers, evidence level, source version and phenotype/genotype scope.

The source files must document whether a feature is drug-level, pathway-level, population-level, or genuinely report-/patient-level. Drug-level constants cannot be treated as individual genotype or expression measurements.

## Target specifications

### Population-level task

Unit: one canonical sertraline–event pair per defined evidence/observation period.

Primary label: curated positive versus curated negative-with-evidence. Unknown/unlabelled pairs are excluded from primary binary training and retained in audit counts.

Do not use `a_count`, `total_count`, PRR, ROR, EBGM, IC, or any mathematically equivalent target-construction quantity as a predictor when those quantities define the label. If a statistical signal-rule experiment is added, it must have a separate target namespace, separate experiment report, and leakage exclusion list.

### Report-level task

Unit: one eligible deduplicated FAERS case/report with sertraline exposure meeting the prespecified drug-role eligibility rule.

Primary label: serious reported outcome = 1; explicitly non-serious reported outcome = 0. Seriousness is mapped from the official FAERS OUTC codes under a versioned mapping. Reports with missing, conflicting, or insufficient outcome evidence are excluded from the primary binary target and counted separately.

FAERS reports are spontaneous reports. This endpoint estimates reported seriousness conditional on inclusion in the reporting database; it is not incidence, causal attribution, or an individual's clinical risk.

## Deduplication and eligibility

- Deduplicate follow-up versions using the official case identifier and a documented latest-version rule.
- Preserve source rows and identifiers in an audit trail; never silently discard records.
- Use report identifiers and case identifiers consistently. A case and its follow-up versions must remain in one partition.
- Normalize drug names to active ingredients using a versioned mapping table.
- Record the role-code policy. The primary analysis should predefine whether only primary/secondary suspect roles qualify; concomitant-only reports should not be silently mixed into the exposed cohort.
- Normalize event terms to MedDRA PT codes and record the MedDRA version.
- Do not infer non-serious status from absence of a serious outcome code unless the source release and outcome semantics support that rule.

## Leakage and split audit

- Group report-level splits by canonical case identifier.
- Group population-level splits by canonical drug–event pair.
- Build chronological holdouts using dates available at the prediction cut-off.
- Fit imputation, encoding, feature selection, scaling, and calibration only on training partitions.
- Exclude target-defining evidence fields and their mathematical equivalents from predictors.
- Check for duplicated cases, event pairs, source records, and follow-up versions across partitions.
- If curated labels were published after the simulated prediction cut-off, do not use them as historical predictors or pretend they were available earlier.

## Phase 1 deliverables

1. Machine-readable audit report with source inventory, schemas, row counts, missingness, duplicate counts, date ranges, sertraline counts, and outcome distributions.
2. Versioned field-mapping and drug-normalization specifications.
3. Curated reference-label manifest with evidence provenance.
4. Data dictionary and exclusions log.
5. A signed-off decision on whether each target has enough valid positives and negatives to proceed.

## Stop conditions

Do not proceed to model training if any of the following remain unresolved:

- No defensible negative class for the curated population task.
- No stable case identifier or defensible follow-up deduplication rule for report-level evaluation.
- Serious/non-serious outcome mapping is ambiguous for the selected FAERS release.
- Dataset partitions cannot prevent case/pair leakage.
- Source provenance or date cut-offs are unavailable.
- Required predictors are synthetic, target-derived, or only available after the prediction cut-off.

## How to run the audit

Install the repository requirements, then run:

```bash
python scripts/audit_model_v2_data.py --data-dir data --output reports/model_v2/phase1_data_audit.json
```

For an alternate source directory:

```bash
python scripts/audit_model_v2_data.py --data-dir /path/to/faers-and-reference-data --output reports/model_v2/phase1_data_audit.json
```

The script is a first-pass inventory and profiling tool. Its detected aliases are provisional and must be reviewed against the source release documentation before target construction.
