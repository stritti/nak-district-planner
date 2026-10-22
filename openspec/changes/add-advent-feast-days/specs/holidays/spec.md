## MODIFIED Requirements

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
