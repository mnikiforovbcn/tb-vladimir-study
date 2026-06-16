This folder contains data about the project of preventive treatment of tuberculosis in Vladimir Oblast of Russian Federation.

## Folder contents

- `Data/raw/VladKovMur_dataset.csv` — the main dataset: 7,732 patient records across 62 fields, combining three regional sources within Vladimir Oblast: Vladimir (6,318 records), Kovrov (1,034), and Murom (380). Records span screenings dated from June 2018 to June 2026.
- `Documentation/DataSet Description.docx` — a Russian-language data dictionary defining every field in the CSV (name, description, allowed values, and data type).
- `Documentation/DataSet Description (English).md` — English translation of the data dictionary above, with corrections (the `Pol`/`Sex` field rename, a fixed description for `SchemaDoses`) and an added entry for `DiaskintestPositive`, which was undocumented in the original.
- `Descriptive Study Plan.md` — a descriptive epidemiological study plan for the dataset: objectives, study design, variable mapping, data quality checks, a step-by-step cascade-of-care analysis (screening → diagnosis → LTI preventive treatment → adherence → outcomes), site/temporal comparisons, and limitations.
- `Analytical Framework Implementation Plan.md` — a software/data engineering plan for building the analysis pipeline that implements the study plan above: technology stack, repository structure, and an 8-phase build sequence (ingestion, schema/QC, derived variables, cascade analytics, visualization, report assembly, automation, validation).
- `src/tb_cascade/`, `tests/`, `notebooks/`, `report/`, `reports/`, `Data/processed/`, `pyproject.toml`, `uv.lock`, `.pre-commit-config.yaml`, `.gitignore`, `README.md` — Phase 0 scaffolding for the analysis pipeline (package skeleton, locked/verified `uv` dependency environment, lint/format hooks); pipeline modules themselves are not yet implemented.
- `.obsidian/` — configuration folder for the Obsidian note-taking app (not project data).

## Dataset description

The dataset tracks individuals identified as contacts of active TB cases, homeless persons, or people living with HIV (PLHIV) who are candidates for preventive treatment of latent tuberculosis infection (LTI), including drug-resistant strains. Each row represents one individual, identified by source registry and registration number (`Source_id`, `Source`, `Nomer`), with a link back to the index TB case (`IndexCase`).

Key groups of fields:

- **Demographics & risk group**: `BirthDate`, `Sex`, `TargetGroup` (contact / homeless / PLHIV / other), `Contact`/`Homeless`/`PLHIV`/`Others` flags, and `RelationWithSource` (relationship to the index TB case, e.g. neighbor, relative, healthcare worker).
- **Treatment group**: `TreatGroup` classifies each person into TB treatment, LTI (preventive) treatment, or observation only, with one-hot flags `TreatGroup_01/02/03`.
- **Screening & diagnosis**: `Screening`/`DateScreening` (initial TB screening), `SuspectedTB`, `DiaskintestPositive`, follow-up screenings at 1 year (`Screening_y`) and 24 months (`Screening_24`), `CompleteExaminationTB`, `ConfirmedDiagnosisTB`, and LTI status (`LTI`, `NoTBNoLTI`, `NoTBLTIunknown`).
- **LTI preventive treatment**: whether treatment was recommended/prescribed/started (`PrevTreatmentRec/Presc/Start` + dates), treatment regimen dates, and whether the regimen included bedaquiline (`RegBq`) or moxifloxacin (`RegMfx`) — both used against drug-resistant TB.
- **Treatment outcomes**: completion status (`TreatmentCompleted` = 100% of doses, `TreatmentFinished` = 85–100%), `TBdeveloped`, treatment stopped/not finished/continuing/unknown outcome flags, doses taken vs. scheduled (`DosesTaken`, `SchemaDoses`, `Take50pc`, `Take100pc`), and `FinalOutcome` (TB did not develop / TB developed / unknown / other).
- **Incentive payments**: dates and receipt flags for support/incentive payments tied to screening, 50%, and 100% treatment completion milestones, and 1-year follow-up (`Supp*` / `DateSupp*` fields), differentiated by treatment group.

Patients are roughly evenly split by sex (3,940 female vs. 3,792 male using the `Sex` coding 1=male, 2=female per the data dictionary — counts here use raw codes). Most individuals (6,004) fall in the "contact" target group, versus 1,042 homeless and 686 PLHIV. The majority (6,382) are in the observation-only treatment group, 1,219 received LTI treatment, and 101 received full TB treatment. Of the 3,499 records with a recorded final outcome, the large majority (3,302) show no TB developed.
