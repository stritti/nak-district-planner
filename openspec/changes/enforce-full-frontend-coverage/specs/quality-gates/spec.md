## ADDED Requirements

### Requirement: Frontend production code maintains at least 80 percent coverage per file
The frontend test configuration SHALL measure all relevant TypeScript and Vue production sources below `src`. Test files, test-support modules and type declarations MAY be excluded explicitly. The application entry point MAY be excluded only when it contains bootstrap wiring and all executable startup behavior is delegated to covered production modules. Every measured production file SHALL maintain at least 80 percent statements, branches, functions and lines coverage.

#### Scenario: New production file is added
- **WHEN** a new `.ts` or `.vue` production file is added below `src`
- **THEN** it is automatically included in the coverage denominator
- **AND** no manual allowlist entry is required
- **AND** the file itself must satisfy the 80 percent thresholds

#### Scenario: Coverage regresses in one production file
- **WHEN** statements, branches, functions or lines fall below 80 percent for any measured production file
- **THEN** the frontend unit-test CI job fails

#### Scenario: Test-support module is added
- **WHEN** a module below `src/testing` exists only to provide Vitest/browser test doubles and is not shipped as application logic
- **THEN** it is excluded from the production coverage denominator

#### Scenario: Bootstrap entry point contains application behavior
- **WHEN** executable authentication, service-worker or other application behavior would otherwise live in `main.ts`
- **THEN** that behavior is moved to covered production modules before `main.ts` is excluded from unit coverage
