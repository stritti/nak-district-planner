## ADDED Requirements

### Requirement: Demo district walkthrough matches the seed
The documentation SHALL contain a walkthrough of the demo district that names its district, congregations with service times, leaders, organist, calendar subscription and number of services, and shows each matrix conflict in the week the seed creates it. A backend unit test SHALL fail when the seed and the walkthrough diverge, and CI SHALL run it when either changes.

#### Scenario: Seed changes a service time
- **WHEN** a change moves a demo congregation's service time without updating the walkthrough
- **THEN** the backend unit tests fail

#### Scenario: Walkthrough edited alone
- **WHEN** a pull request changes only the walkthrough page
- **THEN** CI runs the backend unit tests including the walkthrough check

### Requirement: User documentation follows every change
Every OpenSpec change that alters user-visible behaviour SHALL name the affected VitePress pages in its proposal and SHALL update them in the same change. When the demo district shows the changed behaviour, the change SHALL update the seed and the walkthrough together. The OpenSpec project configuration SHALL state these rules for proposals and tasks.

#### Scenario: New matrix rule
- **WHEN** a change adds a conflict rule that the matrix shows
- **THEN** its tasks include updating the conflict rules page and, if the demo district gets an example, the seed and the walkthrough
