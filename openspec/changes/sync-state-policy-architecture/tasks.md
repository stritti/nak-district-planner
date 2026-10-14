## 1. Baseline and decision record
- [ ] Add characterization tests for the sync-state behavior delivered by PR #375.
- [ ] Evaluate `python-statemachine` and `transitions` against domain-purity, typing, graphability, maintenance, and dependency footprint.
- [ ] Record the selected approach and rejection rationale for alternatives.

## 2. Domain policy
- [ ] Introduce entity-scoped field-authority definitions.
- [ ] Introduce declarative/validated sync transitions.
- [ ] Add explicit conflict-resolution commands and invalid-transition handling.
- [ ] Ensure changed-field classification happens before conflict escalation.

## 3. Aggregate integration
- [ ] Expose required PlanningSlot aggregate operations.
- [ ] Remove application paths that mutate EventInstance state outside aggregate validation.
- [ ] Keep provider-specific data outside the domain policy.

## 4. Verification
- [ ] Add transition matrix and edge-case tests.
- [ ] Add field-authority regression tests.
- [ ] Run focused and full backend tests, lint/type checks, and coverage >= 80%.
- [ ] Update architecture documentation if the selected state-machine mechanism changes the stable mental model.
