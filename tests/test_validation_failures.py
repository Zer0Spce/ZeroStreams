import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import scraper


class ValidationFailureTests(unittest.TestCase):
    def test_access_denied_publishes_unverified_and_reports_failure(self):
        entry = {'url': 'https://example.test/live.m3u8',
                 'page': 'https://roxiestreams.info/soccer-streams-1',
                 'name': 'Soccer', 'group': 'Soccer'}
        discovery = ({entry['page']: ''}, {entry['url']: [entry]}, [], [], [])
        previous = os.getcwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                original = '#EXTM3U\n# last successful playlist\n'
                Path('playlist.m3u').write_text(original)
                with patch.dict(os.environ, {'VERIFY_STREAMS': '1'}), patch.object(scraper, 'select_roxie', return_value=discovery), patch.object(
                    scraper, 'live_media', side_effect=HTTPError(entry['url'], 403, 'Forbidden', {}, None)
                ):
                    scraper.main()
                playlist = Path('playlist.m3u').read_text()
                self.assertIn(entry['url'], playlist)
                self.assertIn('[Unverified]', playlist)
                report = json.loads(Path('status.json').read_text())
                self.assertFalse(report['playlist_retained'])
                self.assertEqual(report['live_urls'], 0)
                self.assertEqual(report['published_urls'], 1)
                self.assertEqual(report['validation_errors'][0]['reason'], 'access_denied')
                self.assertEqual(report['validation_errors'][0]['http_status'], 403)
            finally:
                os.chdir(previous)

    def test_fetch_does_not_retry_access_denied(self):
        with patch.object(scraper, 'urlopen', side_effect=HTTPError(
            'https://example.test', 403, 'Forbidden', {}, None
        )) as request:
            with self.assertRaises(HTTPError):
                scraper.fetch('https://example.test')
        self.assertEqual(request.call_count, 1)
