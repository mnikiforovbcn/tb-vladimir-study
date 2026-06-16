# Descriptive Study Plan: TB Preventive Treatment Cascade in Contacts, Homeless Persons, and People Living with HIV — Vladimir, Kovrov, and Murom (Vladimir Oblast, Russian Federation)

## 1. Background and rationale

Vladimir Oblast operates a programmatic intervention to prevent active tuberculosis (TB), including drug-resistant TB, among three high-risk groups: household/close contacts of TB index cases, homeless persons, and people living with HIV (PLHIV). Individuals in these groups are screened for TB, evaluated for latent TB infection (LTI), and where indicated offered preventive treatment, with adherence supported by incentive payments. The `VladKovMur_dataset.csv` file (7,732 individual records, 62 variables) pools registry data from three sites — Vladimir (n=6,318), Kovrov (n=1,034), and Murom (n=380) — covering screening dates from June 2018 through June 2026.

A descriptive study of this dataset would characterize the population reached by the program, quantify each step of the screening-to-treatment-completion cascade, and identify where the cascade leaks (i.e., where eligible individuals do not progress to the next step). This is exploratory and hypothesis-generating: it does not test a causal hypothesis, but it produces the foundational tables and figures that justify and inform any subsequent analytic study (e.g., predictors of non-completion, comparative effectiveness of bedaquiline- vs. moxifloxacin-containing regimens).

## 2. Objectives

**Primary objective:** Describe the demographic composition, TB/LTI screening and diagnostic cascade, preventive treatment uptake, and treatment outcomes among individuals enrolled in the Vladimir Oblast TB prevention program between 2018 and 2026.

**Specific objectives:**

1. Characterize the study population by site, target group (contact / homeless / PLHIV / other), sex, and age.
2. Quantify the screening and diagnostic cascade: screened → suspected TB → fully evaluated → confirmed active TB vs. LTI vs. neither.
3. Quantify the LTI preventive treatment cascade: eligible → recommended → prescribed → initiated → completed/finished, with attrition at each step.
4. Describe regimen composition (bedaquiline-containing vs. moxifloxacin-containing) among those treated.
5. Describe adherence (doses taken vs. scheduled, 50%/100% dose thresholds) and final outcomes (TB developed / did not develop / unknown / other).
6. Describe uptake of incentive/support payments and their timing relative to treatment milestones.
7. Compare the above across the three sites and over calendar time (enrollment year/quarter).
8. Identify the extent and pattern of missing data and right-censoring (records without a recorded final outcome), since the data extend close to the present date.

## 3. Study design

Retrospective, descriptive, cross-sectional/cohort analysis of existing programmatic surveillance data. No new data collection, no comparison group, no hypothesis testing beyond simple descriptive comparison (proportions, rates, and confidence intervals where appropriate). The unit of analysis is the individual record (one row per enrolled person).

## 4. Data source and study population

- **Source:** `Data/raw/VladKovMur_dataset.csv`, deduplicated by `Source` + `Nomer` (site + registration number).
- **Inclusion:** All individuals with a record in the dataset, regardless of target group or outcome status.
- **Population strata of interest:** `TargetGroup` (1 = contact, 2 = homeless, 3 = PLHIV, 4 = other) and `TreatGroup` (1 = TB treatment, 2 = LTI treatment, 3 = observation only).
- **Linkage:** `IndexCase` allows grouping contacts under the same source TB case for household-cluster descriptive analysis (e.g., number of contacts screened per index case).

## 5. Key variables and operational definitions

