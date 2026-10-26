# Locking Down the Supabase Data API

Supabase exposes every table in the `public` schema through its Data API (PostgREST and GraphQL) at `https://<project-ref>.supabase.co/rest/v1/<table>`. Access is controlled by two things:

- **Grants** to the `anon` and `authenticated` roles. Anyone holding the `anon` key, which is designed to be public, acts as `anon`.
- **Row-level security (RLS).** When RLS is on and no policy matches, the API returns no rows.

The app does **not** use the Data API. It connects to Postgres directly as the table owner, and RLS doesn't apply to the owner. So the API roles can lose all access without breaking anything.

The target state:

| Table | `anon` / `authenticated` access |
|---|---|
| `portfolios` | None: no grants, RLS on, no policies |
| `keepalive_heartbeat` | `anon` may read and upsert row `id = 1` only; this table holds only a timestamp |
| Anything else in `public` | None, unless deliberately exposed |

Run every SQL block below in the Supabase dashboard: **SQL Editor → New query → paste → Run**. Each block is safe to run more than once.

---

## Step 1: Audit what is exposed now

Paste this and run it. Keep the result to compare against at the end.

```sql
SELECT c.relname                                         AS table_name,
       c.relkind                                         AS kind,  -- r = table, v = view
       c.relrowsecurity                                  AS rls_on,
       has_table_privilege('anon', c.oid, 'SELECT')      AS anon_read,
       has_table_privilege('anon', c.oid, 'INSERT')      AS anon_insert,
       has_table_privilege('anon', c.oid, 'UPDATE')      AS anon_update,
       has_table_privilege('anon', c.oid, 'DELETE')      AS anon_delete,
       has_table_privilege('authenticated', c.oid, 'SELECT') AS auth_read
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind IN ('r', 'v', 'm', 'p')
ORDER BY c.relname;
```

Then list any existing policies, because a leftover permissive policy (e.g. "Enable read access for all users") would reopen a table:

```sql
SELECT tablename, policyname, roles, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
```

**Optional: confirm the leak from outside.** In PowerShell, using your project URL and `anon` key (Project Settings → API):

```powershell
$url = "https://<project-ref>.supabase.co"
$key = "<anon key>"
curl.exe -s "$url/rest/v1/portfolios?select=user_id,name&limit=3" -H "apikey: $key" -H "Authorization: Bearer $key"
```

If this prints portfolio rows, the data is currently public. An empty `[]` means RLS is on but the grants are still there.

---

## Step 2: Lock down `portfolios`

```sql
ALTER TABLE public.portfolios ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE    public.portfolios        FROM anon, authenticated;
REVOKE ALL ON SEQUENCE public.portfolios_id_seq FROM anon, authenticated;
```

If Step 1 listed any policies on `portfolios`, drop each one:

```sql
DROP POLICY IF EXISTS "<policy name from step 1>" ON public.portfolios;
```

`service_role` keeps access. Its key is secret and should never leave a server.

---

## Step 3: Lock down `keepalive_heartbeat`

This table was created before the Oct 30, 2026 change, so it probably still has the old automatic `ALL` grants. Reduce them to exactly what the keepalive workflow needs:

```sql
REVOKE ALL ON TABLE public.keepalive_heartbeat FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON TABLE public.keepalive_heartbeat TO anon;

ALTER TABLE public.keepalive_heartbeat ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS keepalive_anon ON public.keepalive_heartbeat;
CREATE POLICY keepalive_anon ON public.keepalive_heartbeat
    FOR ALL TO anon
    USING (id = 1)
    WITH CHECK (id = 1);
```

If Step 1 listed any **other** policies on `keepalive_heartbeat`, drop them as in Step 2.

---

## Step 4: Lock down any other tables

If Step 1 listed tables besides those two with `anon_read` or `auth_read` set to `true`, run this for each one (replace `my_table`):

```sql
ALTER TABLE public.my_table ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.my_table FROM anon, authenticated;
```

For a **view**, skip the `ALTER TABLE` line and run only the `REVOKE`. Views ignore the RLS of the tables underneath them by default, so revoking the grant is what protects them.

---

## Step 5: Stop new tables from being exposed

Since Oct 30, 2026, Supabase no longer grants API access to new `public` tables automatically. To make this hold regardless of platform defaults, remove the default grants for tables you create yourself (from the SQL editor or the app):

```sql
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE ALL ON TABLES    FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE ALL ON SEQUENCES FROM anon, authenticated;
```

From now on, a table is reachable through the API only if you write an explicit `GRANT` for it.

---

## Step 6: Verify

1. **Re-run the Step 1 audit.** Every row should have `rls_on = true`. Only `keepalive_heartbeat` should show `true` for `anon_read`, `anon_insert` and `anon_update`. `anon_delete` and `auth_read` should be `false` everywhere.
2. **Re-run the PowerShell `curl.exe` check.** It should now return `permission denied for table portfolios` (code `42501`) instead of rows.
3. **Check that the keepalive still works.** In GitHub, open **Actions → Supabase keepalive → Run workflow**. Both steps should pass.
4. **Check that the app still works.** Log in to the deployed app and load, save and delete a portfolio.
5. **Check the Security Advisor.** In Supabase, open **Advisors → Security Advisor**. There should be no "RLS Disabled in Public" or "Policy Exists RLS Disabled" errors.

---

## Step 7: Keep it locked

`PgPortfolioStore` re-applies the Step 2 lockdown every time the app starts (`_LOCK_DOWN` in `src/portfolio_simulator/services/pg_portfolio_store.py`). If the table is ever recreated or someone re-grants access, the next app restart closes it again. Push to `main` to deploy this.

When you add a new table in the future:

- **The app reads it directly (the usual case):** create it with `ENABLE ROW LEVEL SECURITY` and no grants to `anon` or `authenticated`.
- **It genuinely must be reachable with the `anon` key:** grant only the needed privileges and add a narrow RLS policy, as in Step 3.
