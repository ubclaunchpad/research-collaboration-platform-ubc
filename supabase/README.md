# Connecting to the Research Matching Platform database

Our database runs on Supabase. This guide gets you from the email invite to running your first query from code. It takes about 10 minutes.

## What you need

- The invite email from Supabase
- Node.js 20.19 or newer (`node -v` to check), the same version the frontend needs
- This repo cloned on your computer

## Step 1: Join the Supabase organization

1. Open the invite email and click the link.
2. Create a Supabase account using the same email the invite was sent to.
3. You should land in the **Research Matching Platform** organization. Click the project to open it.
4. Turn on two-factor authentication: click your avatar (top right), then **Account preferences > Security**.

## Step 2 (optional): Look at the data in the dashboard

No code needed for this part.

1. In the left icon bar, click **Table Editor** to browse the tables.
2. Click **SQL Editor** (the `>_` icon) to run SQL. Try:

```sql
select s.full_name, o.title, a.status
from public.applications a
join public.students s on s.id = a.student_id
join public.opportunities o on o.id = a.opportunity_id;
```

### The tables

| Table | What it holds | Columns |
|---|---|---|
| `students` | Student profiles | `id`, `full_name`, `department`, `interests` (list of text) |
| `opportunities` | Research openings | `id`, `title`, `faculty_name`, `department`, `is_open` |
| `applications` | Who applied to what | `id`, `student_id`, `opportunity_id`, `status` |

## Step 3: Get your own secret key

1. In the project, click the **gear icon** (bottom of the left bar), then **API Keys**.
2. Under **Secret keys**, create a new key and name it after yourself, for example `backend-alex`.
3. Copy the value. It starts with `sb_secret_`.

## Step 4: Create your `.env` file

1. In the root folder of this repo, copy `.env.example` to a new file named exactly `.env`.
2. Replace the placeholder with your own key:

```bash
SUPABASE_URL=https://mcntwsjcbfcbrkmgvsxg.supabase.co
SUPABASE_SECRET_KEY=sb_secret_paste_your_key_here
```

3. Open `.gitignore` and check that it contains a line that says `.env`. If it doesn't, add it before you do anything else.

## Step 5: Connect and run your first query

Nothing to install. Node 20 has `fetch` built in and can read `.env` by itself, so we talk to Supabase's REST API directly.

In the `supabase/` folder, create a file named `supabase.mjs`. Every other file imports the connection from here.

```js
const url = process.env.SUPABASE_URL
const key = process.env.SUPABASE_SECRET_KEY

// path is the table name plus any query string, e.g. 'students?select=*'
export async function supabase(path, { method = 'GET', body } = {}) {
  const res = await fetch(`${url}/rest/v1/${path}`, {
    method,
    headers: {
      apikey: key,
      'Content-Type': 'application/json',
      Prefer: 'return=representation', // send back the rows that changed
    },
    body: body && JSON.stringify(body),
  })
  const text = await res.text()
  const json = text ? JSON.parse(text) : null
  return res.ok ? { data: json, error: null } : { data: null, error: json }
}
```

In the same folder, create a file named `example.mjs`:

```js
import { supabase } from './supabase.mjs'

const { data, error } = await supabase('students?select=*')

if (error) console.error(error)
else console.log(data)
```

Run it from the repo root:

```bash
node --env-file=.env supabase/example.mjs
```

You should see the list of students printed in your terminal.

## Common queries

Every call returns `{ data, error }`. Always check `error` first.

Filters go in the query string as `column=operator.value`. Common operators: `eq`, `neq`, `gt`, `lt`, `ilike` (case-insensitive match, `*` as wildcard), `in.(1,2,3)`. Full list: [Supabase REST API docs](https://supabase.com/docs/guides/api).

**Read specific columns with a filter**

```js
const { data, error } = await supabase('opportunities?select=title,faculty_name&is_open=eq.true')
```

**Read across related tables (a join)**

```js
const { data, error } = await supabase('applications?select=status,students(full_name),opportunities(title)')
```

**Add a row**

```js
const { data, error } = await supabase('students', {
  method: 'POST',
  body: { full_name: 'Test Student', department: 'Physics', interests: ['optics'] },
})
```

**Change a row**

```js
const { data, error } = await supabase('applications?id=eq.1', {
  method: 'PATCH',
  body: { status: 'reviewing' },
})
```

**Delete a row**

```js
const { error } = await supabase('students?id=eq.3', { method: 'DELETE' })
```

Always include a filter such as `?id=eq.1` on update and delete, so you only touch the rows you mean to.

## Rules for everyone

- **Never commit your `.env` file or paste your key** in chat, issues, or screenshots.
- **Only use the secret key in backend code.** Never in a web page or mobile app.
- **This is one shared database.** Anything you change, everyone sees. Don't drop or rename tables without telling the team.
- **If your key leaks,** delete it on the API Keys page right away, create a new one, and tell the project owner.

## Troubleshooting

| What you see | Likely cause | Fix |
|---|---|---|
| `.env: not found`, or `Failed to parse URL from undefined/rest/v1/...` | `.env` is missing, misnamed, not in the repo root, or you ran `node` from another folder | Check the file name and location, run from the repo root with `--env-file=.env` |
| `bad option: --env-file` | Node is older than 20.6 | Update Node (see "What you need") |
| `permission denied for table ...` (code 42501) | The table hasn't been opened up to the secret key | Ask the project owner to grant access to that table |
| Empty list `[]` when you expected rows | Your filter matches nothing | Check the filter values in the Table Editor |
| Requests time out or the project won't load | The project paused after a week without activity | Ask the project owner to restore it from the dashboard |
| `401 Unauthorized` | Wrong key, deleted key, or the key is being used in a browser | Copy the key again from the API Keys page; use it in backend code only |
