# DataSet Field Descriptions

*English translation of `DataSet Description.docx`.*

| Field name | Description | Values | Type |
|---|---|---|---|
| Source_id | Database code | 1 = Vladimir, 2 = Murom, 3 = Kovrov | int |
| Source | Database | Vladimir, Murom, Kovrov | str |
| Nomer | Registration number | | int |
| IndexCase | Index case | | str |
| BirthDate | Date of birth | | date |
| Sex[^1] | Sex | 1 = male, 2 = female | int |
| TargetGroup | Target group | 1 = Contact, 2 = Homeless, 3 = PLHIV, 4 = Other | int |
| Contact | Contact | 0 = no, 1 = yes | int |
| Homeless | Homeless | 0 = no, 1 = yes | int |
| PLHIV | PLHIV | 0 = no, 1 = yes | int |
| Others | Other | 0 = no, 1 = yes | int |
| TreatGroup | Group | 1 = TB treatment, 2 = LTI treatment, 3 = Observation | int |
| TreatGroup_01 | Group 1 | 0 = no, 1 = yes | int |
| TreatGroup_02 | Group 2 | 0 = no, 1 = yes | int |
| TreatGroup_03 | Group 3 | 0 = no, 1 = yes | int |
| RelationWithSource | Relationship with the TB source case | 45 = Colleague, 313 = Neighbor, 314 = Other, 348 = Relative living in the same apartment/house, 366 = Healthcare worker | int |
| Screening | Underwent TB screening | 0 = no, 1 = yes | int |
| DateScreening | Screening date | | date |
| SuspectedTB | Suspected TB | 0 = no, 1 = yes | int |
| DiaskintestPositive[^3] | Diaskintest result | 0 = negative, 1 = positive | int |
| Screening_y | Screening after one year | 0 = no, 1 = yes | int |
| DateScreening_y | Date of screening after one year | | date |
| NoTbAfter_y_xray | No TB after one year, by X-ray findings | 0 = no, 1 = yes | int |
| NoTbAfter_y | No TB after one year, confirmed by physician | 0 = no, 1 = yes | int |
| Screening_24 | Screening after 24 months | 0 = no, 1 = yes | int |
| NoTbAfter_24 | No TB after 24 months | 0 = no, 1 = yes | int |
| CompleteExaminationTB | Complete TB work-up performed | 0 = no, 1 = yes | int |
| DateCompleteExaminationTB | Date of complete TB work-up | | date |
| ConfirmedDiagnosisTB | Confirmed TB diagnosis | 0 = no, 1 = yes | int |
| LTI | No TB, has LTI (latent TB infection) | 0 = no, 1 = yes | int |
| NoTBNoLTI | No TB, no LTI | 0 = no, 1 = yes | int |
| NoTBLTIunknown | No TB, LTI status unknown | 0 = no, 1 = yes | int |
| PrevTreatmentRec | LTI treatment indicated | 0 = no, 1 = yes | int |
| PrevTreatmentPresc | LTI treatment prescribed | 0 = no, 1 = yes | int |
| PrevTreatmentStart | LTI treatment started | 0 = no, 1 = yes | int |
| DatePrevTreatmentStart | Treatment start date | | date |
| DateTreatmentScheme | Date treatment regimen was assigned | | date |
| RegBq | Regimens containing bedaquiline | 0 = no, 1 = yes | int |
| RegMfx | Regimens containing moxifloxacin | 0 = no, 1 = yes | int |
| TreatmentCompleted | Completed (100% of doses taken) | 0 = no, 1 = yes | int |
| TreatmentFinished | Finished (more than 85% but less than 100% of doses taken) | 0 = no, 1 = yes | int |
| DateOutcome | Treatment end date | | date |
| TBdeveloped | TB developed | 0 = no, 1 = yes | int |
| TreatmentStopedMed | Stopped for medical reasons | 0 = no, 1 = yes | int |
| TreatmetnNotFinished | Not finished | 0 = no, 1 = yes | int |
| TreatmentContinue | Continuing LTI treatment | 0 = no, 1 = yes | int |
| OutcomeNotKnown | Unknown | 0 = no, 1 = yes | int |
| DosesTaken | Number of doses taken | | int |
| SchemaDoses[^2] | Number of doses the patient is scheduled to receive according to the treatment regimen | | int |
| Take50pc | Took 50% of doses | 0 = no, 1 = yes | int |
| Take100pc | Took 100% of doses | 0 = no, 1 = yes | int |
| DateSuppScreening | Date of incentive payment for screening | | date |
| SuppScreening | Received incentive payment for screening | 0 = no, 1 = yes | int |
| DateSupp50pc | Date of incentive payment for 50% | | date |
| Supp50pc | Received incentive payment for 50% | 0 = no, 1 = yes | int |
| DateSupp100pc | Date of incentive payment for 100% | | date |
| Supp100pc | Received incentive payment for 100% | 0 = no, 1 = yes | int |
| DateSupp1yearGr23 | Date of incentive payment for 1 year (groups 2, 3) | | date |
| Supp1yearGr23 | Received incentive payment for 1 year (groups 2, 3) | 0 = no, 1 = yes | int |
| DateSupp1yearGr1 | Date of incentive payment for 1 year (group 1) | | date |
| Supp1yearGr1 | Received incentive payment for 1 year (group 1) | 0 = no, 1 = yes | int |
| FinalOutcome | Outcome | 1 = TB did not develop, 2 = TB developed, 3 = Unknown, 4 = Other | int |

## Translator's notes

- **[^1]: Sex.** The original Russian-language document and the database column were named "Pol" (Russian for "sex"). The column has since been renamed to `Sex` in the dataset; this table reflects that current name.
- **[^2]: SchemaDoses.** Corrected from the original document, which incorrectly listed "0 = no, 1 = yes" as the values for this field. `SchemaDoses` holds the total number of doses the patient is scheduled to receive per the treatment regimen (e.g., 12, 120, 180).
- **[^3]: DiaskintestPositive.** Not documented in the original Russian-language file; description and values added here (1 = Diaskintest positive, 0 = Diaskintest negative).
