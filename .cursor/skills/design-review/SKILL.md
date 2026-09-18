---
name: design-review
description: Reviews the feature design of targeted code (files, folders, modules, or a diff) against clean-design principles, the application's existing architecture, and its shared design and naming conventions, then produces a prioritized remediation plan for the user to approve. Use when the user asks for a design review, architecture review, code-quality or maintainability assessment, "does this follow our conventions", refactor suggestions, or asks to evaluate how a feature is structured.
---

# Design Review

Evaluate targeted code for design quality and architectural fit, then present a remediation plan. Do not modify code until the user approves the plan.

## Workflow

Copy and track:

```
Design review:
- [ ] 1. Fix the target scope
- [ ] 2. Build the architecture baseline
- [ ] 3. Run the inventory script
- [ ] 4. Evaluate each component
- [ ] 5. Cross-cutting analysis
- [ ] 6. Score, prioritize, and write the plan
- [ ] 7. Present the plan and stop
- [ ] 8. (After approval) implement in phases with verification
```

### 1. Fix the target scope

Resolve what "targeted code" means, in this order of precedence:
- Paths, files, or symbols the user named.
- An open file or a selection, if that is what they are pointing at.
- `git diff` (uncommitted or branch changes) if they said "my changes", "this PR", "the diff".
- The feature slice if they named a feature: follow the call graph from the entry point (route, screen, command) through every module it touches, on both sides of the API boundary when the feature crosses it.

List the concrete files that are in scope and the files that are adjacent (callers, callees, tests). Adjacent files are read for context but only flagged when the target depends on their design.

### 2. Build the architecture baseline

The review compares the target against how the *rest* of the application is built, not against abstract ideals alone.

1. Read [project-conventions.md](project-conventions.md). It captures the layering, naming, and shared patterns of this repo.
2. Skim `README.md`, `docs/architecture.md`, and any `AGENTS.md` / `.cursor/rules` for changes the conventions file has not caught up with.
3. For each target file, open two or three *sibling* files that play the same role (another route handler, another store, another provider) and note the patterns they share: file layout, export shape, error handling, naming, where configuration and constants live, how tests are organized.
4. If the baseline you observe contradicts `project-conventions.md`, treat the code as the source of truth for the review and flag the doc drift as a finding.

### 3. Run the inventory script

The script gives objective metrics so the review is not only opinion. Execute it, do not read it:

```bash
python .cursor/skills/design-review/scripts/inventory.py <target paths...>
python .cursor/skills/design-review/scripts/inventory.py <target paths...> --json   # machine-readable
```

It reports, per target: file and function/component sizes, branch-complexity hotspots, internal import graph with fan-in and cycles, naming-convention violations (Python snake_case / PascalCase, TypeScript camelCase / PascalCase components), same-named units defined in more than one file (duplication leads, including across the API/app boundary when both are passed), and modules with no matching test file. Python stdlib only, no installs required. Treat its output as leads to verify by reading the code, not as findings by themselves.

### 4. Evaluate each component

For every file (and for every substantive class, function, component, hook, or store inside it), work through [checklists.md](checklists.md). The checklist covers:

- **Responsibility and cohesion**: one reason to change, no god modules, no utility dumping grounds.
- **Coupling and dependency direction**: layers depend inward, no cycles, no reaching across the API boundary.
- **Abstraction fit**: interfaces match the existing seams (e.g. the provider `Protocol` pattern), no speculative generality, no leaky abstractions.
- **Data modelling and contracts**: types/models live in the shared place, wire field naming is consistent, validation happens at the boundary.
- **Error handling and resilience**: failures mapped to the same status codes and error shapes as siblings, no swallowed exceptions, timeouts and limits where the siblings have them.
- **Efficiency**: unnecessary sequential awaits, repeated work that siblings cache, N+1 fetches, heavy work on render paths, unbounded growth.
- **Naming and conventions**: file, symbol, route, and field names match the baseline; terminology matches the domain glossary (sloka, verse, version, script, fingerprint).
- **Testability and tests**: pure logic separated from I/O, seams mockable in the same way siblings mock them, tests exist and test behaviour rather than implementation.
- **Duplication**: logic that already exists elsewhere in the repo (search for it before concluding it is new).
- **Dead or unused code**: unused exports, unreachable branches, stale flags.

Record each issue as a finding with: location, what the code does, what the baseline does, why it matters, and the recommended change. Skip trivial style nits that a formatter handles.

### 5. Cross-cutting analysis

After the per-component pass, look at the target as a whole:

- Does the feature's shape match `docs/architecture.md` data flow? Any step added, skipped, or moved to the wrong side of the API?
- Are there hidden shared concepts (the same idea implemented twice with different names)?
- Would a new engineer find things where they expect to, given the sibling layout?
- Is anything in the target that should be a shared utility, or a shared utility that should be local?
- Security and trust boundaries: secrets stay server-side, `X-App-Key` enforcement, rate limits, input size caps, robots handling (see conventions file).

### 6. Score, prioritize, and write the plan

Rate each finding:

| Severity | Meaning |
|---|---|
| **P0 Blocker** | Breaks architecture rules, security boundary, or will cause defects |
| **P1 Should fix** | Violates conventions or clean-design principles in a way that hurts maintainability |
| **P2 Improvement** | Better design available, modest payoff |
| **P3 Nit** | Naming/readability polish |

Estimate effort per finding (S < 30 min, M ≤ half day, L > half day) and risk (does the change touch a public contract, persisted data, or many call sites?). Group related findings into phases so each phase is independently shippable and testable. Write the plan using [plan-template.md](plan-template.md).

### 7. Present the plan and stop

Output the report and plan to the user. Include the strengths of the code too, so the user can tell what to preserve. Then **stop and wait**. Do not start implementing. If the user asks to proceed, ask which phases (or accept "all").

### 8. After approval: implement with verification

For each approved phase:
1. Make the changes for that phase only.
2. Run the relevant tests: `pytest` in `services/api` for backend changes; `npm test` in `apps/mobile` for app changes; both when the API contract changed.
3. Re-run the inventory script on the same targets and confirm the metrics moved in the right direction.
4. Report what changed, test results, and anything discovered that should become a new finding.
5. If a convention was introduced or changed, propose an update to `project-conventions.md` (do not apply it silently).

## Judgement rules

- Prefer the repo's existing pattern over a textbook pattern. Consistency beats local optimality; flag the pattern itself as a separate finding if it is bad.
- One finding per root cause. If ten call sites share the same mistake, that is one finding with ten locations.
- Every recommendation must be concrete enough to implement without further design discussion: name the new module, the new signature, the sibling to copy from.
- When two acceptable designs exist and the difference is material, present both in the plan with a recommendation rather than choosing silently.
- Do not pad the report. If the code is well designed, say so and keep the plan short.

## Additional resources

- Detailed evaluation criteria: [checklists.md](checklists.md)
- Repository architecture and naming baseline: [project-conventions.md](project-conventions.md)
- Report and plan format: [plan-template.md](plan-template.md)
- Metrics script: `scripts/inventory.py`
