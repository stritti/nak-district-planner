## ADDED Requirements

### Requirement: Scoped configurable duty categories
The system SHALL allow district administrators to define organisational duty categories for their district and congregation administrators to add congregation-owned categories or override the inherited applicability, enabled state and capacity. Each category SHALL have a stable identifier, display name, stable code, owning scope and applicability to one or more event categories. Congregation overrides SHALL take precedence; in their absence district configuration SHALL apply.

#### Scenario: District category inherited by a congregation
- **WHEN** a district administrator enables Organist for Gottesdienst and a congregation has no override
- **THEN** Organist is available on that congregation's Gottesdienst planning slots

#### Scenario: Congregation disables an inherited category
- **WHEN** a congregation administrator disables Organist for Gottesdienst in their congregation
- **THEN** it is not offered for new assignments there, but remains available in the parent district and other congregations

#### Scenario: District-level event
- **WHEN** a slot belongs to a district and has no congregation
- **THEN** only district-level configuration determines its available categories

### Requirement: Idempotent service-specific defaults
The system SHALL provide Schließdienst, Organist and Dirigent as enabled default categories for `Gottesdienst`, and Schließdienst only for every other event category. Defaults SHALL be created idempotently without requiring assignments and without overwriting explicit local configuration.

#### Scenario: Defaults on first use
- **WHEN** an existing district has no custom duty configuration
- **THEN** Gottesdienst offers Schließdienst, Organist and Dirigent, while a non-Gottesdienst slot offers Schließdienst only

#### Scenario: Repeat seeding
- **WHEN** default initialisation executes twice
- **THEN** no duplicate categories or overrides are created

### Requirement: Safe category lifecycle
The system SHALL retain stored event duty assignments and their display information when a category is disabled or renamed; a used category SHALL NOT be hard-deleted in a way that loses assignment history. Reducing effective capacity below the number of already stored assignees SHALL preserve and flag those assignees, while rejecting additions exceeding the new capacity.

#### Scenario: Capacity reduced below existing assignments
- **WHEN** an administrator reduces a duty's capacity from two to one while two persons are already assigned
- **THEN** both records remain visible and the duty is flagged as over capacity
- **AND** a new third person is rejected until the number of assignments allows it

#### Scenario: Disable an assigned category
- **WHEN** an administrator disables a category already used on a planning slot
- **THEN** existing assignments remain readable but the category cannot be selected for new assignments

### Requirement: Scoped catalogue authorisation
District-level configuration writes SHALL require `DISTRICT_ADMIN` for that district; congregation-level writes SHALL require `CONGREGATION_ADMIN` for that congregation. Reads and writes SHALL enforce tenant boundaries.

#### Scenario: Foreign district mutation
- **WHEN** an administrator for district A attempts to modify a category belonging to district B
- **THEN** the request is rejected without changing any rows
