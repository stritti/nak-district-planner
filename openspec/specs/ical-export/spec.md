# ical-export Specification

## Purpose

Publishes planning data as subscribable iCalendar feeds (UC-05/UC-06) through unguessable export tokens with public (anonymised) and internal semantics.

## Requirements

### Requirement: Export token management
`POST`, `GET` and `DELETE /api/v1/export-tokens` SHALL require `DISTRICT_ADMIN` of the token's district (listing without `district_id` only for superadmins). Tokens SHALL be generated with `secrets.token_urlsafe(32)`, typed `PUBLIC` or `INTERNAL`, and MAY be scoped to a congregation or a leader.

#### Scenario: Token deleted
- **WHEN** a token is deleted
- **THEN** subsequent feed requests with it respond with 404

### Requirement: ICS feed endpoint
`GET /api/v1/export/{token}/calendar.ics` SHALL be unauthenticated, respond with 404 for unknown tokens, set the token as RLS context, and return `text/calendar` covering planning slots from one year back to two years ahead (narrowed to the congregation for congregation tokens). The `approval_status` query parameter SHALL accept `confirmed_only` or `include_planned`.

#### Scenario: Unknown token
- **WHEN** the feed is requested with an unknown token
- **THEN** the endpoint responds with 404 without revealing whether a token exists

#### Scenario: Invitation copy location
- **WHEN** a slot is an invitation copy of another congregation's service
- **THEN** its `LOCATION` is the host congregation, not the invited one, and the host's Dienstleiter appears in the `COMMENT` (anonymised in public feeds)

#### Scenario: Default approval filter
- **WHEN** a public token without leader scope is used without `approval_status`
- **THEN** only `CONFIRMED` slots are exported; other tokens also export `PLANNED` slots marked `STATUS:TENTATIVE`

### Requirement: Leader name anonymisation
Leader names SHALL appear in full only for `INTERNAL` and leader-scoped tokens; `PUBLIC` tokens SHALL show `Dienstleiter: [Name anonymisiert]`.

#### Scenario: Public feed
- **WHEN** a public token's feed contains an assigned service
- **THEN** the leader name is replaced by the anonymised placeholder

### Requirement: Stable UIDs
Each VEVENT UID SHALL be `{planning_slot_id}@nak-bezirksplaner`, independent of the `EventInstance`, so calendar clients do not see re-exported events as new.

#### Scenario: Feed fetched twice
- **WHEN** the same slot is exported at two different times
- **THEN** both VEVENTs carry the same UID

### Requirement: Personal ICS includes organisational duties without duplicates
Personal calendar feeds for an authenticated, securely linked participant or a subject-bound, district-scoped INTERNAL personal export token SHALL include slots assigned through organisational duties, aggregating all of that person's tasks per slot into a single VEVENT. The UID SHALL remain `{planning_slot_id}@nak-bezirksplaner`. A person who is also the service leader SHALL still receive only one VEVENT.

#### Scenario: Additional constraints for Personal ICS includes organisational duties without duplicates
- **GIVEN** this requirement is applicable
- **WHEN** the system processes the relevant operation
- **THEN** Updates to appointments, time and cancellation SHALL be reflected in subsequent feed responses; public or unscoped district INTERNAL exports SHALL not reveal personal duty-holder identities or private duty labels. Export token reads SHALL be limited by the bound subject and district through RLS and require the subject's current effective scope authorization on every feed request; existing PUBLIC/INTERNAL leader tokens SHALL retain legacy leader visibility and MUST NOT infer a duty owner from unlinked leader names. No token SHALL be issued for an unlinked free-text name.

#### Scenario: Bound subject token
- **WHEN** a verified user obtains a personal INTERNAL export token bound to their subject for district A
- **THEN** the token reveals only that subject's currently assigned events and duty labels in district A
- **AND** it cannot be used to request another subject or district by query parameter

#### Scenario: Duty-only participant without a leader record
- **WHEN** a securely linked user who has no leader record receives an organisational duty
- **THEN** their authenticated calendar and subject-bound personal ICS include that duty without fabricating a leader record

#### Scenario: Member loses district access
- **WHEN** a user retains a subject-bound ICS token but their effective membership for its district is revoked
- **THEN** subsequent token reads do not reveal formerly accessible duty events, even if an assignment still exists

#### Scenario: Revoked duty or token
- **WHEN** the last qualifying duty is removed or the personal token is revoked
- **THEN** subsequent token reads no longer reveal the removed duty or are rejected for a revoked token

#### Scenario: Multiple duties on one slot
- **WHEN** a person has both Organist and Dirigent assignments on one slot
- **THEN** their personal feed contains one VEVENT for the slot and both task labels

#### Scenario: Duty-only personal export
- **WHEN** a person is assigned Schließdienst without a service-leader assignment
- **THEN** their personal feed contains the event with Schließdienst as task

#### Scenario: Cancellation or removal
- **WHEN** a slot is cancelled or the person's last duty assignment is removed
- **THEN** the next feed response follows the established cancellation/removal policy and does not retain a stale personal booking

#### Scenario: Public token
- **WHEN** a PUBLIC export token is used
- **THEN** no personal organisational duty names, assignments or task labels are disclosed

### Requirement: Export credentials are hash-only at rest
Each ICS bearer credential SHALL be generated using at least 32 random bytes and returned only in the creation response. Only its SHA-256 digest SHALL persist in the database. Anonymous feed RLS and SECURITY DEFINER authorization SHALL compare digests of the presented credentials. A stored hash string SHALL NOT itself authorize a feed.

#### Scenario: Legacy subscription survives contract migration
- **WHEN** a previously issued valid ICS URL is fetched after the hash-only migration
- **THEN** its original token still authorizes the same district and visibility scope
- **AND** the raw secret is no longer present in database storage

#### Scenario: Hash impersonation fails
- **WHEN** a client presents a database-stored digest as the bearer token
- **THEN** the lookup and every RLS-protected read fail as for an invalid token

#### Scenario: Credential revocation
- **WHEN** an export token record is revoked
- **THEN** existing URLs immediately stop working with HTTP 404

### Requirement: Stable cancellation notifications
A `CANCELLED` previously published planning slot SHALL remain exported to the same token scopes with its original UID, an incremented revision `SEQUENCE` and `STATUS:CANCELLED`. A public token SHALL continue to enforce confirmation and internal visibility rules, and a draft deleted before confirmation SHALL simply be absent.

#### Scenario: Released event cancelled after export
- **WHEN** a previously exported confirmed event is cancelled
- **THEN** its iCalendar event retains its UID and reports `STATUS:CANCELLED`
