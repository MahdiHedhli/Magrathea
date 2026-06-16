# Implementation Plan: [FEATURE NAME]

**Spec**: [spec.md](spec.md) | **Status**: Draft

## Technical context
- **Language / runtime**: […]
- **Worker / model**: […]  (respect the model floors in `governance/model-limit-policy.md`)
- **Gate runner**: […]  (deterministic, exit-code only — Constitution I)
- **Dependencies**: [pinned; installed locally, never global]

## Constitution check
Confirm before writing tasks; re-confirm after design. Any relaxation of a
principle is a blocker (Constitution Governance).
- [ ] I Gate-first   [ ] II Escalate   [ ] III Governance outside worker scope
- [ ] IV Sandboxed worker   [ ] V Security model-floor   [ ] VI Two budgets
- [ ] VII Recovery by reattach   [ ] VIII Reproducible

## Architecture
[Components and how they connect. Diagram if useful.]

## Worker sandbox
- Writable dirs: […]   Off-limits: governance/, secrets, CI, infra (default)
- Tools: [default none; name only what a task needs]
- Sandbox mode: workspace-write (default)

## Project structure
[Where new code/specs/tests live.]

## Risks & mitigations
- [risk] → [mitigation]

## Verification
[How the gate proves this; where the smoketest is recorded.]
