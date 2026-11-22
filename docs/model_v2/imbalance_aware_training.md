# ADR-X Model v2 — Imbalance-aware training and decision protocol

Status: approved training design; execution is blocked until Phase 1 data audit establishes valid labels, cohort sizes, and group/time structure.

## Objective

Optimize reliable discrimination of both positive and negative classes under class imbalance. Do not optimize raw accuracy alone, do not manufacture labels, and do not claim perfect prediction.

The population-level task and report-level task are evaluated independently. The positive class has a different scientific meaning in each task:
- Population task: curated positive drug–event association versus curated negative-with-evidence pair. Unlabelled pairs are not negatives.
- Report task: serious versus explicitly non-serious outcome among eligible deduplicated FAERS cases. Unknown/conflicting outcomes are excluded from the primary binary endpoint.

## 1. Establish the class distribution first

For every task and every split, report positive and negative counts, prevalence and imbalance ratio, excluded/unknown counts and reasons, unique pair or case counts, and counts by time period and relevant strata.

If the curated population dataset has too few defensible negative-with-evidence examples, stop rather than treating unlabelled pairs as negatives. If the report endpoint has too few examples in either class, reduce model complexity and report uncertainty.

## 2. Training comparisons

For each of the four configurations (population baseline, population extended, report baseline, report extended), compare in a controlled experiment:
1. Unweighted model as a reference.
2. Class-weighted model, with weights calculated from the training partition only.
3. A decision threshold tuned on validation predictions.
4. Optional training-only negative downsampling if the majority class is very large; retain natural prevalence in validation and test.
5. Optional resampling only if justified by feature types and sample size. It must happen inside each training fold after splitting. Never resample validation or test data.

For LightGBM, evaluate scale_pos_weight or class weights as alternatives, not as simultaneous arbitrary multipliers. For mixed categorical/numeric data, do not default to vanilla SMOTE: synthetic examples may be invalid and may distort biological or report-level relationships. If resampling is tested, document the method and compare it against class weighting.

Keep hyperparameter search bounded and use grouped inner validation. Do not select a method based on the final test set.

## 3. Validation and threshold selection

- Preserve grouped splits: canonical drug–event pair for the population task; canonical FAERS case ID for the report task.
- Preserve a chronological holdout where dates support it.
- Keep natural prevalence in validation and test.
- Fit weights, imputers, encoders, feature selectors, resampling, calibration, and threshold selection without using the final test set.
- Choose the decision threshold on validation data according to a prespecified objective. Default objective: maximize balanced accuracy, with sensitivity and specificity both reported.
- Freeze the threshold before evaluating the final test set.

The probability threshold need not be 0.50. A threshold is a decision policy, not a property of the model, and must be reported with its selection method.

## 4. Metrics — never use accuracy alone

Primary metrics: AUPRC (with positive-class prevalence as its no-skill reference), balanced accuracy, positive-class sensitivity, negative-class specificity, Matthews correlation coefficient (MCC), and confusion matrix with raw counts.

Secondary metrics: AUROC, precision/positive predictive value, negative predictive value, macro-F1 and per-class precision/recall/F1, Brier score, and calibration curve.

Report confidence intervals, preferably by bootstrap resampling at the independent group unit (case or drug–event pair), not by treating correlated rows as independent. Show performance across temporal windows where possible.

## 5. Probability calibration

Class weighting and resampling can change the effective class prior and make raw model probabilities poorly calibrated. Evaluate calibration on untouched validation data with natural prevalence. Compare sigmoid/Platt calibration and isotonic calibration only when validation sample size is sufficient. Fit calibration on validation/calibration data only, never on final test outcomes. Evaluate Brier score and calibration curves on final test data.

Calibrated probabilities remain conditional on the selected FAERS/curated dataset. They are not population incidence or individual clinical risk.

## 6. Model selection rule

1. Pass leakage and data-integrity checks.
2. Meet minimum acceptable sensitivity and specificity chosen before final testing.
3. Compare AUPRC and MCC.
4. Compare balanced accuracy and calibration.
5. Prefer the simpler model when differences are within uncertainty.
6. Report all four model configurations even if the extended model performs worse.

A model that performs well on one class but fails on the other is not considered successful. If no model meets prespecified criteria, report that result honestly and revise data/target quality rather than forcing a high score.

## 7. Required experiment report

For every run, persist dataset fingerprint and source versions; target definition and class counts; split identifiers and cut-off dates; random seed and package versions; feature schema and excluded leakage fields; algorithm, hyperparameters, class weights and sampling method; selected threshold and validation objective; calibration method; per-class metrics, confusion matrix, AUPRC, AUROC, MCC, balanced accuracy, Brier score; confidence intervals and limitations.

## 8. Safety and interpretation

These models support research analysis of pharmacovigilance data. They are not diagnostic tools, causal estimators, or validated individual patient-risk calculators. A positive or negative output is a classification under a specific target definition and dataset, not a statement that a drug caused or cannot cause an adverse reaction.