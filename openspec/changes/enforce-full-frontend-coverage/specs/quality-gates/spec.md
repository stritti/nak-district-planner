## MODIFIED Requirements

### Requirement: Frontend production code maintains at least 80 percent coverage
The frontend test configuration SHALL measure all relevant TypeScript and Vue production sources below `src`. Test files, type declarations and the bootstrap-only application entry point MAY be excluded explicitly.

#### Scenario: New production file is added
- **WHEN** a new `.ts` or `.vue` production file is added below `src`
- **THEN** it is automatically included in the coverage denominator
- **AND** no manual allowlist entry is required

#### Scenario: Coverage regresses
- **WHEN** statements, branches, functions or lines fall below 80 percent for the measured production scope
- **THEN** the frontend unit-test CI job fails