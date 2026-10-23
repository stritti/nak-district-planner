## ADDED Requirements

### Requirement: Registration congregation choices SHALL match the current district
The public registration view MUST show congregation options only for the currently selected district. It SHALL immediately clear an obsolete congregation selection and options when the district changes. A delayed response or error from an obsolete request MUST NOT overwrite the current district's choices.

#### Scenario: Out-of-order district responses
- **WHEN** a user selects district A then district B and A's request completes after B's request
- **THEN** only district B's congregations remain available for selection

#### Scenario: District selection cleared while request is pending
- **WHEN** the district selection is cleared before a congregation request completes
- **THEN** the congregation selection and options remain empty, even if the previous request later completes

#### Scenario: Superseded request fails
- **WHEN** a previous district's request fails after the selected district's request succeeds
- **THEN** the error from the previous request does not clear the current district's congregations
