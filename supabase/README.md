# DietLens Supabase

This directory contains the database migration and transaction boundary for the hosted backend. It is intentionally separate from the existing SQLite migrations so local CLI tests remain deterministic.

1. Create a Supabase project.
2. Install the Supabase CLI and run `supabase login`.
3. From the repository root run `supabase link --project-ref <project-ref>`.
4. Review `migrations/0001_dietlens_core.sql`, `migrations/005_planning.sql`, and `migrations/006_meal_records.sql`, then run `supabase db push`.
5. Keep the publishable key in the browser and the secret/service-role key only in the Python server. Never commit either key. For the transactional Python Repository, use the direct `SUPABASE_DB_URL` connection string from the Connect dialog; do not substitute a browser key.

The profile confirmation function is an atomic database boundary. The server must still validate the authenticated user's ownership and operation parameters before calling it. Plan, shopping-list, inventory, and actual meal rows are separate objects; confirming a plan never creates an actual meal record. Other Harness writes will move behind equivalent functions as each vertical slice is migrated.
