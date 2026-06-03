# Falmouth Bay Wildlife Log

A public, no-login web app for logging marine wildlife sightings around Falmouth Bay.
Records species, count, location (pin or GPS), automatic weather conditions, and notes,
and builds a shared map everyone can see. Static site — host free on GitHub Pages,
data in a free Supabase project. No warnings, no install.

---

## 1. Create the database (Supabase, free, ~5 min)

1. Go to **supabase.com** → sign in → **New project**. Pick a name and region (London/EU is closest). Wait ~2 min for it to provision.
2. In the left sidebar open **SQL Editor** → **New query**, paste the block below, and click **Run**:

```sql
-- table
create table sightings (
  id          bigint generated always as identity primary key,
  created_at  timestamptz default now(),
  species     text not null,
  count       int  default 1,
  lat         double precision not null,
  lng         double precision not null,
  notes       text,
  observer    text,
  weather     jsonb
);

-- turn on row level security
alter table sightings enable row level security;

-- anyone may read all sightings
create policy "public read"
  on sightings for select
  to anon
  using (true);

-- anyone may add a sighting (but not edit/delete others')
create policy "public insert"
  on sightings for insert
  to anon
  with check (true);
```

This gives you exactly the behaviour you wanted: anyone can view and add sightings,
nobody can tamper with or delete existing ones.

3. Open **Project Settings → API** (or the **Connect** dialog).
   Copy two things:
   - **Project URL** — looks like `https://abcdxyz.supabase.co`
   - **anon / publishable key** — the public client key (safe to expose; it's protected by the RLS policies above)

---

## 2. Add your keys to the app

Open `index.html`, find the `CONFIG` block near the top of the `<script>`, and paste:

```js
const CONFIG = {
  SUPABASE_URL: "https://abcdxyz.supabase.co",
  SUPABASE_KEY: "sb_publishable_xxx_or_eyJ..."
};
```

(If you leave these blank, the app shows a one-time connect screen and stores the keys
in *your* browser only — handy for testing, but for the public site bake them into CONFIG
so every visitor connects automatically.)

---

## 3. Host on GitHub Pages (free, ~3 min)

1. Create a new GitHub repo, e.g. `falmouth-wildlife`.
2. Upload `index.html` (and this README) to it.
3. Repo **Settings → Pages** → **Source: Deploy from a branch** → branch `main`, folder `/ (root)` → **Save**.
4. After a minute your app is live at `https://<your-username>.github.io/falmouth-wildlife/`.

Share that link — visitors land straight on the map and form, no warnings, no sign-in.

---

## Notes & next steps

- **Species photos:** run `fetch_images.py` on your own machine once (`pip install pillow requests` then `python3 fetch_images.py`). It downloads a freely-licensed photo per species into an `img/` folder, resizes them to small thumbnails, and writes `CREDITS.md`. Drop `img/` and `CREDITS.md` into the repo next to `index.html`. Any species without a photo automatically shows a built-in line icon, so the app works with or without the folder.
- **Weather** comes from Open-Meteo, which needs no API key.
- **Cost:** Supabase free tier and GitHub Pages comfortably cover a community project like this.
- **Spam protection (optional):** if abuse ever becomes an issue, add Cloudflare Turnstile to the form, or restrict inserts with a lightweight Supabase Edge Function. Not needed to start.
- **Custom domain:** GitHub Pages supports custom domains under Settings → Pages if you ever want `wildlife.something.co.uk`.
- **Data export:** anytime, from Supabase **Table Editor → sightings → Export to CSV**.
