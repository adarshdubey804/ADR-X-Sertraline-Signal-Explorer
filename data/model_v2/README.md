# Local ADR-X Model v2 data

This directory is reserved for locally acquired source data and intermediate outputs. Large raw datasets are intentionally not committed to GitHub.

Use the layout in `docs/model_v2/data_acquisition_workflow.md`. Keep raw downloads immutable; store derived data separately. Record SHA-256 checksums, source versions, retrieval dates, licenses/terms, and transformations in `reports/model_v2/source_manifest.json`.

Do not place API keys, credentials, patient-identifying information, restricted downloads, or raw FAERS archives in this repository.