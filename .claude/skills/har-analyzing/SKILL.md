---
name: analyzing-har
description: HAR (HTTP Archive) analyzer for the Octopus Energy España integration. Parses a browser-captured HAR file, extracts GraphQL operations from calls to /api/graphql/kraken, and compares them against octopus_client.py — classifying each operation as New, Changed, or Known. Writes a prioritised markdown report to wiki/reports/. No code edits.
disable-model-invocation: false
---

# Analyzing HAR — GraphQL API Drift Report (skill)

The Octopus Energy España GraphQL API is undocumented and reverse-engineered. When the dashboard app updates, new operations appear, existing queries gain or lose fields, and response shapes change. You read a HAR file captured from a live browser session, compare it against the current integration code, and write a prioritised report — so the next developer knows exactly what to implement, update, or deprecate. You do **not** edit code.

## When to Use

- `/analyzing-har <path>` — analyze the given HAR file.
- `/analyzing-har` with no argument — ask the user for the HAR path.
- Invoke whenever a new HAR is captured from the Octopus Energy España dashboard to detect API drift.

## Inputs

| Input | Source |
|-------|--------|
| HAR file | User-supplied path (HAR 1.2 JSON format; `.har` extension) |
| Known operations | `custom_components/octopus_energy_es/api/octopus_client.py` |
| Report destination | `wiki/reports/YYYY-MM-DD-har-analysis.md` |

## Approach

### Step 1 — Parse the HAR

Read the HAR file as JSON. Navigate to `log.entries[]`. Validate it is HAR 1.2 by checking for `log.version` — if absent, proceed with best-effort parsing and note it in the report.

If the file cannot be parsed as JSON, stop and tell the user. If no entries exist, write a report that says so (AC8).

### Step 2 — Filter GraphQL entries

Keep only entries where **all** of:
- `request.method == "POST"`
- `request.url` matches `*/api/graphql/kraken`

Count the total entries and the GraphQL-only count; both go in the report summary.

### Step 3 — Extract operations

For each GraphQL entry:

1. **Request body** — read `request.postData.text`, parse as JSON. Extract:
   - `operationName` (string or null)
   - `query` (the full GraphQL query/mutation string)
   - `variables` (object or null)
   - If `operationName` is absent or null, derive the name from the first `query` or `mutation` keyword in the query string. If still indeterminate, label it `<anonymous>`.

2. **Response body** — read `response.content.text`. If `response.content.encoding == "base64"`, base64-decode it. If the original response was gzip-compressed, it may have been decoded by the browser before export — use the decoded text as-is (HAR 1.2 spec guarantees decoded content in `text`). Parse the decoded text as JSON. Extract `data` key names from the top level (AC9).

3. **Parse errors** — if any step throws, note `[PARSE ERROR: <entry url> — <reason>]` in the report and continue (AC7).

### Step 4 — Extract known operations from octopus_client.py

Read `custom_components/octopus_energy_es/api/octopus_client.py`.

Extract all operation names by scanning for:
- `mutation <Name>` or `query <Name>` patterns inside triple-quoted strings
- The operation name is the identifier immediately after `mutation` or `query`

For each known operation also extract the field list — the set of leaf field names inside the query/mutation body. This is needed for the Changed classification.

The current known operations (as of the last analysis) are listed below for reference, but always re-derive them from the live file:

| Operation | Method |
|-----------|--------|
| `obtainKrakenToken` | `_authenticate` |
| `getAccountNames` | `fetch_properties` |
| `AccountProperties` | `_fetch_property_id` |
| `getAccountMeasurements` | `_fetch_consumption_via_property` |
| `MeasurementsQuery` | `_fetch_consumption_via_account` |
| `AccountCreditsQuery` | `fetch_account_credits` |
| `PropertyWithAgreement` | `fetch_tariff_info` |
| `Agreement` | `fetch_tariff_info` |
| `AccountInfo` | `fetch_account_info` |
| `getDevices` | `fetch_devices` |
| *(anonymous)* | `fetch_billing` — `accountBillingInfo` root field |

### Step 5 — Classify each HAR operation

For each operation extracted in Step 3:

