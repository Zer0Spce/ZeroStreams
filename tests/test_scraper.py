import unittest
from unittest.mock import patch
import scraper

class ParserTests(unittest.TestCase):
    def test_generated_domain_urls(self):
        source = """fetch('domains.txt'); function getRandomStream(path, subdomain = 'tedesco') {} getRandomStream('tsn.m3u8'); getRandomStream('nfl.m3u8', 'admin2')"""
        urls = scraper.extract_sources(source, scraper.BASE+'nfl-streams-1', lambda *args: 'example.org\n')
        self.assertEqual(urls, ['https://admin2.example.org/nfl.m3u8', 'https://tedesco.example.org/tsn.m3u8'])
    def test_ignore_external_and_assets(self):
        links = list(scraper.internal_links('<a href="/nfl">NFL</a><a href="https://ads.test/">Ad</a><a href="/x.png">Image</a>', scraper.BASE))
        self.assertEqual(links, [(scraper.BASE+'nfl', 'NFL')])
    def test_backup_rewrites_absolute_primary_links(self):
        links = list(scraper.internal_links('<a href="https://roxiestreams.info/nfl">NFL</a>', 'https://roxiestreams.biz/', 'https://roxiestreams.biz/'))
        self.assertEqual(links, [('https://roxiestreams.biz/nfl', 'NFL')])

    def test_failover_uses_first_complete_mirror(self):
        primary = 'https://roxiestreams.info/'
        backup = 'https://roxiestreams.biz/'
        with patch('scraper.BASE', primary), patch('scraper.BACKUPS',(backup,)), patch('scraper.discover_roxie', side_effect=[({}, {}, [{'error':'offline'}]), ({backup:'player'}, {}, [])]), patch('scraper.collect_roxie', side_effect=[({},[],[]), ({'https://example.org/live.m3u8':[]},[],[])]):
            pages,candidates,unsupported,errors,attempts = scraper.select_roxie(None)
            self.assertEqual(scraper.BASE,backup)
            self.assertEqual(errors,[])
            self.assertEqual(len(attempts),2)
            self.assertTrue(candidates)

    def test_domain_file_failure_triggers_backup(self):
        primary = 'https://roxiestreams.info/'
        backup = 'https://roxiestreams.su/'
        with patch('scraper.BASE',primary), patch('scraper.BACKUPS',(backup,)), patch('scraper.discover_roxie',side_effect=lambda *args: ({'p':'player'}, {}, [])), patch('scraper.collect_roxie',side_effect=[({},[],[{'error':'domains unavailable'}]), ({'stream':[]},[],[])]):
            result = scraper.select_roxie(None)
            self.assertEqual(scraper.BASE,backup)
            self.assertEqual(result[3],[])

    def test_collect_direct_public_hls_formats(self):
        page = scraper.BASE + 'nba-streams-1'
        source = """<video src="/media/one.m3u8?token=x"></video>
        <script>const fallback = "//cdn.example.org/two.m3u8"; file: "relative/three.m3u8"</script>"""
        urls = scraper.extract_sources(source, page)
        self.assertIn(scraper.BASE + 'media/one.m3u8?token=x', urls)
        self.assertIn('https://cdn.example.org/two.m3u8', urls)
        self.assertIn(scraper.BASE + 'relative/three.m3u8', urls)

    def test_main_publishes_unverified_candidates_without_network_checks(self):
        import json
        import os
        from pathlib import Path
        from tempfile import TemporaryDirectory

        page = scraper.BASE + 'nba-streams-1'
        urls = ['https://cdn.example.org/one.m3u8', 'https://cdn.example.org/two.m3u8']
        candidates = {
            url: [{'name':'Team A vs Team B', 'group':'NBA', 'provider':'RoxieStreams',
                   'page':page, 'url':url}]
            for url in urls
        }
        old_cwd = os.getcwd()
        with TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                with patch('scraper.select_roxie', return_value=({page:'player'}, candidates, [], [], [])), \
                     patch('scraper.ppv_catalog', return_value=([], [], {'status':'embed-only'})), \
                     patch('scraper.live_media', side_effect=AssertionError('must not validate HLS')):
                    scraper.main()
                playlist = Path('playlist.m3u').read_text()
                status = json.loads(Path('status.json').read_text())
                for url in urls:
                    self.assertIn(url, playlist)
                self.assertEqual(playlist.count('#EXTINF:'), 2)
                self.assertEqual(status['published_urls'], 2)
                self.assertEqual(status['validation_mode'], 'discovery_only')
                self.assertEqual(status['not_checked_urls'], 2)
            finally:
                os.chdir(old_cwd)

    def test_zero_candidates_keep_existing_playlist(self):
        import os
        from pathlib import Path
        from tempfile import TemporaryDirectory

        old_cwd = os.getcwd()
        with TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                Path('playlist.m3u').write_text('#EXTM3U\n#EXTINF:-1,Previous\nhttps://example.org/old.m3u8\n')
                with patch('scraper.select_roxie', return_value=({}, {}, [], [], [])), \
                     patch('scraper.ppv_catalog', return_value=([], [], {'status':'embed-only'})):
                    with self.assertRaises(RuntimeError):
                        scraper.main()
                self.assertIn('https://example.org/old.m3u8', Path('playlist.m3u').read_text())
            finally:
                os.chdir(old_cwd)

    def test_reject_vod_and_fake_manifest(self):
        for text in ['<html>Denied</html>', '#EXTM3U\n#EXTINF:6,\nx.ts\n#EXT-X-ENDLIST']:
            with patch('scraper.fetch', return_value=text):
                self.assertFalse(scraper.live_media('https://example.org/live.m3u8', scraper.BASE))
    def test_live_master_follows_variant_and_segment(self):
        from io import BytesIO
        manifests = ['#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000\nmedia.m3u8', '#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:6,\nsegment.ts']
        with patch('scraper.fetch', side_effect=manifests), patch('scraper.urlopen', return_value=BytesIO(b'video')) as request:
            self.assertTrue(scraper.live_media('https://example.org/master.m3u8', scraper.BASE))
            self.assertEqual(request.call_args.args[0].full_url, 'https://example.org/segment.ts')

    def test_poster_validation_rejects_missing_and_html(self):
        from io import BytesIO
        class FakeResponse(BytesIO):
            headers = {'Content-Type': 'text/html'}
        scraper.poster_available.cache_clear()
        with patch('scraper.urlopen', return_value=FakeResponse(b'<html>Not found</html>')):
            self.assertFalse(scraper.poster_available('https://example.org/missing.jpg'))
        scraper.poster_available.cache_clear()

    def test_poster_validation_accepts_jpeg(self):
        from io import BytesIO
        class FakeResponse(BytesIO):
            headers = {'Content-Type': 'image/jpeg'}
        scraper.poster_available.cache_clear()
        with patch('scraper.urlopen', return_value=FakeResponse(b'\xff\xd8\xff' + bytes(40))):
            self.assertTrue(scraper.poster_available('https://example.org/photo.jpg'))
        scraper.poster_available.cache_clear()

    def test_m3u_sanitizes_labels(self):
        output = scraper.render([{'group':'NFL"\n', 'name':'Game\nInjected', 'page':scraper.BASE, 'url':'https://example.org/live.m3u8'}])
        self.assertIn(',Game Injected\n', output)
        self.assertTrue(output.startswith('#EXTM3U\n'))

if __name__ == '__main__':
    unittest.main()
