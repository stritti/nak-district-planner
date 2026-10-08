## ADDED Requirements

### Requirement: Release validation uses an integrated candidate
The release process SHALL validate the actual combined commit after stacking or merging release PRs, not infer integration correctness solely from each PR's independent CI result.

#### Scenario: Individually green overlapping pull requests
- **WHEN** two independently green pull requests modify common calendar paths, schemas or migrations
- **THEN** the combined candidate SHALL run relevant unit, PostgreSQL integration, security, migration, OpenSpec and end-to-end checks before release approval

### Requirement: Exactly one intended Alembic upgrade head
The release migration graph SHALL have one intended upgrade head and SHALL successfully upgrade a representative previous-version PostgreSQL database to that head without data loss outside documented migration policies.

#### Scenario: Assignment and holiday migration branches
- **WHEN** #484's `20261007_assignment_unique` and #485's `20261007_confirm_holidays` both descend from `20261007_celery_tables`
- **THEN** integration SHALL adjust revision lineage or add an explicit merge revision, and `alembic heads`, `upgrade head`, `alembic check` and downgrade policy SHALL be verified on the integrated tree

#### Scenario: Existing duplicate assignments
- **WHEN** the assignment uniqueness migration encounters duplicates
- **THEN** retention order SHALL be deterministic, the removed rows SHALL be measured or reported, and the documented irreversible cleanup policy SHALL be reviewed before production deployment

### Requirement: Calendar synchronization is bounded, deterministic and safely reconciled
The system SHALL apply provider-independent identity and synchronization decisions, bound remote calendar resource consumption, and SHALL NOT infer source deletion merely from absence in an incomplete or bounded snapshot.

#### Scenario: Event moved outside an external provider query window
- **WHEN** a linked CalDAV or ICS event moves outside the requested time window but remains at the provider
- **THEN** the synchronization SHALL NOT cancel or hard-delete it on the basis of absence alone

#### Scenario: Provider writes across multiple links
- **WHEN** a use case would write to multiple provider links, one of which is unsupported or invalid
- **THEN** it SHALL reject the unsupported combination before sending any provider write, without falsely claiming database rollback can reverse an external side effect

#### Scenario: Untrusted large or stalled calendar response
- **WHEN** a provider response exceeds the defined size or wall-clock budget
- **THEN** synchronization SHALL fail safely, without accepting private network destinations, leaking credentials or occupying a worker indefinitely

### Requirement: Public calendar publication is distinct from tenant authorization
The system SHALL independently enforce tenant-access restrictions, business applicability, approval state and event publication visibility. Database RLS SHALL not be treated as the sole authorization or public-visibility rule.

#### Scenario: Distributed internal district event
- **WHEN** a confirmed district-level slot applies to a congregation but its event is INTERNAL
- **THEN** a PUBLIC congregation export SHALL not include the event title or description

#### Scenario: Export under the production database role
- **WHEN** an unauthenticated public, internal or personal export is executed under the restricted NOBYPASSRLS production role
- **THEN** its visibility and assignment/name access SHALL match the token scope and shall not reveal data outside that scope

### Requirement: Service assignments and generated occurrences retain database-enforced identity
The system SHALL enforce at most one assignment per planning slot and SHALL prevent two overlapping accepted assignments for a leader under concurrency. Generated slot occurrence identity SHALL persist independently of later edits to the date or time.

#### Scenario: Concurrent writes
- **WHEN** two independent database sessions assign one leader to overlapping slots
- **THEN** only the conflict-free result SHALL commit and the competing attempt SHALL return a documented conflict outcome

#### Scenario: Planner moves a generated slot
- **WHEN** a generated service changes time but keeps its identity and owning congregation
- **THEN** a subsequent generation run SHALL not create a duplicate occurrence

#### Scenario: Generated slot changes category or owner
- **WHEN** a generated slot ceases to represent the original congregation's service occurrence
- **THEN** its generation key SHALL be cleared or reassigned safely and the original occurrence SHALL remain eligible for generation

### Requirement: OpenSpec describes the integrated implementation
The release specification baseline SHALL reflect the merged production code; active change deltas SHALL be reconciled before archiving, and no change SHALL be archived as complete while it is materially modified by another pending release PR.

#### Scenario: Generation spec archived while still changing
- **WHEN** #489 archives `auto-generate-draft-services-8-weeks` and #491 still changes its spec and tasks
- **THEN** the final archive and baseline SHALL incorporate the accepted #491 behavior and strict validation SHALL succeed

### Requirement: New application logic preserves the dependency direction
New application components SHALL depend on domain/application ports for persistence and external systems, rather than importing concrete infrastructure adapters. Existing exceptions SHALL remain explicitly bounded legacy debt.

#### Scenario: New direct adapter import
- **WHEN** a new application service imports a concrete `app.adapters` module
- **THEN** the architecture gate SHALL fail until the dependency is inverted rather than extending the legacy allowlist

### Requirement: Release verification covers failure paths
The combined release candidate SHALL meet the repository's existing coverage threshold of greater than 80 percent and SHALL exercise security, concurrency, partial failure, time-zone boundary and migration edge cases without weakening any existing quality gate.

#### Scenario: Green checks on separate heads
- **WHEN** all eight release PRs have successful individual CI workflows
- **THEN** this SHALL NOT by itself constitute release approval until relevant integrated verification evidence is recorded
