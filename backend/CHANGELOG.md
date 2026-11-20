# Changelog

## Unreleased

- Add Supabase Auth JWT verification (`app/auth.py`) and a `GET /me` endpoint that returns the logged-in user.
- Add database trigger restricting sign-ups to UBC email addresses (`supabase/migrations/`).
- Add researcher merge (`app/merge/`): per-field source priority, ORCID/email/name+department identity matching, a review list for low-confidence matches, and idempotent upserts. Includes the RES-25 sample data and a CLI to run the merge on it.

## 0.1.0 - 2026-10-03

- Initial project setup.
