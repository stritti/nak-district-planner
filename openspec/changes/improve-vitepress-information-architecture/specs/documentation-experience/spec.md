## ADDED Requirements

### Requirement: Product value is clear on the homepage
The VitePress homepage SHALL explain the district-wide planning value, principal user workflows, and supported V1 calendar sources. Providers that are not production-ready MUST be labeled planned.

#### Scenario: First-time visitor
- **WHEN** a visitor opens the project documentation
- **THEN** they can understand the purpose and find the task-oriented overview without reading architecture documents

### Requirement: Navigation follows tasks and avoids duplicated rules
The documentation SHALL provide separate routes for workflows, use-case references, local development, and operations. The overview SHALL link to canonical detailed documents instead of copying their full rules.

#### Scenario: Planner finds an assignment workflow
- **WHEN** a planner follows the workflow navigation
- **THEN** they find a matrix assignment explanation and links to use cases and role restrictions

### Requirement: Mermaid diagrams produce static SVG
Supported Mermaid flowchart and sequence diagrams SHALL render as static SVG at documentation build time. The documentation build SHALL reject broken internal links. Diagrams SHALL be explained in adjacent prose.

#### Scenario: Production documentation build
- **WHEN** the VitePress build is executed
- **THEN** the workflow and approval documentation pages contain SVG diagrams
- **AND** the published pages do not depend on a browser Mermaid runtime

### Requirement: Implementation status is distinguished from roadmap
The documentation MUST distinguish available V1 integration types (HTTPS ICS and CalDAV) from planned Google and Microsoft providers and future review-based ingestion.

#### Scenario: Connector comparison
- **WHEN** a reader checks calendar integration
- **THEN** production-ready V1 and future connectors are explicitly differentiated
