---
name: app-store-compliance
description: Audits an Expo/React Native app and its backend against Apple App Store Review Guidelines and submission requirements (privacy policy, App Privacy labels, privacy manifests, purpose strings, ATS, export compliance, third-party AI data-sharing consent, IAP, Sign in with Apple, account deletion, third-party content, metadata) on either the staged git changes or the whole codebase, then produces a prioritized remediation plan. Use when the user asks about App Store compliance, review rejection risk, App Store readiness, Apple guidelines, TestFlight/submission prep, or whether a change is safe to ship to iOS.
---

# App Store Compliance Review

Determine whether targeted code meets Apple's requirements to be published on the App Store, and present a remediation plan. Do not change code until the user approves the plan.

## Workflow

```
Compliance review:
- [ ] 1. Fix the scope (staged vs. whole codebase vs. paths)
- [ ] 2. Load the rule set and the project profile
- [ ] 3. Run the scanner
- [ ] 4. Manual rule pass on the scope
- [ ] 5. Consistency pass: code vs. privacy policy vs. store metadata
- [ ] 6. Classify, plan, present, stop
- [ ] 7. (After approval) remediate, re-scan, re-verify
```

### 1. Fix the scope

- **Staged changes** ("my staged changes", "before I commit", "this commit"): scope is `git diff --cached --name-only`. Repo-wide configuration, dependency, and document checks still run because compliance is a property of the whole app; the per-file rules run only on staged files.
- **Entire codebase** ("is the app compliant", "ready for App Store", "audit the repo"): scope is the whole repository.
- **Explicit paths**: the named files/folders plus repo-wide checks.

When a staged change adds a dependency, permission, network call, storage key, or user-facing text, treat the whole feature it belongs to as in scope even if only part of it is staged.

### 2. Load the rule set and the project profile

Read [rules.md](rules.md) (guideline-by-guideline requirements and how each is checked) and [project-profile.md](project-profile.md) (which rules apply to this app, which are N/A and why, and the app-specific risk areas). The profile also lists what the previous review found so regressions are caught.

### 3. Run the scanner

Execute (do not read) the scanner. Standard library only.

```bash
python .cursor/skills/app-store-compliance/scripts/compliance_scan.py --staged
python .cursor/skills/app-store-compliance/scripts/compliance_scan.py --all
python .cursor/skills/app-store-compliance/scripts/compliance_scan.py apps/mobile/app services/api/app
# add --json for structured output; --no-global to skip repo-wide checks; exit code 2 when a BLOCKER exists
```

Findings carry a rule id (`CFG-`, `EAS-`, `DEP-`, `DOC-`, `API-`, `AI-`, `ACC-`, `SRC-`), a severity, a location, and the guideline reference. Every scanner finding must be confirmed by reading the code before it enters the report; the scanner is heuristic.

### 4. Manual rule pass

The scanner cannot judge content, flows, or metadata. For the scope, walk the **Manual** rows in `rules.md`. The ones that most often matter for this app:

- **5.1.2(i)** disclosure and explicit consent before user data goes to third parties, including third-party AI. Trace every path that sends user input off-device and confirm a disclosure precedes the first send.
- **5.2.2** third-party web content: attribution visible, no copied commentary/translations, robots respected, review notes prepared.
- **1.1.1** religious content presented respectfully; no ranking or disparaging of traditions; AI output cannot produce offensive text without a mitigation.
- **2.1** completeness: production build reaches a hosted API, no placeholder text, demo instructions in review notes, error states are graceful.
- **2.3** metadata accuracy: description, screenshots, and review notes describe exactly what the build does (including that meanings are AI-generated).
- **4.2 / 4.3(b)** more than a web wrapper and meaningfully different from existing apps; listing highlights the differentiators.
- **App Privacy labels** reflect every data type the code sends (search queries, URLs, IP in server logs) and every SDK.
- **Privacy manifest** covers app-level collected data types and any required-reason APIs.

### 5. Consistency pass

Three artefacts must agree; disagreements are findings:

1. What the **code** actually sends, stores, and logs (client `api.*` calls, stores, backend logging and caching).
2. What the **privacy policy** (`docs/privacy.md`) and terms say.
3. What the **store metadata** (`docs/app-store.md`: labels, age rating, description, review notes) says.

A staged change that adds data flow without touching 2 and 3 is a REQUIRED finding even if the code itself is fine.

### 6. Classify, plan, present, stop

| Severity | Meaning |
|---|---|
| **BLOCKER** | Submission fails or rejection is certain (secret in bundle, dev client in production, missing bundle id, disabled ATS) |
| **REQUIRED** | A guideline requirement is unmet; expect rejection or a metadata rejection |
| **VERIFY** | Cannot be decided from code alone; a human must confirm (device test, App Store Connect setting, legal judgement) |
| **INFO** | Housekeeping before submission |

Write the report with [plan-template.md](plan-template.md): findings table, per-finding detail with the guideline text paraphrased and the concrete fix, then a phased remediation plan ordered BLOCKER → REQUIRED → VERIFY, followed by a pre-submission checklist of App Store Connect actions that live outside the repo. Present it and **stop**.

### 7. After approval

For each approved phase: make the change, run the tests (`pytest` in `services/api`, `npm test` and `npm run lint` in `apps/mobile`), re-run the scanner with the same scope, and confirm the finding is gone. Update `docs/privacy.md` / `docs/app-store.md` in the same phase when a data flow or label changes. Record any newly discovered convention in `project-profile.md` under "Review history".

## Judgement rules

- Cite the guideline number for every finding; if unsure of the number, say "guideline area" rather than inventing one.
- Prefer the smallest change that satisfies the rule and matches existing patterns (e.g. a disclosure sheet built with the existing `theme.ts` and `MeaningDisclaimer` style, not a new UI library).
- Rules that are N/A for this app (IAP, accounts, tracking, kids) stay N/A until a staged change makes them applicable; when it does, say so explicitly in the report.
- Apple revises the guidelines several times a year. If a rule seems to conflict with `rules.md`, check the [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) and the [developer news feed](https://developer.apple.com/news/) before deciding, and note the date checked in the report.
- Never present a VERIFY item as resolved; list the exact human action needed.

## Additional resources

- Rule catalogue with check methods: [rules.md](rules.md)
- App-specific applicability and risk profile: [project-profile.md](project-profile.md)
- Report and plan format: [plan-template.md](plan-template.md)
- Scanner: `scripts/compliance_scan.py`
