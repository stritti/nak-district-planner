## MODIFIED Requirements

### Requirement: Onboarding empty states
Empty lists that a new installation starts with SHALL explain the next step and, for users allowed to take it, offer it as an action: the first district, the first congregation of a district, the matrix of a district without congregations and the matrix without planned services. The matrix SHALL distinguish a district without congregations from a congregation or group filter without matches.

#### Scenario: District without congregations in the matrix
- **WHEN** the matrix of a district without congregations is shown and no congregation filter is set
- **THEN** it states that the district has no congregations yet instead of a filter hint
- **AND** offers "Gemeinde anlegen" only to district admins, which opens the new-congregation dialog of that district

#### Scenario: Group without congregations
- **WHEN** the selected group of the matrix has no congregations
- **THEN** it states that the group has no congregations and offers to show all groups

#### Scenario: Matrix without planned services
- **WHEN** the matrix shows congregations but no planned service in the selected range
- **THEN** it offers planners "Entwürfe erzeugen" for that range from the congregations' service times
- **AND** tells viewers that the planning creates the services
