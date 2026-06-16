# Feature Specification: [FEATURE NAME]

**Feature branch**: `[NNN-feature-name]`
**Status**: Draft
**Created**: [DATE]

## Summary
[One paragraph: what this delivers and why. No implementation detail.]

## User Scenarios & Testing
### Primary scenario
[As a <role>, I <do> so that <outcome>. Numbered happy-path steps.]

### Acceptance (the gate)
Every criterion MUST be deterministic and machine-checkable (Constitution I).
- **AC-1** [observable, exit-code-checkable outcome]
- **AC-2** […]

### Edge cases
- [boundary / failure / limit-hit behavior]

## Requirements
### Functional
- **FR-1** [testable capability] [NEEDS CLARIFICATION: … if ambiguous]
- **FR-2** […]

### Non-functional
- [performance, security, dependency, sandbox constraints]

## Out of scope
- [explicitly excluded]

## Review checklist
- [ ] Acceptance is deterministic and machine-checkable.
- [ ] No implementation detail in requirements.
- [ ] Every requirement maps to an acceptance criterion.
- [ ] No unresolved [NEEDS CLARIFICATION].
