# Compliance Report and Remediation Plan Template

Fill every section. Where a section is empty, say so in one line.

```markdown
# App Store compliance review: <scope>

**Scope**: <staged: N files | entire codebase | paths>  
**Guidelines checked against**: App Review Guidelines as of <date checked>, plus privacy manifest, App Privacy, ATS, export compliance requirements  
**Scanner**: BLOCKER n · REQUIRED n · VERIFY n · INFO n (confirmed by reading code: n kept, n dismissed)

## Verdict

<One paragraph: can this be submitted as-is? If not, the one or two things that would cause rejection.>

## Findings

| # | Sev | Guideline | Rule | Location | Finding | Effort |
|---|-----|-----------|------|----------|---------|--------|
| 1 | REQUIRED | 5.1.2(i) | AI-001 | `apps/mobile/app/(tabs)/index.tsx` | <one line> | M |

### Finding 1: <title>
- **Requirement**: <paraphrase of the guideline text>
- **Observed**: <what the code/config/doc does, with `path:line` references>
- **Risk**: <rejection at review | metadata rejection | processing failure | legal exposure>
- **Remediation**: <concrete change: files, components, config keys, copy text; sibling pattern to follow>
- **Also update**: <privacy policy section / App Privacy label / review notes affected>

## N/A confirmations

- <Rule> — N/A because <reason>; becomes applicable if <trigger>.

## Consistency check (code ↔ privacy policy ↔ store metadata)

- <Agreement or discrepancy, with locations>

## Remediation plan

### Phase 1: Blockers and rejections  (findings #…)  — effort <S/M/L>
1. <step>
Verify: `<test commands>`; re-run `compliance_scan.py <same scope>`; expected: finding gone.

### Phase 2: Required guideline items  (findings #…)
...

### Phase 3: Verifications needing a human  (findings #…)
- <Exact action: e.g. "Run `npx expo prebuild -p ios` in a scratch clone and confirm PrivacyInfo.xcprivacy lists NSPrivacyCollectedDataTypeSearchHistory">

## Pre-submission checklist (App Store Connect, outside the repo)
- [ ] Privacy policy URL = https://<host>/privacy (opens without login)
- [ ] App Privacy labels match the data table in project-profile.md
- [ ] Age rating questionnaire answered on the current tiers
- [ ] Review notes pasted from docs/app-store.md §5 and updated for this build
- [ ] Support URL and contact email live
- [ ] Screenshots from the submitted build
- [ ] Production env vars set on EAS (`EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_APP_KEY`)

---
Reply with the phases to proceed with (e.g. "1 and 2", or "all"), or ask for changes.
```

Rules:

- Every finding cites a guideline number or a named requirement (privacy manifest, ATS, export compliance).
- Dismissed scanner findings are listed in one line each with the reason, so the user can see what was ruled out.
- Phases end with the exact verification command and expected outcome.
- The pre-submission checklist is always included, even when there are no code findings.
- The agent stops after the call to action.
