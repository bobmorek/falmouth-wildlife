# Falmouth Bay Wildlife Log

A lightweight, single-page citizen-science app for logging marine wildlife
sightings around Falmouth Bay and the wider Cornish / South-West England coast.
Drop a pin on the map, pick the species you spotted, and the app automatically
captures the weather conditions at that location and time before saving the
record to a [Supabase](https://supabase.com) database.

The whole app is a single `index.html` file — no build step, no framework.

## Features

- **Interactive map** (Leaflet + CARTO dark basemap) centred on Falmouth Bay.
- **Two-level species picker** grouped into dolphins & porpoise, whales,
  seabirds, and other marine life, with hand-drawn line icons and optional
  photo thumbnails.
- **Location capture** by tapping the map to drop a pin or using your device's
  current GPS location.
- **Automatic weather** at the sighting location and time via the free
  [Open-Meteo](https://open-meteo.com) API (air temp, wind speed/direction,
  cloud cover, pressure, conditions). No API key required.
- **Live sightings map** — every saved record is shown as a marker with a popup
  showing the species, count, date, observer, weather and notes.
- **Running stats** for total sightings, distinct species, and how many you've
  logged from this device.

## Quick start

1. Open `index.html` in a browser, or host the file on any static host
   (GitHub Pages, Netlify, Cloudflare Pages, etc.).
2. The first time you run it, paste your Supabase **Project URL** and
   **anon / publishable key** into the connect dialog. These are stored in the
   browser's `localStorage` so you only need to enter them once.

   Alternatively, hard-code them in the `CONFIG` block near the top of the
   `<script>` in `index.html`:

   ```js
   const CONFIG = {
     SUPABASE_URL: "https://YOUR-PROJECT.supabase.co",
     SUPABASE_KEY: "sb_publishable_… or eyJ…"
   };
   ```

## Supabase setup

1. Create a free project at [supabase.com](https://supabase.com).
2. In the **SQL Editor**, create the `sightings` table:

   ```sql
   create table public.sightings (
     id          bigint generated always as identity primary key,
     created_at  timestamptz not null default now(),
     species     text not null,
     count       integer not null default 1,
     lat         double precision not null,
     lng         double precision not null,
     notes       text,
     observer    text,
     weather     jsonb
   );
   ```

3. Enable **Row Level Security** and add policies so the public anon key can
   read and insert sightings (this is a public citizen-science log):

   ```sql
   alter table public.sightings enable row level security;

   create policy "Anyone can read sightings"
     on public.sightings for select
     using (true);

   create policy "Anyone can log a sighting"
     on public.sightings for insert
     with check (true);
   ```

4. Copy your **Project URL** and **anon / publishable key** from
   *Project Settings → API* and use them as described in Quick start above.

## Species photos (optional)

Species rows and map popups will look for a photo at `img/<species_key>.jpg`
(for example `img/common_dolphin.jpg`). If the image is missing, the app falls
back to the built-in line icon, so photos are entirely optional. The species
keys are defined in the `CATEGORIES` array in `index.html`.

## Tech

- [Leaflet 1.9.4](https://leafletjs.com) for the map
- [Supabase JS v2](https://supabase.com/docs/reference/javascript) for storage
- [Open-Meteo](https://open-meteo.com) for weather (no key needed)
- Plain HTML, CSS and vanilla JavaScript — no build tooling

## Privacy & notes

- Supabase URL/key and your local sighting count are stored in `localStorage`.
- The anon/publishable key is designed to be exposed in client-side code;
  access is controlled by the Row Level Security policies above.
- Weather requests are sent to Open-Meteo with the pin's coordinates.
