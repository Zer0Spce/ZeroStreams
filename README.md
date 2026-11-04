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

ZeroStreams runs entirely through **GitHub Actions**, with no external scheduler,
token, API account, or paid service to configure.

Two separately registered workflows provide multiple opportunities to trigger
the same refresh code:
- [Refresh live playlist](.github/workflows/refresh.yml) attempts every 5 minutes
  at UTC minutes 04, 09, 14, 19, etc.
- [Backup automatic playlist refresh](.github/workflows/refresh-watchdog.yml)
  attempts every 5 minutes at UTC minutes 02, 07, 12, 17, etc.

Both share a single concurrency group to avoid simultaneous scrapes. A successful
scan records a short-lived `playlist-refresh-heartbeat` artifact; subsequent
scheduled attempts skip scanning when the latest successful scan was less than
8 minutes ago. Normal target: **roughly one scan every 10 minutes**.

**GitHub scheduled events are best effort.** GitHub can delay or drop them
during periods of high demand. The independent backup schedule reduces reliance
on one workflow registration but cannot guarantee uninterrupted timing if
GitHub's entire schedule service is affected.

Every actual scan tests the parser, runs the scraper, and writes `playlist.m3u`
only when the playlist changes. The file's last commit time is **not** necessarily
the last scan time. Run diagnostics and successful heartbeat artifacts are
available from the GitHub Actions run pages.

### Manual refresh

1. Open **[Actions](https://github.com/Zer0Spce/ZeroStreams/actions/workflows/refresh.yml)**.
2. Select **Refresh live playlist**.
3. Click **Run workflow**, select `main`, then confirm **Run workflow**.

Manual runs always perform a scan, regardless of the last successful scan.
The backup workflow also has a manual trigger for testing.

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


Both GitHub-native schedules and the heartbeat deduplication are documented in the **Schedule** section above.


### PPV event artwork

PPV's public streams API is used only to read event `poster` URLs. Posters take priority when normalized event names and Philippine calendar dates match, with sport-category checks where identified. Ambiguous or missing matches retain existing artwork/logo fallbacks. No PPV stream URLs or separate PPV playlist/workflow are added. The source catalogue is fetched once per nonempty refresh run; API failures do not prevent playlist generation.
