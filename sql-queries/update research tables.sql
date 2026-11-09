-- Migration 002: papers, researcher_papers, external_ids + provenance + upsert keys
-- Run AFTER schema.sql (migration 001). Safe to re-run: every statement is idempotent.
-- Matches ticket RES-5: researchers, labs, papers; researcher<->lab and
-- researcher<->paper joins; external_ids (ORCID, OpenAlex, Semantic Scholar).
--
-- Conventions used in this file
--   sources       text[]       which sources a record came from, e.g. {'openalex','lab_website'}
--   last_crawled  timestamptz  when the record was last fetched
--                              (labs and researchers already have this column from 001,
--                              so it is reused as the "fetched at" field everywhere)

-- 1. Provenance on existing tables -------------------------------------------
alter table public.labs
  add column if not exists sources text[] not null default '{}';

alter table public.researchers
  add column if not exists sources text[] not null default '{}';

alter table public.researcher_labs
  add column if not exists sources      text[] not null default '{}',
  add column if not exists last_crawled timestamptz;

-- 2. Upsert key for labs -----------------------------------------------------
-- A lab is identified by the page it was crawled from.
-- NULLs are allowed and never conflict. If this fails with a duplicate-key
-- error, you already have two labs with the same source_url: clean those first.
do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'labs_source_url_key'
  ) then
    alter table public.labs add constraint labs_source_url_key unique (source_url);
  end if;
end $$;

-- 3. papers ------------------------------------------------------------------
create table if not exists public.papers (
  id                   bigint generated always as identity primary key,
  doi                  text,
  openalex_id          text,
  semantic_scholar_id  text,
  title                text not null,
  abstract             text,
  publication_year     int,
  venue                text,
  url                  text,
  sources              text[] not null default '{}',
  last_crawled         timestamptz,
  embedding            extensions.vector(384),
  embedding_model      text,
  -- Store DOIs lowercase so "10.1/ABC" and "10.1/abc" cannot both exist.
  constraint papers_doi_lowercase check (doi = lower(doi)),
  -- Each id is unique, so you can upsert with ON CONFLICT on any of them.
  -- Postgres allows many NULLs in a unique column, so a paper with no DOI is fine.
  constraint papers_doi_key                 unique (doi),
  constraint papers_openalex_id_key         unique (openalex_id),
  constraint papers_semantic_scholar_id_key unique (semantic_scholar_id)
);

-- Embed title + abstract. Same model as the other tables so vectors are comparable.
create index if not exists papers_embedding_idx
  on public.papers using hnsw (embedding extensions.vector_cosine_ops);

-- 4. researcher <-> paper (many-to-many) -------------------------------------
create table if not exists public.researcher_papers (
  researcher_id    bigint not null references public.researchers (id) on delete cascade,
  paper_id         bigint not null references public.papers (id) on delete cascade,
  author_position  int,                       -- 1 = first author, optional
  sources          text[] not null default '{}',
  last_crawled     timestamptz,
  primary key (researcher_id, paper_id)
);
create index if not exists researcher_papers_paper_id_idx
  on public.researcher_papers (paper_id);

-- 5. external_ids (ORCID, OpenAlex, Semantic Scholar per researcher) ---------
create table if not exists public.external_ids (
  id             bigint generated always as identity primary key,
  researcher_id  bigint not null references public.researchers (id) on delete cascade,
  source         text not null
                 check (source in ('orcid', 'openalex', 'semantic_scholar')),
  external_id    text not null,
  last_crawled   timestamptz,
  -- Upsert key: one external id belongs to exactly one researcher. This is what
  -- stops the crawler creating the same OpenAlex author twice.
  constraint external_ids_source_external_id_key unique (source, external_id),
  -- A researcher has at most one id per source.
  constraint external_ids_researcher_source_key  unique (researcher_id, source)
);
create index if not exists external_ids_researcher_id_idx
  on public.external_ids (researcher_id);

-- 6. Matching function for papers --------------------------------------------
-- Returns the closest papers to a student's embedding, with the authors'
-- researcher ids so you can then look up who to contact.
create or replace function public.match_papers(
  query_embedding extensions.vector(384),
  match_count int default 10
)
returns table (id bigint, title text, abstract text, similarity float)
language sql stable
as $$
  select p.id, p.title, p.abstract,
         1 - (p.embedding <=> query_embedding) as similarity
  from public.papers p
  where p.embedding is not null
  order by p.embedding <=> query_embedding
  limit match_count;
$$;

-- 7. Row Level Security for the new tables -----------------------------------
alter table public.papers            enable row level security;
alter table public.researcher_papers enable row level security;
alter table public.external_ids      enable row level security;

-- Signed-in users can read. Writes come from the crawler via the service role key.
drop policy if exists "read papers" on public.papers;
create policy "read papers" on public.papers
  for select to authenticated using (true);

drop policy if exists "read researcher_papers" on public.researcher_papers;
create policy "read researcher_papers" on public.researcher_papers
  for select to authenticated using (true);

drop policy if exists "read external_ids" on public.external_ids;
create policy "read external_ids" on public.external_ids
  for select to authenticated using (true);

-- 8. Example upserts (for reference, not executed) ---------------------------
-- Papers, keyed on DOI:
--   insert into public.papers (doi, title, abstract, sources, last_crawled)
--   values ('10.1000/xyz123', 'Title', 'Abstract...', '{openalex}', now())
--   on conflict (doi) do update
--     set title = excluded.title,
--         abstract = excluded.abstract,
--         sources = (select array(select distinct unnest(papers.sources || excluded.sources))),
--         last_crawled = excluded.last_crawled;
--
-- Researcher identity, keyed on (source, external_id):
--   insert into public.external_ids (researcher_id, source, external_id, last_crawled)
--   values (1, 'openalex', 'A5023888391', now())
--   on conflict (source, external_id) do update
--     set last_crawled = excluded.last_crawled;
