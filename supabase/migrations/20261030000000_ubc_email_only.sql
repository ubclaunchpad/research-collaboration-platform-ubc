-- Only allow UBC emails (@ubc.ca and *.ubc.ca) to sign up.
-- Done in the database so it can't be skipped by calling the Supabase API directly.
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
