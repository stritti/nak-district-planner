## MODIFIED Requirements

### Requirement: Production upgrade actions are prominent in published Release Notes
Changes that require an operator to modify an existing production installation SHALL introduce an actionable, release-specific upgrade note alongside the change. The release workflow SHALL validate and prepend newly introduced upgrade notes under a prominent "WICHTIG: Anpassungen bei produktiven Installationen" heading to the **draft** GitHub Release before image promotion. The public GitHub Release SHALL not be published until this operation and the image checks are successful.

#### Scenario: Release includes a new required environment variable
- **WHEN** a version includes a new production upgrade note with affected deployments, pre-upgrade steps and post-upgrade checks
- **THEN** the draft GitHub Release description begins with the upgrade instructions
- **AND** the original generated changelog remains intact below those instructions
- **AND** the public release remains unavailable until both images are validated

#### Scenario: Subsequent release has no new required operator actions
- **WHEN** a later release only contains older upgrade notes or no upgrade notes
- **THEN** the release description stays unchanged
- **AND** older operator actions are not repeated

#### Scenario: Upgrade note publication fails
- **WHEN** a new upgrade note lacks affected deployments, pre-upgrade steps or post-upgrade checks, or GitHub rejects the release-description update
- **THEN** the publish-upgrade-notes job fails
- **AND** the image publishing job does not run
- **AND** the GitHub Release remains Draft

#### Scenario: Upgrade notes publication is retried
- **WHEN** the draft release description already includes the note marker for the same release
- **THEN** the notes publisher leaves it unchanged instead of duplicating the notice

## ADDED Requirements

### Requirement: Public releases require verified paired images
The release pipeline SHALL create only draft GitHub Releases until both backend and frontend images have been built from the same release tag, pushed and verified by digest. Exact version tags SHALL not be repointed to different digests. Mutable aliases SHALL move only after both verified exact version tags exist, and SHALL never move for prereleases. Public release publication SHALL be the final step.

#### Scenario: One image build or Registry push fails
- **WHEN** a candidate image cannot be built or pushed
- **THEN** no stable alias is advanced
- **AND** the GitHub Release remains Draft

#### Scenario: Both images are ready
- **WHEN** both staged digests resolve and both exact version tags point to those digests
- **THEN** stable aliases MAY advance
- **AND** the public GitHub Release is published only after all required steps succeed

#### Scenario: Upgrade image digest differs on retry
- **WHEN** an existing exact version tag points to a different digest
- **THEN** the release attempt fails without overwriting that tag
- **AND** the draft remains unpublished pending manual recovery

#### Scenario: Alias update or final release publication fails
- **WHEN** an alias push or public release edit fails
- **THEN** the pipeline attempts to restore previously recorded alias digests
- **AND** the GitHub Release remains Draft
- **AND** operators receive recovery instructions for aliases that cannot be rolled back

#### Scenario: Retry a partial draft release
- **WHEN** an operator dispatches a retry with an existing draft SemVer tag on main
- **THEN** the workflow validates notes and both images again without creating a new Release Please release
- **AND** only identical existing version digests are accepted