| Classification | Condition |
|----------------|-----------|
| **New** | Operation name not in the known set from Step 4 |
| **Changed** | Operation name matches a known operation, but the field set differs (additions or removals vs code) |
| **Known** | Operation name matches and field set is identical (or is a strict subset of the code's fields — the code may request more than the dashboard) |

Field comparison: extract leaf field names from both the HAR query string and the code query string. Ignore aliases (treat `aliasName: fieldName` as `fieldName`). Ignore argument names and variables — compare only selected fields.

Duplicate HAR calls for the same operation (e.g. multiple `getAccountMeasurements` calls with different variables): de-duplicate by operation name; note the variable differences in the report but count as one operation.

### Step 6 — Write the report

Write to `wiki/reports/YYYY-MM-DD-har-analysis.md` (use today's date; create the directory if absent).

**Report structure:**

```markdown
# HAR Analysis — YYYY-MM-DD

> **PII REMINDER**: This report was generated from a live browser session. It may contain account
> numbers, property IDs, CUPS codes, and other personal data. **Redact before committing to a
> public repository.**

## Summary

| Metric | Value |
|--------|-------|
| HAR file | `<filename>` |
| Total entries | N |
| GraphQL POST entries | N (to `octopusenergy.es/api/graphql/kraken`) |
| Known operations | N |
| **New operations** | **N** |
| Changed operations | N |

---

## New Operations

[One subsection per new operation, in priority order — high-impact first]

### `OperationName`

**Priority: High / Medium / Low** — [one-line rationale]

[full query text in a graphql code block]

**Variables:** `{ key: type, ... }` or "none"

**Response keys:** `data.<root>.<fields>` ...

**Integration opportunity:** [one paragraph on what this enables]

---

## Changed Operations

[One subsection per changed operation]

### `OperationName`

**Code location:** `octopus_client.py:<method>()`

| Field | In code | In HAR |
|-------|---------|--------|
| `fieldName` | ✓ | ✓ |
| `newField` | ✗ | ✓ **(new)** |
| `removedField` | ✓ | ✗ (removed from dashboard) |

**Impact:** [one paragraph]
**Recommended action:** [concrete next step]

---

## Known Operations (no change)

| Operation | Type | Integration method |
|-----------|------|--------------------|
| ... | ... | ... |

**Not seen in this HAR** (but exist in the integration): [list]

---

## Priority Action List

| Priority | Action | Effort |
|----------|--------|--------|
| 🔴 High | ... | ... |
| 🟡 Medium | ... | ... |
| 🟢 Low | ... | ... |
| ⏸ Deferred | ... | ... |
```

If no GraphQL entries were found, replace all sections after Summary with a single paragraph: "No GraphQL POST requests to `/api/graphql/kraken` were found in this HAR file." (AC8).

### Step 7 — Update wiki index

Append a one-line entry under a `## HAR Analysis Reports` heading in `wiki/index.md` (create the heading if absent):

```markdown
- [YYYY-MM-DD HAR Analysis](reports/YYYY-MM-DD-har-analysis.md) — N new ops, N changed
```

## Priority guidance

Assign priority to new operations using these signals:

| Signal | Priority |
|--------|----------|
| New sensor-worthy data (tariff fields, supply point status, invoice URLs) | 🔴 High |
| Fields that improve existing sensors or expose feature flags | 🟡 Medium |
| Account management / referrals / address metadata | 🟢 Low |
| Gas supply points (significant new feature) | ⏸ Deferred |

## PII awareness

HAR files from real sessions contain personally identifiable information:

| Field | PII type | Action |
|-------|----------|--------|
| `accountNumber` (`A-XXXXXXXX`) | Account ID | Note in banner |
| `propertyId` | Property ID | Note in banner |
| `cups` / CUPS codes (`ESXXXXXXXX`) | Supply point ID | Note in banner |
| `accountUserMeta.nif` | National ID number | **Never expose as HA sensor** |
| `viewer.email`, `viewer.mobile` | Contact info | Note in banner |

Always include the PII reminder banner (AC10). Never expand or reproduce raw values from the HAR in the report — reference field names only.

## Report quality bar

A good report is:

- **Actionable** — each New/Changed section ends with a concrete recommended action or an explicit "no action needed".
- **Complete** — every GraphQL operation in the HAR is accounted for in one of the three sections.
- **Prioritised** — the Priority Action List is ordered, not alphabetical. High-impact items come first.
- **Honest** — if a field comparison is ambiguous (fragments, aliases obscuring intent), say so rather than guessing the classification.

## Guardrails

- **No code edits.** This skill produces a report only; `@cmok` implements findings.
- **Do not reproduce PII.** Mention field names and note PII risk; never paste raw account numbers, CUPS codes, NIF, or similar values.
- **Classify conservatively.** If unsure whether a field change is intentional API drift or a dashboard quirk, classify as Changed and note the uncertainty.
- **De-duplicate first.** Multiple HAR calls for the same operation are one report entry.
- **No auto-commit.** Leave the report for the user to review and commit (OQ2 resolved: user decides).

## Memory

Read `.tlk/MEMORY.md` (L4) before starting. If the analysis reveals a durable fact about the Octopus Energy España API (a confirmed field removal, a new type, a consistent naming pattern), log it:

```bash
talaka/memory/tools/log.sh --type project "Octopus ES API: <fact>"
```
