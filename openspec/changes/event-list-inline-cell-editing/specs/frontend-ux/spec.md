## ADDED Requirements

### Requirement: Accessible progressive editing in event tables
All tabular overview screens SHALL keep input controls hidden in read mode and provide visible keyboard focus, accessible cell/editor labels and announced save/errors when a cell is edited. Edit controls SHALL work with touch, mouse and keyboard and SHALL not depend exclusively on hovering.

#### Scenario: Keyboard-only edit
- **WHEN** a keyboard user focuses an editable cell and activates it with Enter
- **THEN** the editor becomes focused and announces its field label and current value

#### Scenario: Save feedback
- **WHEN** an inline cell change succeeds or fails
- **THEN** the interface communicates the result accessibly and preserves focus where practical

### Requirement: Application-wide table editing consistency
The SPA SHALL apply a common compact presentation, inline editor activation, keyboard navigation, save/cancel and error-feedback pattern to all table overviews with editable data, regardless of their underlying resource. Editing SHALL only be offered for authorised mutable fields; navigation and explicit domain actions SHALL remain distinct.

#### Scenario: Consistent cross-screen interaction
- **WHEN** a user moves between two different overview tables with editable cells
- **THEN** the same gestures, keyboard shortcuts, active-cell indicators and error states are used in both screens

#### Scenario: Derived field
- **WHEN** a cell displays a computed or protected value
- **THEN** it remains compact and readable without suggesting that it can be edited
