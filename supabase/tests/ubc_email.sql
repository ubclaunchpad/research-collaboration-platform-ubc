-- Run in the Supabase SQL Editor after applying the migration.
-- Everything is rolled back at the end, so no users are left behind.
-- Expected result: the final NOTICE says "all UBC email checks passed".

begin;

do $$
declare
  good text[] := array[
    'a@ubc.ca', 'a@student.ubc.ca', 'a@alumni.ubc.ca', 'a@cs.ubc.ca', 'A@UBC.CA'
  ];
  bad text[] := array[
    'a@gmail.com', 'a@evilubc.ca', 'a@ubc.ca.evil.com', 'a@ubc.com',
    'x@evil.com@ubc.ca', 'a@', 'no-at-sign', ''
  ];
  e text;
begin
  foreach e in array good loop
    insert into auth.users (id, email) values (gen_random_uuid(), e);
  end loop;

  foreach e in array bad loop
    begin
      insert into auth.users (id, email) values (gen_random_uuid(), e);
      raise exception 'FAIL: % was accepted', e;
    exception when others then
      if sqlerrm like 'FAIL:%' then raise; end if;
    end;
  end loop;

  begin
    insert into auth.users (id, email) values (gen_random_uuid(), null);
    raise exception 'FAIL: null email was accepted';
  exception when others then
    if sqlerrm like 'FAIL:%' then raise; end if;
  end;

  -- changing an existing UBC user to a non-UBC address must fail
  begin
    update auth.users set email = 'a@gmail.com' where email = 'a@ubc.ca';
    raise exception 'FAIL: email change to gmail was accepted';
  exception when others then
    if sqlerrm like 'FAIL:%' then raise; end if;
  end;

  raise notice 'all UBC email checks passed';
end;
$$;

rollback;
