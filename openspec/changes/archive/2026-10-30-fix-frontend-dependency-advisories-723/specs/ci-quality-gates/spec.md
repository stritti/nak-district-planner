## ADDED Requirements

### Requirement: Patched frontend dependency versions SHALL be installed and audited
The frontend's frozen Bun lockfile SHALL resolve direct `happy-dom` to version 21.0.4 or newer and transitive `fast-uri` to patched 3.1.9 or newer within the compatible major range, and CI SHALL continue to enforce `bun audit --audit-level=moderate` as a failing gate for moderate or higher advisories.

#### Scenario: Patched dependency graph
- **WHEN** GitHub Actions installs the frozen Bun dependencies and audits the frontend
- **THEN** both patched package versions are installed and the audit exits successfully without exceptions

#### Scenario: Vulnerable transitive dependency reintroduced
- **WHEN** a dependency update resolves `fast-uri` to an affected version and Bun audit reports a moderate advisory
- **THEN** the existing Security Scans workflow fails instead of suppressing the finding

#### Scenario: Vulnerable test DOM dependency reintroduced
- **WHEN** Happy DOM resolves to an affected version and Bun audit reports its high-severity advisory
- **THEN** the existing Security Scans workflow fails

#### Scenario: Manifest and frozen lockfile diverge
- **WHEN** the Happy DOM manifest range is incompatible with its locked resolution
- **THEN** `bun install --frozen-lockfile` fails and CI blocks the change

#### Scenario: Frontend behavior after major dev dependency upgrade
- **WHEN** Vue unit tests exercise both successful interactions and expected error cases using Happy DOM 21
- **THEN** the existing behavior and coverage requirements remain satisfied
