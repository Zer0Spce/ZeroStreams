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

    def test_m3u_sanitizes_labels(self):
        output = scraper.render([{'group':'NFL"\n', 'name':'Game\nInjected', 'page':scraper.BASE, 'url':'https://example.org/live.m3u8'}])
        self.assertIn(',Game Injected\n', output)
        self.assertTrue(output.startswith('#EXTM3U\n'))

if __name__ == '__main__':
    unittest.main()
