## ADDED Requirements

### Requirement: Provider adapters preserve the CalendarConnector boundary
Google and Microsoft integrations SHALL expose provider behavior only through the provider-neutral CalendarConnector port.

#### Scenario: Provider SDK is replaced
- **WHEN** an adapter changes from raw HTTP to an SDK or to another SDK
- **THEN** domain and application code SHALL require no provider-specific changes

### Requirement: Fetches are complete or explicitly failed
A successful provider fetch SHALL include all pages in the requested synchronization window.

#### Scenario: Provider returns another page
- **WHEN** Google returns a nextPageToken or Microsoft returns an @odata.nextLink
- **THEN** the adapter SHALL continue until no continuation remains

#### Scenario: Later page fails
- **WHEN** a later page cannot be fetched after the bounded resilience policy is exhausted
- **THEN** the adapter SHALL fail the fetch explicitly and SHALL NOT report the partial result as complete

### Requirement: Provider failures are normalized
Provider transport, throttling, authentication, and API failures SHALL be translated to typed connector errors.

#### Scenario: Transient throttling
- **WHEN** an idempotent provider read receives a retryable throttling or server response
- **THEN** the adapter SHALL apply the bounded resilience policy and honor provider retry guidance where supported

### Requirement: Credentials remain adapter infrastructure
OAuth access and refresh tokens SHALL not enter domain models or logs.

#### Scenario: Access token expires
- **WHEN** a provider supports refresh and the stored credentials permit it
- **THEN** refresh SHALL occur within infrastructure/application credential handling and updated encrypted credentials SHALL be persisted safely
