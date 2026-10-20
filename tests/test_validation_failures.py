import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import scraper


class ValidationFailureTests(unittest.TestCase):
    def test_access_denied_preserves_playlist_and_reports_failure(self):
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
                with patch.object(scraper, 'select_roxie', return_value=discovery), patch.object(
                    scraper, 'live_media', side_effect=HTTPError(entry['url'], 403, 'Forbidden', {}, None)
                ):
                    with self.assertRaisesRegex(RuntimeError, 'No streams passed'):
                        scraper.main()
                self.assertEqual(Path('playlist.m3u').read_text(), original)
                report = json.loads(Path('status.json').read_text())
                self.assertTrue(report['playlist_retained'])
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
