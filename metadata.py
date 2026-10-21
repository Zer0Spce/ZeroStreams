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
    return value



def event_key(name):
    text = unicodedata.normalize('NFKD', clean_title(name)).casefold()
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()


def roxie_group(page):
    slug = urlsplit(page).path.strip('/').split('-')[0].lower()
    return GROUPS.get(slug, 'Live')


def fallback_logo(group):
    return LOGO_BASE + LOGOS.get(group, 'live') + '.png'


def decorate(entries):
    """Keep each website event; deduplicate only identical event/URL/time entries."""
    unique = {}
    for source in entries:
        entry = dict(source)
        entry['name'] = clean_title(entry['name'])
        identity = (entry['name'], entry['url'], entry.get('starts_at') or 0)
        if identity in unique:
            continue
        entry['poster'] = entry.get('poster') or fallback_logo(entry['group'])
        entry['event_id'] = f"{entry['group']}:{entry['name']}:{identity[2]}"
        entry['provider'] = entry.get('provider', 'RoxieStreams')
        entry['tvg_id'] = 'zerostreams.' + hashlib.sha256(repr(identity).encode()).hexdigest()[:16]
        entry['display_name'] = entry['name']
        if entry.get('starts_at'):
            entry['display_name'] += ' — ' + pht_time(entry['starts_at'])
        unique[identity] = entry
    return sorted(unique.values(), key=lambda e: (e['group'], e['name'], e.get('starts_at') or 0, e['url']))
