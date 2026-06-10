## ADDED Requirements

### Requirement: Field-level sync authority classification
The system SHALL define and enforce field-level sync authority: STRUCTURAL, SOFT, and CONDITIONAL.

#### Scenario: STRUCTURAL field change from external ignored
- **WHEN** an external system modifies a STRUCTURAL field (congregation_id, planning_date, category)
- **THEN** the sync SHALL ignore the change and log a warning

#### Scenario: SOFT field change from external accepted
- **WHEN** an external system modifies a SOFT field (title, description)
- **THEN** the sync SHALL apply the change to EventInstance

#### Scenario: Unclassified field defaults to STRUCTURAL
- **WHEN** a field is not explicitly classified
- **THEN** the sync SHALL treat it as STRUCTURAL (never externally mutable)

### Requirement: Classification mapping
The system SHALL maintain a code-defined mapping of fields to their authority classification.

#### Scenario: Classification loaded at startup
- **WHEN** the sync engine starts
- **THEN** it SHALL load the field-to-authority mapping from a central definition

#### Scenario: Classification not admin-configurable
- **WHEN** an administrator attempts to modify field classifications via API
- **THEN** the system SHALL reject the change (classification is code-defined only)
