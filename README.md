# Who Builds Federal AI? Vendors, Pilots, and the Technical Workforce, 2024–2026

PPOL 5202 Data Visualization, semester project. Guo (Nora) Zhan.

The project describes two sides of the federal government's AI capacity:

- the AI agencies run, from the OMB AI Use Case Inventories: how pilots mature, and whether systems are bought or built;
- the technical staff agencies have to build and run it, from OPM Federal Workforce Data.

## Reproducing

The two final analysis tables are included in `data/processed/`. To reproduce them from the original public files, knit the three notebooks in `code/` in order, from RStudio (Knit button) or from the R console:

``` r
rmarkdown::render("code/01_download_data.Rmd")        # download raw data (~380 MB; skips files already present)
rmarkdown::render("code/02_build_data.Rmd")           # build and merge the files in data/processed/
rmarkdown::render("code/03_build_tableau_data.Rmd")   # reshape ai_use_cases.csv into the three Tableau chart tables
```

`01_download_data.Rmd` fixes the OPM months at January 2024 through July 2026, so a re-run downloads the same months the proposal used. OPM revises recent files, so re-downloaded counts can differ slightly; the manifests saved with the raw files record the versions used.

Paths are resolved with `here::here()`, anchored by the `.here` file in this folder, so the notebooks run from any working directory. R packages: `tidyverse`, `arrow`, `jsonlite`, `here`, `rmarkdown`.

The final proposal and packaged Tableau workbook are included in `proposal/`.

## Folder structure

```
code/
  01_download_data.Rmd          download all raw data from source URLs and APIs
  02_build_data.Rmd             build the two analysis tables and the 2024–2025 join key
  03_build_tableau_data.Rmd     build the three chart tables the Tableau workbook reads
data/
  processed/
    ai_use_cases.csv            one row per AI use case per inventory year (2023, 2024, 2025)
    workforce.csv               OPM counts: headcount, hires, exits by department, occupation, age, tenure, exit type
  keys/
    use_case_link_2024_2025.csv   join key: 2024 use case record_id -> 2025 record_id (match type, similarity)
proposal/
  Who Builds Federal AI.docx    final proposal
  Who Builds Federal AI.pdf     final proposal PDF
  prototypes_tableau_native.twbx  packaged Tableau workbook with its chart data
  tableau_data/                 the three chart tables used in Tableau (from 03_build_tableau_data.Rmd)
Data Access Links GitHub.docx   submission document linking to the two processed datasets
.here                           marks the project root for here::here()
```

The large raw downloads are intentionally not stored in the repository. Running `code/01_download_data.Rmd` recreates `data/raw/` from the official OMB and OPM sources.

## Joins

The OMB and OPM tables are used side by side and are **not merged**. The only join is between the 2024 and 2025 OMB inventories:

| Join | Key | File |
|----|----|----|
| OMB 2024 ↔ OMB 2025 (same use case) | `record_id_2024` ↔ `record_id_2025` (also stored as `link_id` in `ai_use_cases.csv`) | `data/keys/use_case_link_2024_2025.csv` |

## Sources

| Source | URL |
|----|----|
| OPM Federal Workforce Data (EHRI status and dynamics files) | <https://data.opm.gov/get-data/data-downloads> |
| OMB 2025 Federal Agency AI Use Case Inventory | <https://github.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory> |
| OMB 2023 and 2024 Federal AI Use Case Inventories | <https://github.com/ombegov/2024-Federal-AI-Use-Case-Inventory> |

## Manual steps and judgment calls

- No data file is edited by hand. The three Tableau chart tables are written by `03_build_tableau_data.Rmd`, including the shortened topic names on the heatmap; only the workbook layout and formatting were set by hand in Tableau.
- The 2023 inventory is read as UTF-8 and the 2024 inventory as Windows-1252, the encodings the files actually use.
- Linking 2024 and 2025 use cases uses a name-similarity threshold of 0.8, chosen by reading sampled pairs; the check is shown in `02_build_data.Rmd`, Section A4.
- The Department of Defense is excluded from workforce figures: its June–July 2026 OPM data are incomplete, and the OMB inventories do not cover it either.
