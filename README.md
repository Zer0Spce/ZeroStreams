# ZeroStreams

An automatically maintained M3U playlist of discovered public HLS stream URLs,
refreshed **10 times daily (Philippine Time, UTC+8)**. ZeroStreams brings together clean event titles,
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

- Consistent league/category names, normalized matchup titles, and NCAA event grouping.
- Known PPV event start times display in Philippine Standard Time (PHT, UTC+8), including the date.
- Alternate URLs for an event labeled **Feed 1**, **Feed 2**, etc., with the
  broadcaster and language labels when available.
- Exact duplicate URLs removed. Different working mirror URLs are retained.
- URLs shared across unrelated events labeled as shared channels rather than
  arbitrarily assigned to one match.
- Public PPV event posters used only for matching events; unreachable/broken posters
  automatically fall back to built-in ZeroStreams category thumbnails. No guessed event art.
- Events with no authoritative start timestamp do not show a fabricated time.
- Stable `tvg-id`, `tvg-name`, `tvg-logo`, and `group-title` M3U attributes.
  Feed numbers can change as feeds become unavailable; IDs do not depend on them.

Example title for alternate feeds:
`NFL | Detroit Lions vs Carolina Panthers — Feed 1`

## Sources

| Source | Discovery | Current playback support |
| --- | --- | --- |
| RoxieStreams | Internal event links and the site's current HLS domain list | Every directly discovered HLS URL (unverified) |
| PPV | Documented public catalogue API and public event details | Only directly published public HLS URLs, when supplied |

The [PPV API documentation](https://ppv.st/api) provides titles, posters,
schedule times, and player links. Current responses provide iframe players
and empty M3U8 fields. Those iframe URLs **are not M3U playback URLs** and are
excluded from this playlist. PPV metadata still enriches exact matching events.
The adapter will include public direct HLS URLs if the API supplies them and
the URL is publicly provided. PPV's player integrations are kept intact; the
scraper does not extract streams from its embedded players or use VIP links.

`ppv-catalog.json` lists current PPV events, artwork, and links to their original
player pages. `status.json` explicitly reports `embed-only`, partial API errors,
and the number of direct candidates. A PPV outage does not prevent the primary
RoxieStreams playlist from refreshing; category artwork remains available.

## Schedule

The primary project refreshes 10 times each day in Philippine Time (PHT, UTC+8):
12:00 AM, 4:00 AM, 6:00 AM, 7:00 AM, 8:00 AM, 10:00 AM,
12:00 PM, 3:00 PM, 6:00 PM, and 9:00 PM. Manual refresh is also available.

To refresh whenever you want:

1. Open **[Actions](https://github.com/Zer0Spce/ZeroStreams/actions/workflows/refresh.yml)**.
2. Select **Refresh live playlist** in the sidebar.
3. Click **Run workflow**, leave the branch as **main**, then click the green
   **Run workflow** button.
4. Wait for the run to show a green check, then reload the playlist in your player.

Manual refreshes run one at a time. Scheduled runs can be delayed by GitHub Actions. The published playlist retains
its previous successful contents when discovery fails.

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

The scraper publishes all directly discovered HLS candidates without testing their
manifest or media segments. Some links may be offline, expired, geo-restricted,
or not directly playable; inclusion is not proof that a stream is working.
The scan status exposes `validation_mode: discovery_only`, `published_urls`,
and `not_checked_urls` to make that distinction explicit. PPV metadata excludes future
and ended events unless they are marked as continuous channels.

VLC referrer/user-agent directives are included. Some players ignore these;
feeds requiring those headers may fail there. No DRM, authentication, or access
controls are bypassed. Use streams where you have permission to access them.

An incomplete RoxieStreams discovery fails the run and retains the last
published playlist. A scan with no discovered HLS candidates does not overwrite
the playlist. Consult the scan report and Actions history for freshness and source
coverage. Public-repository schedules may be disabled after 60 days without
activity. Parser, live-manifest, timing, deduplication, title, image, and PPV
source-boundary behavior are covered by automated tests.
