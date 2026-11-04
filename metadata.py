"""Public PPV catalogue metadata and consistent IPTV presentation."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import html
import json
import os
import re
import time
import unicodedata
from urllib.parse import quote, urlsplit

PPV_BASES = ('https://api.ppv.st/api', 'https://api.ppv.cx/api')
LOGO_BASE = 'https://raw.githubusercontent.com/' + os.getenv('GITHUB_REPOSITORY', 'Zer0Spce/ZeroStreams') + '/main/assets/logos/'
PHT = timezone(timedelta(hours=8), 'PHT')
GROUPS = {'nfl':'NFL', 'redzone':'NFL', 'nba':'NBA', 'wnba':'WNBA', 'nhl':'NHL',
          'ncaa':'NCAA', 'college':'College Sports',
          'mlb':'MLB', 'soccer':'Soccer', 'f1':'Formula 1', 'nascar':'NASCAR',
          'motogp':'MotoGP', 'mxgp':'MXGP', 'wwe':'WWE', 'ufc':'UFC',
          'boxing':'Boxing', 'fighting':'Combat Sports', 'motorsports':'Motorsports'}
LOGOS = {'NFL':'nfl', 'NBA':'nba', 'WNBA':'wnba', 'NHL':'nhl', 'MLB':'mlb',
         'Soccer':'soccer', 'Formula 1':'formula-1', 'NASCAR':'nascar', 'MotoGP':'motogp',
         'MXGP':'mxgp', 'WWE':'wwe', 'UFC':'ufc', 'Boxing':'boxing',
         'Combat Sports':'combat-sports', 'Motorsports':'motorsports'}


def clean_title(value):
    value = ' '.join(html.unescape(str(value)).split())
    # Remove marketing labels while retaining the actual fixture or channel name.
    value = re.sub(r'^(?:RoxieStreams|Watch Live|Live Stream)\s*[:|–—-]\s*', '', value, flags=re.I)
    value = re.sub(r'\s*[-–—|]\s*(?:Live Stream(?:ing)?|Watch Live|HD Stream)\s*$', '', value, flags=re.I)
    value = re.sub(r'\s+versus\s+', ' vs ', value, flags=re.I)
    value = re.sub(r'\bvs\.?\s*', 'vs ', value, flags=re.I)
    value = re.sub(r'\s+at\s+', ' vs ', value, flags=re.I)
    value = re.sub(r'\bLA Clippers\b', 'Los Angeles Clippers', value)
    value = re.sub(r'\bDenamrk\b', 'Denmark', value)
    value = re.sub(r'\s*-\s*(Race|Malaysian Grand Prix)\b', r': \1', value)
    return value.strip()


def scheduled_start(item):
    """Return a Unix start only for scheduled events, not continuous channels."""
    if item.get('always_live') in (True, 1, '1') or re.search(r'24\s*/\s*7', str(item.get('tag') or ''), re.I):
        return 0
    try:
        return max(0, int(item.get('starts_at') or 0))
    except (TypeError, ValueError, OverflowError):
        return 0


def pht_time(timestamp):
    """Format an authoritative Unix start in Philippine Time (UTC+8)."""
    if not timestamp:
        return ''
    try:
        local = datetime.fromtimestamp(int(timestamp), PHT)
    except (TypeError, ValueError, OverflowError, OSError):
        return ''
    hour = local.hour % 12 or 12
    ampm = 'AM' if local.hour < 12 else 'PM'
    return f'{local:%b} {local.day}, {local.year}, {hour}:{local.minute:02d} {ampm} PHT'


def category_title(group, name):
    """One consistent league prefix, never a duplicated league prefix."""
    name = clean_title(name)
    if group == 'Shared Channels':
        return f'Shared Channels | {name}'
    existing = re.match(rf'^{re.escape(group)}\s*[:|–—-]\s*(.+)$', name, re.I)
    if existing:
        return f'{group} | {existing.group(1)}'
    if name.casefold() == group.casefold() or name.casefold().startswith(group.casefold() + ' '):
        return name
    return f'{group} | {name}'


def event_key(name):
    text = unicodedata.normalize('NFKD', clean_title(name)).casefold()
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()


def active(item, now):
    if item.get('always_live') in (True, 1, '1'):
        return True
    start = int(item.get('starts_at') or 0)
    end = int(item.get('ends_at') or 0)
    return start > 0 and start <= now and (end == 0 or now < end)


def hls_url(value):
    return isinstance(value, str) and urlsplit(value).scheme in ('http', 'https') and '.m3u8' in urlsplit(value).path.lower()


def direct_sources(detail):
    """Accept only directly published HLS. Keep iframe integrations intact."""
    if detail.get('auth') or detail.get('vip_stream'):
        return []
    urls = set()
    for field in ('m3u8', 'playlist_full'):
        if hls_url(detail.get(field)):
            urls.add(detail[field])
    for source in detail.get('sources') or []:
        if source.get('type') in ('hls', 'playlist', 'm3u8') and hls_url(source.get('data')):
            urls.add(source['data'])
    return sorted(urls)


def ppv_catalog(fetcher, now=None):
    now = int(time.time()) if now is None else now
    failure = None
    for api in PPV_BASES:
        try:
            index = json.loads(fetcher(api + '/streams', 'https://ppv.st/'))
            if index.get('success') is not True or not isinstance(index.get('streams'), list):
                raise ValueError('Unexpected PPV catalogue schema')
            break
        except Exception as exc:
            failure = str(exc)
    else:
        return [], [], {'status':'unavailable', 'error':failure, 'active_events':0, 'direct_candidates':0}
    catalog, entries, errors = [], [], []
    embed_only = 0
    for category in index['streams']:
        for item in category.get('streams') or []:
            if not active(item, now):
                continue
            catalog.append({'name':clean_title(item.get('name') or 'Untitled Stream'),
                            'poster':item.get('poster') or '', 'tag':item.get('tag') or '',
                            'category':category.get('category') or 'Live', 'uri':item.get('uri_name'),
                            'starts_at':item.get('starts_at'), 'ends_at':item.get('ends_at'),
                            'starts_at_pht':pht_time(scheduled_start(item)),
                            'page':'https://ppv.st/live/' + str(item.get('uri_name') or '')})
            uri = item.get('uri_name')
            if not uri:
                errors.append({'id':item.get('id'), 'error':'Missing stream URI'})
                continue
            try:
                response = json.loads(fetcher(api + '/streams/' + quote(uri, safe='/'), 'https://ppv.st/'))
                if response.get('success') is not True or not isinstance(response.get('data'), dict):
                    raise ValueError('Unexpected PPV stream schema')
                detail = response['data']
                if detail.get('auth') or detail.get('vip_stream'):
                    continue
                found = 0
                for variant in [detail] + list(detail.get('substreams') or []):
                    for url in direct_sources(variant):
                        found += 1
                        entries.append({'name':clean_title(item.get('name') or detail.get('name') or 'Untitled Stream'),
                                        'group':item.get('tag') if item.get('tag') in ('NFL','NBA','NHL','MLB','WNBA','UFC','WWE') else category.get('category') or 'Live',
                                        'page':'https://ppv.st/live/' + str(variant.get('uri') or uri),
                                        'url':url, 'provider':'PPV', 'poster':item.get('poster') or '',
                                        'source_tag':variant.get('source_tag') or detail.get('source_tag') or '',
                                        'locale':variant.get('locale') or item.get('locale') or '',
                                        'identity':f'ppv:{variant.get("id", item.get("id"))}:{urlsplit(url).path}',
                                        'starts_at':item.get('starts_at') or 0,
                                        'starts_at_pht':pht_time(scheduled_start(item))})
                if found == 0:
                    embed_only += 1
            except Exception as exc:
                errors.append({'uri':uri, 'error':str(exc)})
    return catalog, entries, {'status':'partial' if errors else ('direct-hls' if entries else 'embed-only'),
                             'active_events':len(catalog), 'direct_candidates':len(entries),
                             'embed_only_events':embed_only, 'errors':errors}


def roxie_group(page):
    slug = urlsplit(page).path.strip('/').split('-')[0].lower()
    return GROUPS.get(slug, 'Live')


def fallback_logo(group):
    return LOGO_BASE + LOGOS.get(group, 'live') + '.png'


def decorate(entries, catalog, poster_validator=None):
    """Dedupe exact URLs; merge matching event names, number distinct feeds."""
    metadata = {}
    for item in catalog:
        metadata.setdefault(event_key(item['name']), item)
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
            entry['name'] = channel.upper()
            entry['group'] = 'Shared Channels'
            entry['poster'] = ''
        else:
            entry['name'] = clean_title(entry['name'])
            match = metadata.get(event_key(entry['name']))
            if match:
                entry['name'] = clean_title(match['name'])
                entry['poster'] = match['poster']
                entry['starts_at'] = scheduled_start(match)
                entry['starts_at_pht'] = match.get('starts_at_pht') or pht_time(scheduled_start(match))
        poster = entry.get('poster') or ''
        # Reject broken/unreachable PPV images before emitting an IPTV tvg-logo.
        if poster and urlsplit(poster).scheme in ('https', 'http'):
            if poster_validator is not None:
                try:
                    if not poster_validator(poster):
                        poster = ''
                except Exception:
                    poster = ''
        else:
            poster = ''
        entry['poster'] = poster or fallback_logo(entry['group'])
        # Date avoids grouping repeat fixtures on different days.
        date = datetime.fromtimestamp(int(entry['starts_at']), PHT).date().isoformat() if entry.get('starts_at_pht') else ''
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
            details.extend(provider for provider in entry['provider'].split(' + ') if provider.casefold() != 'roxiestreams')
            if entry.get('source_tag'):
                details.append(entry['source_tag'])
            if entry.get('locale'):
                details.append(entry['locale'].upper())
            title = category_title(entry['group'], entry['name'])
            if entry.get('starts_at_pht'):
                title += ' — ' + entry['starts_at_pht']
            entry['display_name'] = title + (' — ' + ' · '.join(details) if details else '')
            result.append(entry)
    return result
