## ADDED Requirements

### Requirement: Accessible progressive editing in event tables
The event overview SHALL keep input controls hidden in read mode and provide visible keyboard focus, accessible cell/editor labels and announced save/errors when a cell is edited. Edit controls SHALL work with touch, mouse and keyboard and SHALL not depend exclusively on hovering.

#### Scenario: Keyboard-only edit
- **WHEN** a keyboard user focuses an editable cell and activates it with Enter
- **THEN** the editor becomes focused and announces its field label and current value

#### Scenario: Save feedback
- **WHEN** an inline cell change succeeds or fails
- **THEN** the interface communicates the result accessibly and preserves focus where practical
