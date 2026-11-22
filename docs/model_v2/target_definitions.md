# ADR-X Model v2 — Target Definitions

Version: 2.0-draft  
Status: approved research design; operational field mapping pending Phase 1 data audit.

## A. Population-level curated drug–event signal classification

### Estimand and unit

Classify a canonical sertraline–event pair for a defined observation/evidence period using independently curated reference evidence. The unit is the pair-period, not an individual patient or FAERS report.

### Primary target

- Positive (1): the pair meets the prespecified independent curated-evidence inclusion criteria.
- Negative (0): the pair has been explicitly reviewed and meets prespecified criteria for a negative-with-evidence designation.
- Unknown: insufficient evidence, conflicting evidence, or not reviewed. Unknown pairs are excluded from primary binary training.

A missing association in a database is not a negative label. A curated positive association is not proof that sertraline caused the event.

### Evidence manifest

Each label must include:

- canonical drug identifier and ingredient name;
- event identifier and terminology/version;
- label and evidence class;
- source/version and stable citation or record identifier;
- publication/retrieval date;
- observation/evidence window;
- curator rule and rationale;
- confidence/evidence grade;
- whether FAERS-derived information contributed to the label.

The primary evaluation set should prioritize reference evidence independent of the model's FAERS predictors. If a reference source incorporates FAERS, disclose this dependency and do not describe the evaluation as fully independent.

### Secondary weak-label experiment

A statistical pharmacovigilance rule may be evaluated as a separate weak-label experiment. It must not be conflated with the curated primary task. If its label uses report counts, expected counts, PRR, ROR, EBGM, IC, or related statistics, those quantities and transformations must be excluded from the predictors. Report the task as learning to reproduce a signal definition, not independent biological truth.

## B. Report-level serious reported outcome classification

### Estimand and unit

Estimate the probability that an eligible deduplicated FAERS case involving sertraline has a serious outcome recorded in the FAERS outcome fields. The unit is one canonical case after applying a documented follow-up-version rule.

### Eligibility

- Sertraline must be identified through a versioned ingredient normalization map.
- The primary analysis must predefine qualifying drug roles. Recommended primary cohort: primary suspect and secondary suspect; concomitant-only reports are excluded from the primary cohort and may be explored separately.
- The case must have sufficient identifiers for deduplication and partition grouping.
- The report must have an interpretable outcome classification.

### Primary binary target

- Serious (1): at least one qualifying serious outcome code is present under the selected FAERS release's documented OUTC mapping.
- Explicitly non-serious (0): the source record supports a non-serious classification under the prespecified data semantics.
- Excluded/unknown: no usable outcome evidence, conflicting source rows that cannot be resolved, or ambiguous outcome mapping.

Do not label a report non-serious merely because no serious code was found unless the source release's data semantics establish that absence as an explicit non-serious classification. Retain unknowns as unknown and report their counts.

### Interpretation

The target describes an outcome recorded in a spontaneous report. It does not establish causality, population incidence, treatment risk, or a clinical prognosis for a person.

## Feature exclusion lists

For the population task, exclude all fields used to construct curated labels and any direct derivatives. For the weak-label experiment, exclude all statistical signal-rule components and their mathematical equivalents.

For the report task, exclude the OUTC fields and all derived seriousness indicators from predictors. Also exclude post-outcome or post-report variables unavailable at the intended prediction time. Report identifiers, case identifiers, source filenames, and row-order artifacts are not predictors.

## Validation grouping

- Population task: group by canonical drug–event pair; temporal split by evidence/observation cut-off.
- Report task: group by canonical FAERS case identifier; temporal split by report date.
- Keep all follow-up versions of a case in one partition.
- Fit every learned preprocessing step on training data only.

## Required reporting

Every result must name the task, unit, target definition, eligibility criteria, source releases, data cut-off, split strategy, class counts, exclusions, metrics, confidence intervals, and limitations. No single metric should be presented without this context.
