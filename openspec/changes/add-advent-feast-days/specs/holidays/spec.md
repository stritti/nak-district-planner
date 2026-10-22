## MODIFIED Requirements

### Requirement: Church feast days
The system SHALL compute Palmsonntag, Ostersonntag and Pfingstsonntag from the Easter date (Gauss algorithm), the Entschlafenen-Gottesdienste on the first Sunday of March, July and November, and the 1st through 4th Advent, independent of a district's `state_code`. The 1st Advent SHALL be the fourth Sunday before 25 December; the 2nd through 4th Advent SHALL be the following Sundays. All computed church feast days SHALL be imported as confirmed, district-level planning slots with category `Feiertag` applicable to all congregations.

#### Scenario: Easter 2026
- **WHEN** feast days for 2026 are computed
- **THEN** Ostersonntag is 5 April 2026

#### Scenario: Advent 2026
- **WHEN** feast days for 2026 are computed
- **THEN** the 1st Advent is 29 November, the 2nd Advent is 6 December, the 3rd Advent is 13 December, and the 4th Advent is 20 December

#### Scenario: Advent dates are imported as holidays
- **WHEN** the computed feast days are imported for a district
- **THEN** each Advent Sunday is a confirmed district-level planning slot with category `Feiertag` applicable to all congregations