# holidays Specification

## Purpose

Imports public holidays and NAK church feast days as district-level `Feiertag` planning slots so they appear in the matrix and exports.

## Requirements

### Requirement: Church feast days
The system SHALL compute Palmsonntag, Ostersonntag and Pfingstsonntag from the Easter date (Gauss algorithm) and the Entschlafenen-Gottesdienste on the first Sunday of March, July and November, independent of a district's `state_code`.

#### Scenario: Easter 2026
- **WHEN** feast days for 2026 are computed
- **THEN** Ostersonntag is 5 April 2026

### Requirement: Public holidays via Nager.Date
For districts with a `state_code` the system SHALL import national holidays and holidays of that state from the Nager.Date API; holidays of other states SHALL be skipped. Districts without `state_code` SHALL receive no public holidays.

#### Scenario: Bavarian district
- **WHEN** the import runs for a district with `state_code = BY`
- **THEN** national and Bavaria-specific holidays are imported and other states' holidays are not

### Requirement: Idempotent import
Holiday slots SHALL be keyed by stable identifiers derived from district, date and name; repeated imports SHALL update or skip existing slots and report `created`, `updated` and `skipped` counts.

#### Scenario: Second import of a year
- **WHEN** the same year is imported twice
- **THEN** the second run creates no new slots

### Requirement: Scheduled and manual import
The beat task `auto_import_feiertage` SHALL run on the first of each month at 03:00 and import the current year, plus the next year from September onwards. `POST /api/v1/districts/{id}/feiertage` SHALL trigger an import for a `DISTRICT_ADMIN`; `GET /api/v1/districts/{id}/feiertage/states` SHALL list German state codes.

#### Scenario: Run in September
- **WHEN** the monthly task runs in September
- **THEN** the current and the following year are imported
