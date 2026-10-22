# holidays Specification

## Purpose

Imports public holidays and NAK church feast days as district-level `Feiertag` planning slots so they appear in the matrix and exports.

## Requirements

### Requirement: Church feast days
The system SHALL compute Palmsonntag, Ostersonntag and Pfingstsonntag from the Easter date (Gauss algorithm), the Entschlafenen-Gottesdienste on the first Sunday of March, July and November, and the four Advent Sundays from 25 December, independent of a district's `state_code`, and import them as confirmed district-level `Feiertag` slots applicable to all congregations.

#### Scenario: Easter 2026
- **WHEN** feast days for 2026 are computed
- **THEN** Ostersonntag is 5 April 2026

#### Scenario: Advent 2026
- **WHEN** feast days for 2026 are computed
- **THEN** the 1st Advent is 29 November, the 2nd Advent is 6 December, the 3rd Advent is 13 December, and the 4th Advent is 20 December

#### Scenario: Advent rule
- **WHEN** the Advent Sundays of a year are computed
- **THEN** the 4th Advent is the Sunday strictly before 25 December and the 1st to 3rd Advent are the Sundays three, two and one week earlier
- **AND** the 4th Advent is 24 December in 2023 and 18 December in 2033, when 25 December is a Sunday

#### Scenario: Advent dates are imported as holidays
- **WHEN** the computed feast days are imported for a district
- **THEN** each Advent Sunday is a confirmed district-level planning slot with category `Feiertag` applicable to all congregations

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
