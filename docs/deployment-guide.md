# Deployment Guide — Streamlit Community Cloud + Supabase

This guide walks through deploying the Portfolio Simulator as a 24/7 hosted app with user authentication and per-user portfolio storage.

**Stack:**
- **Hosting:** Streamlit Community Cloud (free)
- **Database:** Supabase PostgreSQL (free tier, 500MB)
- **Auth:** streamlit-authenticator (password-based whitelist)

---

## Prerequisites

- A GitHub account with this repo pushed to it
- Python 3.11+ installed locally (for generating password hashes)
- The `streamlit-authenticator` package installed locally:
  ```bash
  pip install streamlit-authenticator
  ```

---

## Step 1: Commit and push the code to GitHub

Make sure all changes are committed and pushed:

```bash
cd "C:/Users/mathi/Documents/Github repos/Portfolio-Simulator"
git add -A
git commit -m "your commit message"
git push origin main
```

---

## Step 2: Create a Supabase project (free database)

1. Go to https://supabase.com and click **Start your project** (sign up with GitHub if you don't have an account)
2. Click **New project**
3. Fill in:
   - **Project name**: `portfolio-simulator`
   - **Database password**: pick a strong password and **save it somewhere** — you'll need it in Step 4
   - **Region**: pick the closest to your users (e.g. `West EU (London)`)
4. Click **Create new project** — wait ~2 minutes for it to spin up

---

## Step 3: Create the portfolios table in Supabase

1. In your Supabase dashboard, click **SQL Editor** in the left sidebar
2. Click **New query**
3. Paste this exact SQL and click **Run**:

```sql
CREATE TABLE IF NOT EXISTS portfolios (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    data_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, name)
);

CREATE INDEX IF NOT EXISTS idx_portfolios_user ON portfolios(user_id);
```

You should see "Success. No rows returned." — that means the table was created.

---

## Step 4: Get your Supabase connection string

1. In Supabase, click **Project Settings** (gear icon, bottom of left sidebar)
2. Click **Database** in the left menu
3. Scroll to **Connection string** section
4. Select the **URI** tab
5. You'll see something like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.abcdefgh.supabase.co:5432/postgres
   ```
6. Replace `[YOUR-PASSWORD]` with the database password you chose in Step 2
7. **Copy this full string** — you'll need it in Step 6

---

## Step 5: Generate password hashes for your users

For each user you want to allow access, generate a bcrypt hash of their password. Run this in your terminal:

```bash
python -c "import streamlit_authenticator as stauth; print(stauth.Hasher.hash('the_password_here'))"
```

Replace `the_password_here` with the actual password. It will output a single hash like:

```
$2b$12$xK7Gq3Z...long hash...
```

Copy the full hash (starting with `$2b$12$...`). Do this for each user.

> **Note:** This uses the `streamlit-authenticator` v0.4+ API. Older versions used `stauth.Hasher([password]).generate()`, which no longer works.

---

## Step 6: Deploy on Streamlit Community Cloud

1. Go to https://share.streamlit.io
2. Click **Sign in** — use your GitHub account
3. Click **New app**
4. Fill in:
   - **Repository**: `mathieu-calvo/Portfolio-Simulator`
   - **Branch**: `main`
   - **Main file path**: `src/portfolio_simulator/ui/app.py`
5. Click **Advanced settings** before deploying
6. Set **Python version** to `3.11`
7. In the **Secrets** text box, paste the following (replacing the placeholder values with your real ones):

```toml
[credentials]
[credentials.usernames]

[credentials.usernames.mathieu]
email = "your-real-email@example.com"
name = "Mathieu"
password = "$2b$12$PASTE_THE_HASH_FROM_STEP_5_HERE"

[credentials.usernames.anotherperson]
email = "their-email@example.com"
name = "Another Person"
password = "$2b$12$THEIR_HASH_FROM_STEP_5_HERE"

[cookie]
name = "psim_auth"
key = "REPLACE_WITH_A_RANDOM_STRING"
expiry_days = 30

[database]
url = "postgresql://postgres:YOUR_PASSWORD@db.abcdefgh.supabase.co:5432/postgres"
```

**Important details:**
- Each `[credentials.usernames.xxx]` block is one allowed user. `xxx` is their login username
- The `[cookie] key` should be a random string — generate one with:
  ```bash
  python -c "import secrets; print(secrets.token_hex(16))"
  ```
- The `[database] url` is the connection string from Step 4

8. Click **Deploy!**

---

## Step 7: Verify it works

1. Wait 2-3 minutes for the app to build. You can watch the logs in the Streamlit Cloud dashboard
2. Once deployed, you'll get a URL like `https://portfolio-simulator-mathieu-calvo.streamlit.app`
3. Open it — you should see a **login screen**
4. Log in with the username (e.g. `mathieu`) and the **plaintext password** (not the hash)
5. Create and save a portfolio — it's now stored in Supabase
6. To verify isolation: log out, log in as a different user — they should see no portfolios

---

## Managing Users

### Adding a new user

1. Generate their password hash (see Step 5)
2. Go to your Streamlit Cloud dashboard → your app → **Settings** → **Secrets**
3. Add a new block:
   ```toml
   [credentials.usernames.newuser]
   email = "newuser@example.com"
   name = "New User"
   password = "$2b$12$THEIR_HASH_HERE"
   ```
4. Save — the app restarts automatically

### Removing a user

Delete their `[credentials.usernames.xxx]` block from secrets and save.

---

## Updating the App

Any push to `main` on GitHub auto-deploys:

```bash
git add -A
git commit -m "your change description"
git push origin main
```

The app will rebuild in ~2 minutes.

---

## Local Development

None of this affects local development. Running the app locally without any environment variables or secrets uses SQLite and skips authentication, exactly as before:

```bash
streamlit run src/portfolio_simulator/ui/app.py
```

To test authentication locally, create `.streamlit/secrets.toml` (gitignored) with the same format as the secrets above.

---

## Architecture Notes

- **Config switch:** The `database_url` setting controls whether SQLite (local) or PostgreSQL (cloud) is used. The `require_auth` setting controls whether the login screen appears. Both auto-detect from Streamlit secrets when present.
- **User isolation:** Every portfolio query includes a `WHERE user_id = ?` clause. Users cannot see each other's portfolios.
- **Market data cache:** Uses local SQLite regardless of deployment mode. On Streamlit Cloud this is ephemeral (resets on app restart) but rebuilds automatically from Yahoo Finance.
- **Sleep behavior:** Streamlit Cloud free tier apps sleep after ~15 minutes of inactivity and wake in ~30 seconds on the next visit.
