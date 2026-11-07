# DietLens Round 4 Change Log

| Area | Files | Change | Reason |
|---|---|---|---|
| Allergy semantics | `dietlens_mvp/models.py`, `profile_workflow.py`, `agent.py`, `tools.py`, `harness.py`, `api_server.py`, `cold_start.py`, `web/src/App.tsx`, `SettingsScreen.tsx` | Added persisted `unknown`/`none`/`specified` state, conservative legacy handling, explicit onboarding choice and truthful profile display | Prevent omitted allergies from becoming confirmed absence |
| Food safety | `dietlens_mvp/food.py`, `tests/test_food.py`, `tests/test_round4_truthfulness.py` | Missing ingredient/allergen source fields now require confirmation even without constraints | Do not claim safety from incomplete source data |
| Recommendations | `dietlens_mvp/tools.py`, `web/src/App.tsx` | Soft dislikes rank candidates only; add-on and micro-action copy states availability and name-only matching limits | Align recommendation claims with deterministic behavior |
| Review | `dietlens_mvp/comprehensive_review.py`, `web/src/components/WorkbenchScreen.tsx` | Precise Lens labels, one overview, evidence-grouped barriers, deterministic source label and nutrition limitation | Remove duplicated or unsupported interpretations |
| Planning/shopping | `dietlens_mvp/planning.py`, `web/src/components/PlanScreen.tsx`, `ShoppingPanel.tsx` | Empty ingredient no longer falls back to meal name; shopping skips unknown ingredient mappings and explains exact-match scope | Avoid fake ingredient-level shopping data |
| Documentation | `docs/DietLens-Round-4-Product-Truthfulness-Report.md`, `docs/DietLens-Product-Positioning-and-Roadmap.md`, `docs/profile-workflow.md` | Added claim-to-capability matrix, roadmap comparison and state semantics | Make current capability boundaries independently reviewable |

No backend schema, authentication, or API contract outside the additive profile payload was changed.
