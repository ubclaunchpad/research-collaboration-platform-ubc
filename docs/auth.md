# Auth (for frontend)

Sign-up and login use Supabase Auth directly from the frontend. The backend only checks who is logged in.

- Only UBC emails work (`@ubc.ca` and subdomains like `@student.ubc.ca`).
- New users must click the link in the confirmation email before they can log in.

## Setup

```sh
cd frontend
npm install @supabase/supabase-js
```

Add to `frontend/.env`. Use the **publishable** key from Supabase (Settings > API Keys). Never put the `sb_secret_` key in the frontend.

```
VITE_SUPABASE_URL=https://mcntwsjcbfcbrkmgvsxg.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
```

Make one client and import it everywhere, for example `src/supabase.ts`:

```ts
import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY,
)
```

## Sign up

```ts
const { data, error } = await supabase.auth.signUp({ email, password })
```

If it works, no session is returned yet. Show something like "Check your email to confirm your account".

## Log in

```ts
const { data, error } = await supabase.auth.signInWithPassword({ email, password })
```

Logging in before confirming the email gives an error with the message `Email not confirmed`.

## Log out

```ts
await supabase.auth.signOut()
```

## Errors

Always check `error` first.

| What happened | What you get |
|---|---|
| Email not confirmed yet | `error.message` is `Email not confirmed` |
| Wrong email or password | `error.message` is `Invalid login credentials` |
| Not a UBC email | `error.message` is `Only UBC email addresses (@ubc.ca and subdomains) are allowed` (status 500) |

The status is a 500 even though it's the user's mistake, so check the email in the form **before** calling `signUp`. That way people get a clear message right away:

```ts
const isUbcEmail = (email: string) => {
  const domain = email.trim().toLowerCase().split('@')[1] ?? ''
  return domain === 'ubc.ca' || domain.endsWith('.ubc.ca')
}
```

This check is only for the message. The database rejects non-UBC emails either way.

## Calling the backend

Send the access token in the `Authorization` header:

```ts
const { data } = await supabase.auth.getSession()

const res = await fetch('http://localhost:8000/me', {
  headers: { Authorization: `Bearer ${data.session?.access_token}` },
})
```

`GET /me` returns `{ "id": "...", "email": "..." }`. Other protected routes work the same way.

| Status | Meaning |
|---|---|
| 200 | Logged in |
| 401 | No token, bad token, or expired. Send the user to the login page |
| 503 | Backend can't reach Supabase to check the token. Try again later |

The supabase client refreshes the token automatically, so call `getSession()` each time instead of saving the token yourself.

## Knowing if the user is logged in

```ts
supabase.auth.onAuthStateChange((event, session) => {
  // session is null when logged out
})
```

## Note: CORS

The backend doesn't allow requests from the frontend's address yet, so the browser will block `fetch` calls to it. Whoever first calls the backend from the frontend needs to add CORS to `backend/app/main.py` (or set up a proxy in `vite.config.ts`).
