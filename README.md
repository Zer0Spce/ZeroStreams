# ZeroStreams — Standby Backup

> Private standby copy of [ZeroStreams](https://github.com/Zer0Spce/ZeroStreams).
> Automatic refresh is disabled here to avoid idle Actions-minute usage.
> The copied playlist and scan report are snapshots from the primary project.
> Use **Run workflow** for an authenticated manual refresh; private-repository runs consume Actions minutes.
> Raw playlist and thumbnail URLs require access while this repository is private.
> This copy has its own source files and assets and does not depend on the primary repository.

An automatically maintained M3U playlist of validated live HLS streams,
refreshed every **30 minutes**. ZeroStreams brings together clean event titles,
thumbnail artwork, clearly labeled alternate feeds, automatic mirror failover,
and an on-demand refresh button.

Compatible with VLC and IPTV players that support M3U playlists. Stream
availability changes between refreshes.

**[Open the M3U playlist](https://raw.githubusercontent.com/Zer0Spce/ZeroStreamsBAK/main/playlist.m3u)** ·
**[Refresh status](https://github.com/Zer0Spce/ZeroStreamsBAK/actions)** ·
**[Latest scan report](status.json)**

Paste the M3U link into VLC or an IPTV player. Artwork appears in players that
support `tvg-logo`; VLC may show the playlist without artwork.

## Titles and artwork

- Consistent league/category names and normalized matchup titles.
- Alternate URLs for an event labeled **Feed 1**, **Feed 2**, etc., with the
  broadcaster and language labels when available.
- Exact duplicate URLs removed. Different working mirror URLs are retained.
- URLs shared across unrelated events labeled as shared channels rather than
  arbitrarily assigned to one match.
- Real PPV event posters used for exact matching current events. Other entries
  receive the included ZeroStreams category thumbnails.
- Stable `tvg-id`, `tvg-name`, `tvg-logo`, and `group-title` M3U attributes.
  Feed numbers can change as feeds become unavailable; IDs do not depend on them.

Example title for alternate feeds:
`NFL | Detroit Lions vs Carolina Panthers — Feed 1`

## Sources

| Source | Discovery | Current playback support |
| --- | --- | --- |
| RoxieStreams | Internal event links and the site's current HLS domain list | Live HLS manifests with reachable media segments |
| PPV | Documented public catalogue API and public event details | Only directly published public HLS URLs, when supplied |

The [PPV API documentation](https://ppv.st/api) provides titles, posters,
schedule times, and player links. Current responses provide iframe players
and empty M3U8 fields. Those iframe URLs **are not M3U playback URLs** and are
excluded from this playlist. PPV metadata still enriches exact matching events.
The adapter will include public direct HLS URLs if the API supplies them and
live validation succeeds. PPV's player integrations are kept intact; the
scraper does not extract streams from its embedded players or use VIP links.

`ppv-catalog.json` lists current PPV events, artwork, and links to their original
player pages. `status.json` explicitly reports `embed-only`, partial API errors,
and the number of direct candidates. A PPV outage does not prevent the primary
RoxieStreams playlist from refreshing; category artwork remains available.

## Schedule

The primary project refreshes every 30 minutes. Automatic refresh is disabled
in this standby copy. Manual refresh is available using the steps below.

To refresh whenever you want:

1. Open **[Actions](https://github.com/Zer0Spce/ZeroStreamsBAK/actions/workflows/refresh.yml)**.
2. Select **Refresh live playlist** in the sidebar.
3. Click **Run workflow**, leave the branch as **main**, then click the green
   **Run workflow** button.
4. Wait for the run to show a green check, then reload the playlist in your player.

Manual refreshes run one at a time. The primary project's automatic schedule
is unchanged. Future code changes to the primary project are not automatically
synchronized into this snapshot.

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
content or an uninterrupted-playback guarantee. PPV metadata excludes future
and ended events unless they are marked as continuous channels.

VLC referrer/user-agent directives are included. Some players ignore these;
feeds requiring those headers may fail there. No DRM, authentication, or access
controls are bypassed. Use streams where you have permission to access them.

An incomplete RoxieStreams discovery fails the run and retains the last
successful playlist. A complete scan with no reachable streams writes an empty
playlist. Consult the scan report and Actions history for freshness and source
coverage. Public-repository schedules may be disabled after 60 days without
activity. Parser, live-manifest, timing, deduplication, title, image, and PPV
source-boundary behavior are covered by automated tests.
