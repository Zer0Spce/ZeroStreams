"""Read the site's Pacific-time schedule and display Philippine time."""
from datetime import datetime
import html
import re
from zoneinfo import ZoneInfo


def start_times(text, page, links):
    result = {}
    for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>', text, re.I | re.S):
        match = re.search(r'<td\b[^>]*class=[\"\'][^\"\']*event-start-time[^\"\']*[\"\'][^>]*>(.*?)</td>', row, re.I | re.S)
        if not match:
            continue
        value = html.unescape(re.sub('<[^>]+>', '', match[1])).strip()
        try:
            stamp = datetime.strptime(value, '%B %d, %Y %I:%M %p').replace(tzinfo=ZoneInfo('America/Los_Angeles')).timestamp()
        except ValueError:
            continue
        for target, label in links(row, page):
            result[(target, label)] = stamp
    return result


def pht_time(timestamp):
    return datetime.fromtimestamp(timestamp, ZoneInfo('Asia/Manila')).strftime('%b %d, %I:%M %p PHT')
