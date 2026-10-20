## 1. Unique unit names and event form validation
- [x] 1.1 District names unique system-wide, congregation names unique per district (409, normalised, API only); create and rename. The dialogs show the server detail
- [x] 1.2 Event creation form rejects an end that is not after the start before submitting _(bereits vorhanden: `EventListView.submitCreate`, getestet in `EventListView.test.ts`)_

## 2. Duplicate persons and duty conflicts
- [x] 2.1 Leader creation: duplicate hint with explicit override (`LEADER_DUPLICATE`, `confirm_duplicate`, hint in the add dialog)
- [x] 2.2a Duty conflict check by linked account (block) and typed name (warn), overlap by event times with the default duration as fallback
- [x] 2.2b Duties may reference a leader as a third identity (migration `20261020_duty_leader_identity`, API, overlap lookup v2 incl. the leader's service assignments)
- [ ] 2.2d Duties panel offers the leader choice; assigning a leader to a service checks the leader's duties (reverse direction)
- [x] 2.2c Cross-congregation duty check for congregation-scoped planners (SECURITY DEFINER lookup `duty_identity_schedule` returning only schedule facts; pinned by an audit test and tested with the application role)

## 3. Matrix conflict display
- [x] 3.1 Matrix endpoint returns conflicts per cell (double booking, travel time among the loaded assignments; unavailability and duties are not part of this step); cells show a labelled marker

## 4. Person–congregation–role model
- [ ] 4.1 Relation, migration and screens replacing home congregation and special role

## 5. Closure
- [ ] 5.1 Baseline specs updated, change archived
