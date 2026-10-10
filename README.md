# ZeroStreams

An automatically maintained M3U playlist of validated live HLS streams,
refreshed every **15 minutes**. ZeroStreams brings together clean event titles,
thumbnail artwork, clearly labeled alternate feeds, automatic mirror failover,
and an on-demand refresh button.

Compatible with VLC and IPTV players that support M3U playlists. Stream
availability changes between refreshes.

**[Open the M3U playlist](https://raw.githubusercontent.com/Zer0Spce/ZeroStreams/main/playlist.m3u)** ·
**[Refresh status](https://github.com/Zer0Spce/ZeroStreams/actions)** ·
**[Latest scan report](status.json)**

Paste the M3U link into VLC or an IPTV player. Artwork appears in players that
support `tvg-logo`; VLC may show the playlist without artwork.

## Titles and artwork

- Consistent league/category names and normalized matchup titles.
- Alternate URLs for an event labeled **Feed 1**, **Feed 2**, etc., with the
  broadcaster and language labels when available.
- Exact duplicate URLs removed. Different working mirror URLs are retained.
- Reused player pages and URLs shared across scheduled events labeled as shared
  feeds within their sport, rather than assigned to an older matchup.
- Included ZeroStreams category thumbnails for each sport.
- Stable `tvg-id`, `tvg-name`, `tvg-logo`, and `group-title` M3U attributes.
  Feed numbers can change as feeds become unavailable; IDs do not depend on them.

Example title for alternate feeds:
`NFL | Detroit Lions vs Carolina Panthers — Feed 1`

## Sources

RoxieStreams internal event links and current HLS domain lists are the only
stream source for `playlist.m3u`. Only live manifests with reachable media segments are included.

## Schedule

Runs **every 15 minutes**, at minutes **07, 22, 37, and 52 of every hour** (UTC and
Philippine time have the same minute offsets). GitHub may delay scheduled jobs.

Each run checks for changes. If the playlist is identical, it is not rewritten
and no refresh commit is created. New or removed feeds, changed playback URLs,
and changes to event titles or artwork trigger an update. Fresh check reports
remain available in each run's diagnostics artifact; the committed scan report
records the last published playlist update.

To refresh whenever you want:

1. Open **[Actions](https://github.com/Zer0Spce/ZeroStreams/actions/workflows/refresh.yml)**.
2. Select **Refresh live playlist** in the sidebar.
3. Click **Run workflow**, leave the branch as **main**, then click the green
   **Run workflow** button.
4. Wait for the run to show a green check, then reload the playlist in your player.

Manual and scheduled refreshes share one concurrency group, so they run one at
a time. A manual refresh does not alter the automatic schedule.

## Local usage

Python 3.12; no third-party runtime dependencies.

```sh
python -m unittest discover -s tests -v
python scraper.py
```

RoxieStreams failover tries `.info`, then `.biz`, then `.su`. A complete
successful discovery uses one mirror per refresh. Failed primary discoveries
are recorded in `roxie_attempts`; `roxie_source` records the chosen mirror.
Absolute links pointing at another RoxieStreams mirror are resolved onto the
chosen mirror. If every mirror fails, the existing playlist is retained.

Set `SOURCE_URL` to a new primary domain if necessary. Set `ROXIE_BACKUP_URLS`
to a comma-separated list to override backups. To reuse this project
in another repository, update `LOGO_BASE` in `metadata.py` to that repository's
Raw asset URL. Included PNG category thumbnails are committed assets and do
not require an image library at runtime.

## Validation and limits

The scraper checks HLS manifests, rejects ended/VOD playlists, follows master
playlists to media variants, and reads a small part of the latest media segment.
This is a reachability check, not confirmation of the match's actual video
content or an uninterrupted-playback guarantee.

VLC referrer/user-agent directives are included. Some players ignore these;
feeds requiring those headers may fail there. No DRM, authentication, or access
controls are bypassed. Use streams where you have permission to access them.

An incomplete RoxieStreams discovery fails the run and retains the last
successful playlist. A complete scan with no reachable streams writes an empty
playlist. Consult the scan report and Actions history for freshness and source
coverage. Public-repository schedules may be disabled after 60 days without
activity. Parser, live-manifest, deduplication, title, and image
behavior are covered by automated tests.