| Domain | Variables | Notes |
|---|---|---|
| Identification | `Source_id`, `Source`, `Nomer`, `IndexCase` | Site and registration linkage |
| Demographics | `BirthDate`, `Sex` | Age computed as screening date minus `BirthDate`; group into standard 10-year bands |
| Risk group | `TargetGroup`, `Contact`, `Homeless`, `PLHIV`, `Others`, `RelationWithSource` | `RelationWithSource` coded for contacts only (neighbor, relative/cohabitant, healthcare worker, other) |
| Treatment group | `TreatGroup`, `TreatGroup_01/02/03` | Cross-check one-hot flags sum to 1 and match `TreatGroup` |
| Screening | `Screening`, `DateScreening`, `SuspectedTB`, `DiaskintestPositive` | Baseline screening event |
| Follow-up screening | `Screening_y`/`DateScreening_y`, `NoTbAfter_y_xray`, `NoTbAfter_y`, `Screening_24`, `NoTbAfter_24` | 1-year and 24-month re-screening |
| Diagnosis | `CompleteExaminationTB`/`DateCompleteExaminationTB`, `ConfirmedDiagnosisTB`, `LTI`, `NoTBNoLTI`, `NoTBLTIunknown` | Defines the three diagnostic branches |
| Preventive treatment initiation | `PrevTreatmentRec`, `PrevTreatmentPresc`, `PrevTreatmentStart`/`DatePrevTreatmentStart`, `DateTreatmentScheme` | Sequential cascade steps |
| Regimen | `RegBq` (bedaquiline-containing), `RegMfx` (moxifloxacin-containing) | Not mutually exclusive — check overlap |
| Completion/outcome | `TreatmentCompleted`, `TreatmentFinished`, `DateOutcome`, `TBdeveloped`, `TreatmentStopedMed`, `TreatmetnNotFinished`, `TreatmentContinue`, `OutcomeNotKnown` | Mutually exclusive outcome categories — verify they sum to 1 per treated record |
| Adherence | `DosesTaken`, `SchemaDoses`, `Take50pc`, `Take100pc` | Adherence ratio = `DosesTaken` / `SchemaDoses` |
| Incentives | `DateSuppScreening`/`SuppScreening`, `DateSupp50pc`/`Supp50pc`, `DateSupp100pc`/`Supp100pc`, `DateSupp1yearGr23`/`Supp1yearGr23`, `DateSupp1yearGr1`/`Supp1yearGr1` | Group 1 (TB treatment) and groups 2/3 use different 1-year incentive fields |
| Final outcome | `FinalOutcome` | 1 = no TB, 2 = TB developed, 3 = unknown, 4 = other |

## 6. Data management and quality control (typical first step)

1. **Import and type-check**: parse all `Date*` fields as dates; confirm `int`/`float` fields match the data dictionary; flag out-of-range or non-numeric values.
2. **Duplicate check**: verify `Source` + `Nomer` is unique; investigate any duplicates.
3. **Internal consistency checks**:
   - `TreatGroup_01/02/03` flags sum to exactly 1 and match `TreatGroup`.
   - Outcome flags (`TreatmentCompleted`, `TreatmentFinished`, `TBdeveloped`, `TreatmentStopedMed`, `TreatmetnNotFinished`, `TreatmentContinue`, `OutcomeNotKnown`) are mutually exclusive and exhaustive among treated individuals.
   - Logical date order: `DateScreening` ≤ `DateCompleteExaminationTB` ≤ `DatePrevTreatmentStart` ≤ `DateTreatmentScheme` ≤ `DateOutcome`; flag any reversals.
   - `DosesTaken` ≤ `SchemaDoses` and consistent with `Take50pc`/`Take100pc` thresholds.
   - `ConfirmedDiagnosisTB`, `LTI`, `NoTBNoLTI`, `NoTBLTIunknown` are mutually exclusive.
4. **Missing data audit**: tabulate missingness by variable and by site; missingness is expected to be structural (e.g., outcome fields are blank for those still on observation/treatment or enrolled too recently to have an outcome) — distinguish structural missingness from data-entry gaps.
5. **Age derivation and range check**: compute age at screening from `BirthDate`; flag implausible ages (e.g., negative, >100).
6. **Censoring flag**: create an analysis flag for individuals enrolled within the last 12–24 months relative to the analysis date, since they have not had time to reach a final outcome — handle separately from mature cohorts in cascade and outcome analyses.

## 7. Descriptive analysis plan (typical steps)

### Step 1 — Population profile (Table 1)
Frequencies and percentages of `Source`, `TargetGroup`, `Sex`, age group, and `RelationWithSource` (for contacts), overall and stratified by site. Median/IQR for age and for number of contacts screened per `IndexCase`.

### Step 2 — Screening cascade
For the full cohort and by `TargetGroup`/site: proportion screened (`Screening`), proportion with `SuspectedTB`, proportion `DiaskintestPositive`, proportion completing full evaluation (`CompleteExaminationTB`). Present as a funnel/cascade bar chart with counts and percentages retained at each step.

### Step 3 — Diagnostic outcomes
Among those fully evaluated: proportion with `ConfirmedDiagnosisTB` (active TB), `LTI` (latent infection, no active disease), `NoTBNoLTI`, and `NoTBLTIunknown`. Cross-tabulate diagnostic outcome by `TargetGroup` and site.

### Step 4 — LTI preventive treatment cascade
Among those eligible (`LTI` = 1 or `PrevTreatmentRec` = 1): proportion recommended (`PrevTreatmentRec`) → prescribed (`PrevTreatmentPresc`) → started (`PrevTreatmentStart`). Compute the time interval (days) from `DateCompleteExaminationTB` to `DatePrevTreatmentStart` (treatment initiation delay) — median/IQR, and proportion initiated within programmatic targets (e.g., within 30/60 days).

