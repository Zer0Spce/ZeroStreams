# ZeroStreams

An automatically maintained M3U playlist of validated live HLS streams,
targeting a refresh **about every 10 minutes**. ZeroStreams brings together clean event titles,
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

GitHub Actions **attempts a run every 5 minutes** (UTC minute 04, 09, 14,
19, 24, 29, 34, 39, 44, 49, 54, and 59). A successful refresh uploads a
small `playlist-refresh-heartbeat` artifact. Scheduled attempts **skip the
scraper when a successful scan finished less than 8 minutes earlier**.
This provides a backup trigger if GitHub skips an expected slot and normally
results in a scan about every 10 minutes, without touching the playlist when
its content has not changed. Heartbeat artifacts expire after 2 days.

**Important:** GitHub's built-in cron is best effort. It may delay or drop
scheduled events for hours. The staggered attempts help, but do not guarantee
ten-minute intervals. For better timing, configure an independent scheduler
as described below; `workflow_dispatch` is already supported.

A refresh generates `playlist.m3u` only when necessary. If unchanged, the
playlist is neither rewritten nor committed; the playlist file's last-modified
time is therefore **not** the last scan time. Each successful scan has a
heartbeat artifact, and scan reports are available in the run's diagnostics
artifact (the committed `status.json` records the last playlist update).

To force a refresh whenever you want:

1. Open **[Actions](https://github.com/Zer0Spce/ZeroStreams/actions/workflows/refresh.yml)**.
2. Select **Refresh live playlist** in the sidebar.
3. Click **Run workflow**, leave `main` selected and the **Respect refresh interval** checkbox unchecked.
4. Click the green **Run workflow** button; this bypasses the automatic cadence check.

Manual and scheduled refreshes share one concurrency group, so they run one
at a time. A manual refresh does not alter the automatic schedule.

### Recommended: independent external scheduler

For steadier ten-minute refreshes, configure a scheduler you control (for
example, cron-job.org or a scheduled cloud worker) to make an HTTPS POST
every ten minutes to:

```text
https://api.github.com/repos/Zer0Spce/ZeroStreams/actions/workflows/refresh.yml/dispatches
```

With these headers:

```text
Authorization: Bearer YOUR_FINE_GRAINED_GITHUB_TOKEN
Accept: application/vnd.github+json
Content-Type: application/json
```

And this JSON body:

```json
{"ref":"main","inputs":{"scheduled":"true"}}
```

Create a **fine-grained** GitHub token limited to this repository and
**Actions: Read and write**. Store it as a secret in your scheduler;
**never commit it to the repository**. The `scheduled` input makes the
external call respect the same recent-scan check as GitHub's fallback cron.
Leaving the input unchecked during manual GitHub dispatch always forces a
fresh scan. External scheduling must be configured separately; editing this
repository alone does not create an external job.
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


### Names, schedules, and artwork

Scheduled start times are read from the source's Pacific-time event rows and displayed in Philippine time (`PHT`, Asia/Manila, UTC+8), including the date. Missing times are omitted. Event names preserve the website's wording. Each distinct event keeps a separate playlist entry even when it reuses another event's stream URL. Exact duplicate event/URL/time entries are removed. No Shared Feed labels, category prefixes, or feed-number suffixes are added.

Free artwork sources: [IPTV-org channel logos](https://iptv-org.github.io/api/logos.json) and [TheSportsDB sports artwork](https://www.thesportsdb.com/docs/api). Artwork matching is enabled: exact, unambiguous channel names use IPTV-org; identified NBA, NFL, NHL, MLB, Formula 1 and WNBA groups use TheSportsDB league badges. Existing event artwork takes priority. Unknown matches and lookup failures retain the placeholder. No paid key is required; playback validation is unchanged.


The automatic refresh cadence, heartbeat deduplication and optional external dispatcher are documented in the **Schedule** section above.


### PPV event artwork

PPV's public streams API is used only to read event `poster` URLs. Posters take priority when normalized event names and Philippine calendar dates match, with sport-category checks where identified. Ambiguous or missing matches retain existing artwork/logo fallbacks. No PPV stream URLs or separate PPV playlist/workflow are added. The source catalogue is fetched once per nonempty refresh run; API failures do not prevent playlist generation.
