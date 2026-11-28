# Changelog

## Unreleased

- Add Supabase Auth JWT verification (`app/auth.py`) and a `GET /me` endpoint that returns the logged-in user.
- Add database trigger restricting sign-ups to UBC email addresses (`supabase/migrations/`).
- Add OpenAlex matcher (`app/openalex/`) that links each researcher to their OpenAlex author record and pulls papers, topics, keywords and co-authors; unsure matches are flagged for review.

## 0.1.0 - 2026-10-03

- Initial project setup.
