## Why
The matrix marks double booking and short travel time only among the leader assignments it has loaded. Organisational duties of the same person (organist, conductor, ...), services outside the loaded range or group and recorded absences are checked by the assignment dialog but stay invisible in the matrix, so a planner only learns about them when reassigning (roadmap: "Die Matrix zeigt Dienste und Abwesenheiten noch nicht in der Konfliktanzeige").

## What Changes
- Matrix conflicts also consider the duty identity lookup of every assigned leader (duties and the leader's other service assignments in the district) and the leader's unavailability periods, with the same rules as the assignment dialog: `no_double_booking`, `travel_time_check` and `leader_available`.
- A duty on the assignment's own service is ignored, as in the assignment dialog.
- Absences of all assigned leaders are loaded in one query (`LeaderUnavailabilityRepository.list_overlapping_for_leaders`).
- Visibility is unchanged: the duty lookup returns nothing for callers below `PLANNER`, absences follow row-level security.

## Capabilities
### Modified Capabilities
- `service-assignment-matrix`: matrix cells show conflicts with duties, outside services and absences.

## Impact
Backend matrix builder, matrix conflict domain function, unavailability repository port/adapter, unit and PostgreSQL tests. No migration and no API schema change; the frontend already renders conflicts by severity and message.
