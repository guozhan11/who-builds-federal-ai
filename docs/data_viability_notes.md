# Data Viability Notes

Working notes for Section 2 of the proposal. All figures below were computed from the downloaded files on 2026-09-21 with `code/02_build_data.Rmd`. Months for hires and exits are personnel-action effective months.

## Source 1 — OPM Federal Workforce Data (FWD)

| Item | Detail |
|----|----|
| Producer / dataset | U.S. Office of Personnel Management, Federal Workforce Data (EHRI Status and Dynamics files) |
| URL | <https://data.opm.gov/get-data/data-downloads> (API: `https://data.opm.gov/api/v1/files/{employment,separations,accessions}`) |
| Unit of observation | Employment: one federal civilian employee on the last day of a month. Separations / accessions: one personnel action. |
| Coverage | Federal civilian executive-branch workforce, all 50 states + DC + overseas duty stations. Employment snapshots back to 2005; flow files monthly back to 2005 (downloaded: 2024-01 to 2026-07). |
| Size | Employment snapshot \~2.0–2.3M rows × 64 columns per month. Separations \~10k–130k rows × 69 columns per month (497,032 separations Jan 2025–Jul 2026). |
| Key variables | `department_code` / `agency_subelement` (agency; drill-down), `separation_category` (quit, retirement, RIF, …), `drp_indicator` (Deferred Resignation Program), `occupational_group` / `occupational_series` (which expertise left, e.g. IT group 2210), `stem_occupation`, `supervisory_status`, `length_of_service_years`, `duty_station_state` / `county` (geography). |
| Limitations | (1) Excludes USPS, intelligence agencies, TVA, Federal Reserve Board staff, and most legislative/judicial branch. (2) DoD ("Department of War") components did not submit June–July 2026 data, so DoD headcount in the latest snapshot is understated; use 2026-05 or exclude DoD for latest comparisons. (3) Files are revised: each month has multiple versions; the script keeps only the `current` version, so numbers may shift slightly after future re-downloads. (4) Flow files are organized by processing month; a handful of records carry earlier effective dates, so time series should start at 2024-01. (5) Age and pay are bracketed or rounded per OPM's release policy. |
| Join | None: not merged with OMB data. |
| Access confirmed | Yes — 31 separations + 31 accessions monthly files + 5 employment snapshots downloaded as Parquet (\~380 MB). |

Headline check (non-DoD headcount): 1,540,667 (Sep 2024) → 1,457,869 (Sep 2025) → 1,344,285 (Jul 2026), about −12.7%. Of 497,032 separations since Jan 2025, 140,481 (28%) were flagged as Deferred Resignation Program; 10,976 were formal RIFs. Federal IT-group headcount (all agencies): 101,498 (Sep 2024) → 84,733 (Jul 2026).

## Source 2 — OMB Federal Agency AI Use Case Inventories (2023, 2024, 2025)

| Item | Detail |
|----|----|
| Producer / dataset | Office of Management and Budget, consolidated Federal Agency AI Use Case Inventory |
| URL | <https://github.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory> ; <https://github.com/ombegov/2024-Federal-AI-Use-Case-Inventory> |
| Unit of observation | One AI use case reported by an agency. |
| Coverage | Federal civilian agencies (DoD and intelligence community not included). Inventory years 2023, 2024, 2025. |
| Size | 2023: 710 × 10 · 2024: 2,133 × 62 · 2025: 3,611 × 36 (plus 900 × 5 consolidated commercial-off-the-shelf rows) |
| Key variables | `agency`, `development_stage` (pre-deployment / pilot / deployed / retired), `is_high_impact`, `topic_area` (e.g. benefits processing, law enforcement, HR), `classification` (classical ML, generative AI, agentic AI…), `contracting_usage` (vendor vs in-house), `hi_*` safeguard fields (impact assessment, independent review, monitoring, appeal process). |
| Limitations | (1) Self-reported and agency-curated; counts reflect reporting practice as much as real adoption (NASA: 18 cases in 2024 vs 425 in 2025). (2) Schema changed every year — only agency, use case name, and development stage are comparable across all three years. (3) Commerce (223) and Education (56) 2025 records have blank stage, type, and impact fields in the consolidated CSV even though OMB's README summary reports them as deployed/piloted. (4) Safeguard fields are blank for \~71% of high-impact cases (VA: all 215 blank), so "missing" must not be read as "not done". (5) TVA, Federal Reserve Board, and NIGC report AI use but have no OPM workforce counterpart (102 of 3,611 cases). (6) USAID reported 137 cases in 2024 and none in 2025 because the agency was dissolved. |
| Join | 2024 ↔ 2025 inventories only, via `data/keys/use_case_link_2024_2025.csv`. Not merged with OPM data. |
| Access confirmed | Yes — CSVs, data dictionaries, and standardization reports downloaded. |

## Processed files and join keys

| File | Grain | Notes |
|----|----|----|
| `data/processed/ai_use_cases.csv` | AI use case × inventory year | Harmonized `stage` and `build`; raw values kept in `stage_raw`, `build_raw`; `link_id` joins a 2024 record to its 2025 record |
| `data/processed/workforce.csv` | measure (headcount / hires / exits) × period × department × occupation × (age, tenure for headcount) × (separation category, DRP flag for exits) | Long format, one count column `n`; DoD kept, drop it for OMB comparisons |
| `data/keys/use_case_link_2024_2025.csv` | matched pair of use cases | Generated join key 2024 ↔ 2025: exact or fuzzy (edit similarity ≥ 0.8) name match within agency |
