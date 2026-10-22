## Context

A leader (Amtsträger) carries one home congregation (`leaders.congregation_id`, NULL = district level) and one special role (`leaders.special_role`). People serve several congregations (a congregation leader of two congregations). The planning conflict rules already work per person; only the data model cannot say "Vorsteher of A and B".

## Decisions (agreed with the maintainer)

1. **Assignment = congregation + role + home flag.** A person has one or more assignments; exactly one is the home assignment (used for sorting and as default).
2. **Roles as today:** `GEMEINDEVORSTEHER`, `BEZIRKSVORSTEHER` or none. No configurable role list; organisational roles such as organist stay duties.
3. **Immediate replacement.** `leaders.congregation_id` and `leaders.special_role` are dropped in the same revision that creates and backfills the new table; API, UI, registration and tests use only the new structure. The downgrade restores both columns from the home assignment (additional assignments are lost).
4. **Visibility and rights.** A person is visible to members of every assigned congregation. District-level `PLANNER` and above manage all assignments; a congregation-scoped planner or admin manages only the assignment of their own congregation (add, change role, remove) and cannot touch other congregations' assignments.
5. **Overview.** The leader list shows a person under each assigned congregation with the role there; the home congregation is highlighted. District-level assignments form their own section.

## Data model

`leader_assignments(id, leader_id → leaders ON DELETE CASCADE, congregation_id → congregations NULL = district level, role NULL | GEMEINDEVORSTEHER | BEZIRKSVORSTEHER, is_home bool, created_at, updated_at)`

* unique `(leader_id, congregation_id)` with NULLs not distinct (one district-level row at most),
* partial unique index `(leader_id) WHERE is_home` (exactly one home per leader, enforced together with the application rule "at least one assignment"),
* no database check on the role/level combination: new writes are validated by the application (`BEZIRKSVORSTEHER` only on the district level, `GEMEINDEVORSTEHER` only on a congregation), so legacy rows that combine them differently migrate unchanged instead of failing the revision and are flagged for review in the UI.

Backfill: one assignment per existing leader from `(congregation_id, special_role)`, `is_home = true`. The revision cannot fail on existing data.

## Row-level security

Every policy that read `leaders.congregation_id` (the four leader policies) is replaced by one built on `leader_assignments` (module `leader_assignment_rls.py`), which reach the assignments through three SECURITY DEFINER yes/no predicates (`leader_assignment_member`, `leader_assigned_to`, `leader_subject_scope`) instead of inline sub-selects — an inline `leader_assignments` sub-select pulls that table's own policy into every policy that reads `leaders` and made the matrix query about five times slower (p95 ~190 ms → ~590 ms); the old definitions are kept verbatim for the downgrade. `leader_assignments` carries `district_id` itself so its policies never read `leaders` (no recursion).

* **Leaders:** visible to the district and to members of every assigned congregation; a leader without any assignment is visible to the district level only. Update/delete follow the assigned congregations (planner or higher), insert is allowed for district planners and for planners of any congregation of the district, because the assignment is written in the same transaction (the ORM insert does not read the row back).
* **Assignments:** readable like their congregation (and by a valid export token of the district, which the duty-feed policies need); writable by district planners for all rows and by a congregation planner only for rows of their own congregation. A congregation planner therefore cannot move the *home flag* to or from another congregation's assignment (that needs two rows); this stays a district-level action.
* The definer functions of the duty lookup read `leaders` only by id/account/name and are unaffected.

## API

* Leader responses carry `assignments: [{id, congregation_id, role, is_home, revision}]` instead of `congregation_id` and `special_role`; list filters by congregation match any assignment.
* Create accepts `assignments` (at least one, exactly one home). Leader updates no longer touch assignments.
* Assignment sub-resource under `/leaders/{leader_id}/assignments` (`POST`, `PATCH /{id}`, `DELETE /{id}`) with `If-Match`, row locks and the rights of decision 4; moving the home flag is a `PATCH` that unsets the previous home atomically; the last assignment cannot be removed, the home assignment only after another one became home.
* Registration keeps the registrant's single congregation and role (one choice in a public form, no table change); approval creates the leader from that choice or from an explicit `assignments` list that replaces it and the two override fields.
* `link-self` checks the visible assignments instead of the home congregation.

## Frontend

The add dialog selects the first assignment; the edit dialog gets an assignment list (add, role, home, remove) limited by the user's rights; the overview repeats a person under each assigned congregation with the role and a home marker; inline cells edit the role of the assignment shown in that section.

## Rollout and risk

Single revision, transactional. Needs a backup (upgrade note); irreversible for data that exists only in additional assignments. Implementation in four reviewable PRs: (1) revision, domain, repository, RLS and their tests; (2) API; (3) registration and `link-self`; (4) frontend. Main stays releasable only after (1)–(4) are merged, so they are merged together in one release train (a feature branch collects them).
