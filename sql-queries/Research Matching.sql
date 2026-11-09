-- Research matching platform: Supabase schema
-- Paste into Supabase Dashboard > SQL Editor > New query > Run.
-- Assumes a 384-dim embedding model (e.g. all-MiniLM-L6-v2, bge-small).
-- If you use another model, change every vector(384) below to its dimension.

-- 1. Extensions -------------------------------------------------------------
create extension if not exists vector with schema extensions;

-- 2. Enums ------------------------------------------------------------------
create type public.user_role as enum ('student', 'researcher', 'admin');

-- Faculty and department are TEXT instead of ENUM on purpose: the lists will
-- change as you add faculties, and altering enums is painful. Add a lookup
-- table later if you want strict values.

-- 3. users ------------------------------------------------------------------
-- One row per signed-up person. id matches Supabase Auth.
create table public.users (
  id    uuid primary key references auth.users (id) on delete cascade,
  email text not null unique,
  name  text,
  role  public.user_role not null default 'student'
);

-- 4. students ---------------------------------------------------------------
-- The table already exists (id int8, full_name text, department text,
-- interests text[]), so we ALTER it instead of creating it. Existing rows
-- and data are kept. "if not exists" makes this safe to re-run.
alter table public.students
  add column if not exists user_id         uuid unique references public.users (id) on delete cascade,
  add column if not exists faculty         text,
  add column if not exists program         text,
  add column if not exists year_of_study   int check (year_of_study between 1 and 10),
  add column if not exists goals           text,
  add column if not exists embedding       extensions.vector(384),
  add column if not exists embedding_model text,
  add column if not exists updated_at      timestamptz not null default now();

-- Note: user_id is nullable so the existing rows (Ana Lee, Sam Ortiz) stay
-- valid. Link them to a login later by setting user_id.
-- Note: interests stays text[]. When building the text to embed, join it:
--   array_to_string(interests, ', ')   e.g. "genomics, python"

-- 5. labs -------------------------------------------------------------------
create table public.labs (
  id                   bigint generated always as identity primary key,
  name                 text not null,
  department           text,
  description          text,
  website_url          text,
  source_url           text,
  principal_investigator text,
  accepting_students   boolean not null default false,
  last_crawled         timestamptz,
  embedding            extensions.vector(384),
  embedding_model      text
);

-- 6. researchers ------------------------------------------------------------
-- user_id is nullable: you can crawl researchers who have no account yet,
-- and link them when they sign up.
create table public.researchers (
  id                  bigint generated always as identity primary key,
  user_id             uuid unique references public.users (id) on delete set null,
  full_name           text not null,
  title               text,
  faculty             text,
  department          text,
  email               text,
  website             text,
  bio                 text,
  research_summary    text,
  accepting_students  boolean not null default false,
  last_crawled        timestamptz,
  embedding           extensions.vector(384),
  embedding_model     text
);

-- 7. researcher <-> lab (replaces the SET column) ---------------------------
create table public.researcher_labs (
  researcher_id bigint not null references public.researchers (id) on delete cascade,
  lab_id        bigint not null references public.labs (id) on delete cascade,
  primary key (researcher_id, lab_id)
);
create index on public.researcher_labs (lab_id);

-- 8. Vector indexes (cosine distance) ---------------------------------------
create index students_embedding_idx
  on public.students using hnsw (embedding extensions.vector_cosine_ops);
create index labs_embedding_idx
  on public.labs using hnsw (embedding extensions.vector_cosine_ops);
create index researchers_embedding_idx
  on public.researchers using hnsw (embedding extensions.vector_cosine_ops);

-- 9. Auto-create a users row when someone signs up --------------------------
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = ''
as $$
begin
  insert into public.users (id, email, name)
  values (new.id, new.email, new.raw_user_meta_data ->> 'name');
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- 10. Matching functions (call via supabase.rpc) ----------------------------
-- Pass in a student's embedding, get the closest labs that accept students.
create or replace function public.match_labs(
  query_embedding extensions.vector(384),
  match_count int default 10
)
returns table (id bigint, name text, description text, similarity float)
language sql stable
as $$
  select l.id, l.name, l.description,
         1 - (l.embedding <=> query_embedding) as similarity
  from public.labs l
  where l.accepting_students and l.embedding is not null
  order by l.embedding <=> query_embedding
  limit match_count;
$$;

create or replace function public.match_researchers(
  query_embedding extensions.vector(384),
  match_count int default 10
)
returns table (id bigint, full_name text, research_summary text, similarity float)
language sql stable
as $$
  select r.id, r.full_name, r.research_summary,
         1 - (r.embedding <=> query_embedding) as similarity
  from public.researchers r
  where r.accepting_students and r.embedding is not null
  order by r.embedding <=> query_embedding
  limit match_count;
$$;

-- 11. Row Level Security ----------------------------------------------------
alter table public.users          enable row level security;
alter table public.students       enable row level security;
alter table public.labs           enable row level security;
alter table public.researchers    enable row level security;
alter table public.researcher_labs enable row level security;

-- People can read and edit only their own user and student rows.
create policy "own user row" on public.users
  for all to authenticated
  using (id = auth.uid()) with check (id = auth.uid());

create policy "own student row" on public.students
  for all to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Labs, researchers and their links are readable by any signed-in user.
-- Writes happen with the service role key (your crawler), which bypasses RLS.
create policy "read labs" on public.labs
  for select to authenticated using (true);
create policy "read researchers" on public.researchers
  for select to authenticated using (true);
create policy "read researcher_labs" on public.researcher_labs
  for select to authenticated using (true);
