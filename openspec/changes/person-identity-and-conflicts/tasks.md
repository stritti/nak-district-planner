## 1. Unique unit names and event form validation
- [x] 1.1 District names unique system-wide, congregation names unique per district (409, normalised, API only); create and rename. The dialogs show the server detail
- [x] 1.2 Event creation form rejects an end that is not after the start before submitting _(bereits vorhanden: `EventListView.submitCreate`, getestet in `EventListView.test.ts`)_

## 2. Duplicate persons and duty conflicts
- [x] 2.1 Leader creation: duplicate hint with explicit override (`LEADER_DUPLICATE`, `confirm_duplicate`, hint in the add dialog)
- [ ] 2.2 Duties may reference a leader; cross-congregation conflict check for duties (block for strong identity, warn for names)

## 3. Matrix conflict display
- [ ] 3.1 Matrix endpoint returns conflicts per cell; cells show a marker

## 4. Person–congregation–role model
- [ ] 4.1 Relation, migration and screens replacing home congregation and special role

## 5. Closure
- [ ] 5.1 Baseline specs updated, change archived
