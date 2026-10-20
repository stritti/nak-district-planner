## ADDED Requirements

### Requirement: Contract upgrade preserves runtime-role authorization
The hash-only export-token migration SHALL be tested using a non-owner, NOBYPASSRLS application role, not only the database owner. Token-based access SHALL preserve the existing PUBLIC, INTERNAL and personal-feed scope without permitting access to another tenant.

#### Scenario: Public subscription after upgrade
- **WHEN** a valid PUBLIC token is supplied to an application-role transaction
- **THEN** only resources permitted to that feed are visible

#### Scenario: Internal and personal subscriptions after upgrade
- **WHEN** an INTERNAL or user-bound feed token is supplied
- **THEN** the existing scope rules for that feed type hold
- **AND** another tenant's private resources remain inaccessible

#### Scenario: Revoked, unknown or foreign token
- **WHEN** a revoked, unknown or foreign-tenant token is supplied
- **THEN** private resources are not disclosed

#### Scenario: Runtime connection cannot bypass RLS
- **WHEN** tests open the application-role connection
- **THEN** they assert the role is neither superuser nor BYPASSRLS and does not own the target tables

### Requirement: Contract migration eliminates plaintext SQL dependencies
Policies and SECURITY DEFINER functions SHALL match the approved security definitions and SHALL NOT depend on `export_tokens.token` after the upgrade.

#### Scenario: Plaintext column removed
- **WHEN** the contract migration completes
- **THEN** the plaintext column does not exist
- **AND** active policies and functions contain no remaining reference to that column

### Requirement: Reliable CI verification
The restricted-role upgrade tests SHALL run in the existing PostgreSQL integration CI and fail when configured expected prerequisites are missing rather than passing silently.

#### Scenario: Missing restricted-role fixture
- **WHEN** CI cannot create the non-owner role connection
- **THEN** the suite fails visibly
