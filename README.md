# ZeroStreams

Live-event M3U playlist restored from the **October 5, 2026 absolute backup**.
The protected [ZeroStreamsBAK](https://github.com/Zer0Spce/ZeroStreamsBAK) repository remains unchanged.
Only the refresh schedule and unverified-stream publishing rule have been added.

**[M3U playlist](https://raw.githubusercontent.com/Zer0Spce/ZeroStreams/main/playlist.m3u)** ·
**[Manual refresh / Actions](https://github.com/Zer0Spce/ZeroStreams/actions/workflows/refresh.yml)** ·
**[Scan report](status.json)**

## Schedule — Philippine Time (UTC+8)

Refresh the playlist **10 times daily** at:

`00:00`, `04:00`, `06:00`, `07:00`, `08:00`, `10:00`, `12:00`, `15:00`, `18:00`, `21:00`.

GitHub Actions UTC cron: `0 0,2,4,7,10,13,16,20,22,23 * * *`.
GitHub's scheduled actions may start later than the specified minute.
The **Run workflow** manual refresh remains available.

## Stream discovery and unverified HLS

- Discover publicly exposed direct `.m3u8` sources from
  `roxiestreams.info`, with `.biz` and `.su` fallback mirrors, and directly
  published public HLS sources from the PPV event catalogue.
- **Publish discovered HLS candidates without playback checks.** Each
  playlist entry is explicitly labeled **Unverified**. A listed stream may be
  offline, expired, ended, or unavailable in your player.
- Keep the absolute build's event title normalization, duplicate-URL
  consolidation, individually numbered distinct feeds, PPV event posters,
  category-logo fallbacks, and IPTV player referrer/User-Agent hints.
- Do not extract iframe-only sources or bypass authentication, VIP,
  DRM, or access restrictions.
- On an incomplete or failed mirror discovery, keep the last successful
  playlist rather than replacing it with an incomplete result.

`status.json` includes `validation_mode: discovery_only`,
`unverified_urls`, and `published_urls`. `live_urls` remains zero because
playback is no longer verified.

## Local tests

Python 3.12; no third-party runtime dependencies.

```sh
python -m unittest discover -s tests -v
python scraper.py
```

Use only streams you have permission to access.
