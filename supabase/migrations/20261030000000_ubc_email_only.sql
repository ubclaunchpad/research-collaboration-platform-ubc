-- Only UBC email addresses (@ubc.ca and any *.ubc.ca subdomain) may have an
-- account. Enforced here, not just in the frontend, because anyone can call
-- Supabase's sign-up endpoint directly.
--
-- To change the allowed endings, edit the condition in this function.
-- To undo: drop trigger enforce_ubc_email on auth.users;

create or replace function public.enforce_ubc_email()
returns trigger
language plpgsql
set search_path = ''
as $$
declare
  domain text := lower(split_part(coalesce(new.email, ''), '@', 2));
begin
  if domain = 'ubc.ca' or domain like '%.ubc.ca' then
    return new;
  end if;
  raise exception 'Only UBC email addresses (@ubc.ca and subdomains) are allowed';
end;
$$;

create trigger enforce_ubc_email
before insert or update of email on auth.users
for each row execute function public.enforce_ubc_email();
