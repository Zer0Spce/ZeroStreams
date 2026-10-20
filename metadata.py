"""Consistent IPTV titles, category artwork, and feed labels."""
from collections import defaultdict
from schedule import pht_time
import hashlib
import html
import re
import time
import unicodedata
from urllib.parse import urlsplit

LOGO_BASE = 'https://raw.githubusercontent.com/Zer0Spce/ZeroStreams/main/assets/logos/'
GROUPS = {'nfl':'NFL', 'redzone':'NFL', 'nba':'NBA', 'wnba':'WNBA', 'nhl':'NHL',
          'mlb':'MLB', 'soccer':'Soccer', 'f1':'Formula 1', 'nascar':'NASCAR',
          'motogp':'MotoGP', 'mxgp':'MXGP', 'wwe':'WWE', 'ufc':'UFC',
          'boxing':'Boxing', 'fighting':'Combat Sports', 'motorsports':'Motorsports'}
LOGOS = {'NFL':'nfl', 'NBA':'nba', 'WNBA':'wnba', 'NHL':'nhl', 'MLB':'mlb',
         'Soccer':'soccer', 'Formula 1':'formula-1', 'NASCAR':'nascar', 'MotoGP':'motogp',
         'MXGP':'mxgp', 'WWE':'wwe', 'UFC':'ufc', 'Boxing':'boxing',
         'Combat Sports':'combat-sports', 'Motorsports':'motorsports'}


def clean_title(value):
    value = ' '.join(html.unescape(str(value)).split())
    value = re.sub(r'\bvs\.?\s*', 'vs ', value, flags=re.I)
    value = re.sub(r'\s+at\s+', ' vs ', value, flags=re.I)
    value = re.sub(r'\bLA Clippers\b', 'Los Angeles Clippers', value)
    value = re.sub(r'\bDenamrk\b', 'Denmark', value)
    value = re.sub(r'\s*-\s*(Race|Malaysian Grand Prix)\b', r': \1', value)
    value = re.sub(r'\broxiestreams\b\s*[-|:]?\s*', '', value, flags=re.I)
    return value.strip(' -|:')


def event_key(name):
    text = unicodedata.normalize('NFKD', clean_title(name)).casefold()
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()


def roxie_group(page):
    slug = urlsplit(page).path.strip('/').split('-')[0].lower()
    return GROUPS.get(slug, 'Live')


def fallback_logo(group):
    return LOGO_BASE + LOGOS.get(group, 'live') + '.png'


def decorate(entries):
    """Dedupe exact URLs; merge matching event names, number distinct feeds."""
    by_url = defaultdict(list)
    for entry in entries:
        by_url[entry['url']].append(dict(entry))
    unique = []
    for url, aliases in sorted(by_url.items()):
        aliases.sort(key=lambda e: (e.get('provider','RoxieStreams'), e['page'], e['name']))
        entry = aliases[0]
        names = {event_key(e['name']) for e in aliases}
        entry['provider'] = ' + '.join(sorted({e.get('provider','RoxieStreams') for e in aliases}))
        if len(names) > 1:
            channel = urlsplit(url).path.rsplit('/',1)[-1].removesuffix('.m3u8')
            labels = sorted({clean_title(e['name']) + (' (' + pht_time(e['starts_at']) + ')' if e.get('starts_at') else '') for e in aliases})
            entry['name'] = channel.upper() + ' — Shared Feed: ' + ' / '.join(labels)
            entry['starts_at'] = None
            categories = {alias['group'] for alias in aliases}
            entry['group'] = next(iter(categories)) if len(categories) == 1 else 'Shared Channels'
            entry['poster'] = ''
        else:
            entry['name'] = clean_title(entry['name'])
        entry['poster'] = entry.get('poster') or fallback_logo(entry['group'])
        # Date avoids grouping repeat fixtures on different days.
        date = time.strftime('%Y-%m-%d', time.gmtime(entry.get('starts_at') or 0)) if entry.get('starts_at') else ''
        entry['event_id'] = f'{entry["group"]}:{event_key(entry["name"])}:{date}'
        identity = entry.get('identity') or f'{entry["provider"]}:{urlsplit(url).netloc}:{urlsplit(url).path}'
        entry['tvg_id'] = 'zerostreams.' + hashlib.sha256(identity.encode()).hexdigest()[:16]
        unique.append(entry)
    groups = defaultdict(list)
    for entry in unique:
        groups[entry['event_id']].append(entry)
    result = []
    for key in sorted(groups):
        feeds = sorted(groups[key], key=lambda e:(e['provider'],e.get('source_tag',''),e['url']))
        for index, entry in enumerate(feeds,1):
            details = [f'Feed {index}'] if len(feeds)>1 else []
            if entry.get('starts_at'):
                details.append(pht_time(entry['starts_at']))
            details.extend(provider for provider in entry['provider'].split(' + ') if provider.casefold() != 'roxiestreams')
            if entry.get('source_tag'):
                details.append(entry['source_tag'])
            if entry.get('locale'):
                details.append(entry['locale'].upper())
            title = entry['name'] if entry['name'].casefold().startswith(entry['group'].casefold()) else f'{entry["group"]} | {entry["name"]}'
            entry['display_name'] = title + (' — ' + ' · '.join(details) if details else '')
            result.append(entry)
    return result

