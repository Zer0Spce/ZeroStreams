"""Best-effort public artwork matching; never infer a channel from a stream slug."""
from functools import lru_cache
import json
import os
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

LEAGUES = {'NBA': '4387', 'NFL': '4391', 'NHL': '4380', 'MLB': '4424',
           'Formula 1': '4370', 'WNBA': '4516'}


def key(value):
    return re.sub(r'[^a-z0-9]', '', value.casefold())


@lru_cache(maxsize=32)
def get_json(url):
    try:
        with urlopen(Request(url, headers={'User-Agent': 'ZeroStreams/1.0'}), timeout=8) as response:
            return json.load(response)
    except Exception as exc:
        print('Artwork lookup unavailable: ' + str(exc), flush=True)
        return None


def image_url(value):
    return value if isinstance(value, str) and urlsplit(value).scheme == 'https' else ''


@lru_cache(maxsize=1)
def channel_logos():
    channels = get_json('https://iptv-org.github.io/api/channels.json') or []
    logos = get_json('https://iptv-org.github.io/api/logos.json') or []
    by_id = {}
    for logo in logos:
        url = image_url(logo.get('url'))
        if url:
            by_id.setdefault(logo.get('channel'), []).append(url)
    names = {}
    for channel in channels:
        options = sorted(set(by_id.get(channel.get('id'), [])))
        if options:
            for name in [channel.get('name', ''), *(channel.get('alt_names') or [])]:
                names.setdefault(key(name), set()).add(options[0])
    # Ambiguous regional/duplicate channel names retain the existing fallback.
    return {name: next(iter(urls)) for name, urls in names.items() if len(urls) == 1}


def league_logo(group):
    league_id = LEAGUES.get(group)
    if not league_id:
        return ''
    api_key = os.getenv('THESPORTSDB_API_KEY', '123')
    data = get_json(f'https://www.thesportsdb.com/api/v1/json/{api_key}/lookupleague.php?id={league_id}') or {}
    for league in data.get('leagues') or []:
        if str(league.get('idLeague')) == league_id:
            return image_url(league.get('strBadge')) or image_url(league.get('strLogo'))
    return ''


def enrich(entries):
    if not entries:
        return entries
    channels = channel_logos()
    for entry in entries:
        poster = entry.get('poster', '')
        if poster and 'assets/logos/' not in poster:
            continue
        channel = channels.get(key(entry['name']), '')
        logo = channel or league_logo(entry['group'])
        if logo:
            entry['poster'] = logo
            entry['artwork_source'] = 'iptv-org' if channel else 'thesportsdb'
    return entries
