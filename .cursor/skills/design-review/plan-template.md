# Design Review Report and Plan Template

Fill every section. Delete a section only if it is genuinely empty and say so in one line ("No P0 findings.").

```markdown
# Design review: <target name>

**Scope**: <files / feature / diff reviewed>  (<n> files, <m> functions/components)
**Baseline**: project-conventions.md + siblings <list 2–4 sibling files consulted>
**Metrics**: <one-line summary from inventory.py: largest file, longest function, cycles, naming violations, untested modules>

## Summary

<Two to four sentences: overall design health, the one or two most important problems, and whether the code fits the existing architecture.>

## What is well designed

- <Concrete strength worth preserving, with location>
- ...

## Findings

| # | Sev | Area | Location | Finding | Effort | Risk |
|---|-----|------|----------|---------|--------|------|
| 1 | P0 | Coupling | `services/api/app/x.py:12-40` | <one line> | M | High |
| 2 | P1 | Naming | `apps/mobile/src/utils/y.ts` | <one line> | S | Low |

### Finding 1: <title>
- **Observed**: <what the code does, with a short code reference>
- **Baseline**: <what siblings / conventions do, with a reference>
- **Why it matters**: <maintainability, defect risk, performance, security>
- **Recommendation**: <concrete change: new module name, signature, pattern to copy from>
- **Alternatives** (only if materially different options exist): <option B and why A is recommended>

### Finding 2: ...

## Cross-cutting observations

- <Architecture-flow deviations, hidden shared concepts, doc drift, security boundary notes>

## Remediation plan

Phases are independently shippable; each ends with passing tests.

### Phase 1: <name>  (findings #, #)  — effort <S/M/L>, risk <Low/Med/High>
1. <step>
2. <step>
Verify: `<test command(s)>`; re-run `inventory.py` and confirm <metric> improves.

### Phase 2: ...

### Deferred / not recommended
- <Finding # and why it is left as is>

## Open questions for you
- <Decision the user must make before a phase can start, if any>

---
Reply with the phases to proceed with (e.g. "1 and 2", or "all"), or ask for changes to the plan.
```

Rules for filling it in:

- Severity, effort, and risk must be present for every finding.
- Locations use `path:startLine-endLine` and point at the primary occurrence; list secondary occurrences in the body.
- Recommendations name the sibling to copy from when one exists.
- Keep the table to one line per finding; detail goes in the numbered sections.
- The final line is always the call to action; the agent stops after it.