### Step 5 — Regimen description
Among those started on treatment: proportion on bedaquiline-containing (`RegBq`) vs. moxifloxacin-containing (`RegMfx`) regimens, by site and by year of treatment start (to show regimen evolution over time).

### Step 6 — Adherence and completion
Distribution of `DosesTaken`/`SchemaDoses` ratio; proportion reaching `Take50pc` and `Take100pc`; proportion `TreatmentCompleted` vs. `TreatmentFinished` vs. each non-completion category (`TBdeveloped`, `TreatmentStopedMed`, `TreatmetnNotFinished`, `TreatmentContinue`, `OutcomeNotKnown`). Present as a single stacked bar per site/target group summing to 100% of those started.

### Step 7 — Incentive payment uptake
Proportion receiving each incentive (`SuppScreening`, `Supp50pc`, `Supp100pc`, `Supp1yearGr23`/`Supp1yearGr1`) among those eligible for it, and the median delay between the milestone date and the payment date. Compare uptake by site (programmatic implementation may differ).

### Step 8 — Follow-up and final outcomes
Among those with sufficient follow-up time: proportion re-screened at 1 year (`Screening_y`) and 24 months (`Screening_24`); proportion `NoTbAfter_y`/`NoTbAfter_24`. Distribution of `FinalOutcome` (no TB / TB developed / unknown / other), overall and stratified by whether preventive treatment was completed — descriptive only, not adjusted, since this is not a causal analysis. Where person-time is available (`DateScreening` to `DateOutcome` or to censoring), express `TBdeveloped` as an incidence rate (cases per 100 person-years) for descriptive comparison with published LTBI cohort rates.

### Step 9 — Temporal trends
Enrollment, treatment initiation, and outcome counts by calendar year/quarter (2018–2026) to show program growth and any seasonal or policy-driven shifts (e.g., regimen changes, COVID-19-era disruption in 2020).

### Step 10 — Site comparison
Side-by-side summary table (Vladimir / Kovrov / Murom) of all cascade proportions from Steps 2–8, to identify sites with higher attrition for programmatic follow-up — descriptive flagging only, not formal between-site hypothesis testing.

## 8. Statistical methods

- Categorical variables: counts and percentages, with 95% confidence intervals (Wilson or Clopper-Pearson) for key cascade proportions.
- Continuous variables: median and interquartile range (age, time-to-initiation, adherence ratio), given likely skew; mean/SD reported alongside if approximately normal.
- No formal significance testing is required for a purely descriptive study; if simple comparisons are presented (e.g., site differences), chi-square/Fisher's exact for proportions and Kruskal-Wallis for continuous measures may be used descriptively, clearly labeled as exploratory.
- Software: R (or Python/pandas) with reproducible scripts; all derived variables (age, adherence ratio, time intervals, cascade flags) documented in a data dictionary appendix.

## 9. Data visualization plan

- Cascade/funnel chart for screening → diagnosis → treatment → completion (overall and by target group).
- Stacked bar charts of treatment outcome composition by site and target group.
- Line chart of enrollment and treatment initiation counts by year/quarter.
- Table 1-style summary table of baseline characteristics by site.
- Small multiples comparing the three sites across cascade steps.

## 10. Limitations

- Right-censoring: individuals enrolled near the end of the observation window (data extend to mid-2026) cannot yet show a mature outcome; cascade and outcome proportions should be restricted to or stratified by cohorts with adequate follow-up time.
- Programmatic (non-randomized) data: differences between sites or target groups may reflect implementation or population differences rather than treatment effects — no causal inference is intended.
- Missing `RelationWithSource` and other fields for non-contact target groups is structural, not a data quality defect, and should be reported as such rather than treated as missing-at-random.
- Outcome ascertainment depends on completeness of follow-up screening/reporting at each site, which may vary.

## 11. Ethical and data governance considerations

The dataset contains identifiable linkage keys (`Source_id`, `Nomer`, `IndexCase`) but no direct identifiers (name, address) in the fields reviewed. Analysis should nonetheless follow the data use agreement under which the registry data were obtained, restrict outputs to aggregate counts/percentages, and avoid presenting any stratified cell with very small counts (e.g., <5) that could indirectly identify an individual, particularly for the smaller sites (Murom, n=380).

## 12. Deliverables

1. Cleaned, documented analysis dataset with derived variables (age, age group, adherence ratio, time intervals, cascade-step flags).
2. Descriptive statistics report (tables and figures per Section 9) covering Steps 1–10.
3. A short technical appendix documenting data quality findings (Section 6) and any records excluded or flagged.
