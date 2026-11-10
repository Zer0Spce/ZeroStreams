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

    def test_publishes_clean_hls_names_with_status(self):
        url = 'https://cdn.example.org/live.m3u8'
        entry = {'name': 'Football Match', 'group': 'NFL', 'page': scraper.BASE+'nfl',
                 'url': url, 'provider': 'RoxieStreams'}
        with patch('scraper.select_roxie', return_value=({scraper.BASE: 'ok'}, {url: [entry]}, [], [], [])), \
             patch('scraper.ppv_catalog', return_value=([], [], {'status': 'embed-only'})), \
             patch('scraper.verify_candidates', return_value={url: {'status': 'reachable', 'checked_at': '2026-11-10T00:00:00Z'}}), \
             patch('scraper.Path.write_text') as writes, \
             patch('scraper.Path.replace') as replace:
            scraper.main()
            self.assertTrue(replace.called)
            bodies = [str(call.args[0]) for call in writes.call_args_list]
            playlist = next(body for body in bodies if body.startswith('#EXTM3U'))
            report = next(body for body in bodies if '"validation_mode"' in body)
            self.assertIn('x-stream-status="reachable"', playlist)
            self.assertNotIn(' — Unverified', playlist)
            self.assertIn('"reachable_urls": 1', report)
            self.assertIn('"verified_urls": 0', report)
            self.assertIn('"validation_mode": "lightweight_hls"', report)

    def test_m3u_clean_labels_and_safe_status(self):
        entry = {'group': 'NFL"\n', 'name': 'Game\nInjected',
                 'page': scraper.BASE, 'url': 'https://example.org/live.m3u8',
                 'stream_status': 'verified'}
        output = scraper.render([entry])
        self.assertIn(',Game Injected\n', output)
        self.assertIn('x-stream-status="verified"', output)
        self.assertTrue(output.startswith('#EXTM3U\n'))
        entry['stream_status'] = 'malicious" bad="true'
        self.assertIn('x-stream-status="unverified"', scraper.render([entry]))

    def test_probe_classifies_live_segment_and_blocks_html(self):
        from io import BytesIO
        class Stream(BytesIO):
            pass
        def response(data):
            return Stream(data)
        master = b'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000\nvariant.m3u8\n'
        media = b'#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:6,\nchunk.ts\n'
        segment = bytes([0x47]) + b'0'*187 + bytes([0x47]) + b'1'*400
        with patch('scraper.urlopen', side_effect=[response(master), response(media), response(segment)]):
            self.assertEqual(scraper.inspect_hls('https://example.org/master.m3u8', scraper.BASE), 'verified')
        with patch('scraper.urlopen', return_value=response(b'<html>error</html>')):
            self.assertEqual(scraper.inspect_hls('https://example.org/bad.m3u8', scraper.BASE), 'unverified')
        with patch('scraper.urlopen', side_effect=[response(media), OSError('temporary')]):
            self.assertEqual(scraper.inspect_hls('https://example.org/live.m3u8', scraper.BASE), 'reachable')

if __name__ == '__main__':
    unittest.main()
