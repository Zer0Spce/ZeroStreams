"""Best-effort public artwork matching; never infer a channel from a stream slug."""
from functools import lru_cache
from datetime import datetime
from zoneinfo import ZoneInfo
import unicodedata
import json
import os
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

LEAGUES = {'NBA': '4387', 'NFL': '4391', 'NHL': '4380', 'MLB': '4424',
           'Formula 1': '4370', 'WNBA': '4516'}
PPV_CATEGORIES = {'NBA': 'Basketball', 'WNBA': 'Basketball', 'NFL': 'American Football',
                  'NHL': 'Ice Hockey', 'Soccer': 'Football', 'MLB': 'Baseball',
                  'WWE': 'Wrestling', 'UFC': 'Combat Sports', 'Boxing': 'Combat Sports'}


def event_name(value):
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().casefold()
    value = re.sub(r'\s+(?:vs\.?|v\.?|at|@)\s+', ' vs ', value)
    return key(value)


def event_day(stamp):
    try:
        return datetime.fromtimestamp(float(stamp), ZoneInfo('Asia/Manila')).date() if stamp and float(stamp) > 0 else None
    except (ValueError, TypeError, OverflowError, OSError):
        return None


@lru_cache(maxsize=1)
def ppv_posters():
    data = get_json('https://api.ppv.st/api/streams') or {}
    if data.get('success') is not True:
        return []
    result = []
    for category in data.get('streams') or []:
        for stream in category.get('streams') or []:
            poster = image_url(stream.get('poster'))
            if poster and stream.get('name'):
                result.append((event_name(stream['name']), event_day(stream.get('starts_at')),
                               stream.get('category_name') or category.get('category'), poster))
    return result


def ppv_poster(entry, posters):
    name, day = event_name(entry['name']), event_day(entry.get('starts_at'))
    category = PPV_CATEGORIES.get(entry['group'])
    matches = {poster for candidate, date, sport, poster in posters
               if candidate == name and date == day and (not category or category == sport)}
    return next(iter(matches)) if len(matches) == 1 else ''


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
    posters = ppv_posters()
    for entry in entries:
        event_poster = ppv_poster(entry, posters)
        if event_poster:
            entry['poster'] = event_poster
            entry['artwork_source'] = 'ppv'
            continue
        poster = entry.get('poster', '')
        if poster and 'assets/logos/' not in poster:
            continue
        channel = channels.get(key(entry['name']), '')
        logo = channel or league_logo(entry['group'])
        if logo:
            entry['poster'] = logo
            entry['artwork_source'] = 'iptv-org' if channel else 'thesportsdb'
    return entries

