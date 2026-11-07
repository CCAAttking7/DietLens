# DietLens Round 4.1 — Data Truth & Experience Closure

## Scope

This iteration closes cross-module data semantics found after Round 4. It keeps the existing Harness, Profile, planning, food adapters and review architecture.

## Closed issues

### Food source truth

`ingredients` and `allergens` are now considered known only when the adapter provides populated values, or an explicit `allergens_declared_absent: true` assertion. Missing, null, empty-string, whitespace-only and unverified empty arrays remain unknown. `assess_record()` returns `needs_confirmation` for those cases; a detected hard constraint remains `blocked`. The UI receives the same `unknown_fields` and does not promote them to a safe claim.

### Plan and actual quantity semantics

- `PlanItem.servings` is the planned meal serving count.
- `PlanItem.quantity` is the explicitly named main ingredient quantity and is nullable when no ingredient is supplied.
- `MealRecord.quantity` is actual eaten quantity and remains `None` until the user enters or confirms it.

Plan preview accepts a meal without an ingredient, shopping generation skips it, and saved-plan summaries label serving count and ingredient quantity separately. “按计划记录这一餐” carries meal and plan linkage but leaves actual quantity and unit blank.

The old JSON shape remains readable because `quantity` and `servings` retain their names; old values are not reinterpreted as actual intake. New writes use null for an omitted ingredient quantity rather than zero.

### Allergy unknown flow

Stopped tasks now expose `stopped_reason` to the web client. `allergies_unconfirmed` has an explicit explanation and opens the existing profile flow, where the user can leave the state unknown, confirm no known allergies, or specify terms. Other stop reasons retain distinct copy.

### Recommendation truth

The action UI no longer claims different effort levels, goal-aware ranking, or feedback-note learning that the deterministic generator does not implement. Soft dislikes only lower ranking; hard avoids and confirmed allergy terms remain safety filters. Feedback notes are stored for review and are not presented as an automatic future preference signal.

Each generated action now carries `selected_option`. Legacy actions without this field remain ungrouped for evidence-sensitive review rather than being guessed from the first context option.

### Review integrity

Review coverage counts only records with an explicit `plan_item_id`. Same-slot records without that link remain `same_slot`/待核对, and plan-outside records remain separate. The response exposes matched, unmatched, same-slot and unplanned counts. Repeated-barrier insights require the same explicit selected option and meal context.

## Verification

- Python: 236 passed.
- Frontend build: PASS.
- JavaScript syntax: PASS.
- Contrast: PASS.
- Playwright browser suite: PASS locally, including 35 route/viewport checks and no page errors.
- Supabase authenticated flow: BLOCKED because no secure authenticated fixture is available.
- Remote GitHub Actions: reported separately from local results; a hosted browser installation failure remains an environment limitation when present.

