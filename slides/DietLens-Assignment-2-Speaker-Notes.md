# DietLens — Assignment 2 speaker notes

This deck is designed for a six-minute progress presentation. The slides use English for the course deliverable; the notes below give a compact Chinese delivery script. Aim for 40–55 seconds per slide.

## 1. From meal choice to trusted reflection

DietLens is not presented as a complete calorie tracker. Our short-term product definition is a lightweight, user-controlled meal decision and reflection companion. The design connects the current meal, a confirmed decision, what was actually eaten, and later reflection. The screenshot is from the running product and shows the current meal composer.

## 2. Make every meal decision traceable

Since Part I, the main change is a shift from a generic AI assistant to a bounded workflow. We made unknown information explicit, separated plans from actual meals, and constrained the model to interpretation rather than safety decisions or writes. These changes make later review understandable instead of reconstructing intent from ambiguous data.

## 3. The architecture makes trust a system property

Four decisions matter most. The Harness owns state, consent, idempotency and writes. Deterministic rules decide food safety states. Plan servings, ingredient quantity and actual intake are separate facts. Unknown allergy or source data stays unknown. Together, these prevent a plausible-looking answer from becoming an unsafe or misleading record.

## 4. One control plane, bounded intelligence

The browser handles interaction, drafts and route context. FastAPI validates the request and passes it to the Harness. The Harness orchestrates domain services for profile, food safety, planning, meals and review. The repository persists the result. An optional model provider can extract structured intent, but it cannot write data or declare a food safe.

## 5. Small runtime footprint, clear seams

The prototype can run locally with a React/Vite frontend, FastAPI backend and SQLite/WAL. Supabase is an explicit deployment path for hosted auth and Postgres rather than a hidden dependency. Food sources and model providers sit behind boundaries. This keeps the first implementation easy to test while preserving a credible path to deployment.

## 6. From user input to a confirmed fact

The interaction is a state transition: describe, interpret, check, offer, confirm, then reflect. Confirmation is the write boundary. Feedback becomes a separate record and can only support future personalization when a real signal is implemented. The model is deliberately denied three powers: writing, bypassing consent, and declaring safety.

## 7. Design decisions are explicit—and testable

We refined requirements where implementation exposed a semantic gap: allergy tri-state, single-day planning scope, three different quantity meanings, no nutrition inference, and explicit shopping coverage. The open issues are the assumptions for Part III prototypes: authenticated browser fixtures, ingredient-level allergen verification, seven-day planning, portion-aware nutrition and feedback signals. Our next step is to test those risks before increasing product claims.

## Closing sentence

DietLens is designed to be trustworthy because every important transition has a clear owner, a confirmation boundary, and a recoverable record.
