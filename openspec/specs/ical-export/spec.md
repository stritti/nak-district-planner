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
