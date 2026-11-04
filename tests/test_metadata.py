import json
import unittest
from metadata import active, clean_title, decorate, direct_sources, ppv_catalog

class MetadataTests(unittest.TestCase):
    def entry(self, url, name='Detroit Lions vs Carolina Panthers', provider='RoxieStreams'):
        return {'name':name,'group':'NFL','url':url,'page':'https://example.org/event','provider':provider}

    def test_titles_match_across_site_wording(self):
        self.assertEqual(clean_title('  Detroit Lions at Carolina Panthers '), 'Detroit Lions vs Carolina Panthers')
        self.assertEqual(clean_title('LA Clippers vs. Utah Jazz'), 'Los Angeles Clippers vs Utah Jazz')

    def test_reject_future_and_ended_but_keep_247(self):
        self.assertFalse(active({'starts_at':200,'ends_at':300}, 100))
        self.assertFalse(active({'starts_at':50,'ends_at':90}, 100))
        self.assertTrue(active({'starts_at':50,'ends_at':150}, 100))
        self.assertTrue(active({'always_live':1,'ends_at':1}, 100))

    def test_embeds_and_protected_urls_are_not_playlist_urls(self):
        self.assertEqual(direct_sources({'sources':[{'type':'iframe','data':'https://embed.example/player'}]}), [])
        self.assertEqual(direct_sources({'auth':True,'m3u8':'https://example.org/a.m3u8'}), [])
        self.assertEqual(direct_sources({'m3u8':'https://example.org/a.m3u8'}), ['https://example.org/a.m3u8'])

    def test_duplicate_urls_removed_and_alternates_numbered(self):
        a=self.entry('https://example.org/a.m3u8')
        b=self.entry('https://example.org/b.m3u8', provider='PPV')
        output=decorate([a,a,b], [])
        self.assertEqual(len(output),2)
        self.assertFalse(any('RoxieStreams' in entry['display_name'] for entry in output))
        self.assertTrue(all(e['poster'].endswith('nfl.png') for e in output))
        self.assertIn('Feed 1',output[0]['display_name'])
        self.assertIn('Feed 2',output[1]['display_name'])
        self.assertEqual(len({e['tvg_id'] for e in output}),2)
        self.assertEqual(output,decorate([b,a,a], []))

    def test_repeated_url_for_different_events_is_not_mislabeled(self):
        output=decorate([self.entry('https://example.org/tsn.m3u8'), self.entry('https://example.org/tsn.m3u8','Formula 1')], [])
        self.assertEqual(output[0]['name'],'TSN — Shared Feed')
        self.assertEqual(output[0]['group'],'Shared Channels')

    def test_exact_match_uses_event_poster_and_common_name(self):
        output=decorate([self.entry('https://example.org/a.m3u8')], [{'name':'Detroit Lions at Carolina Panthers','poster':'https://example.org/game.jpg','starts_at':100}])
        self.assertEqual(output[0]['poster'],'https://example.org/game.jpg')
        self.assertEqual(output[0]['name'],'Detroit Lions vs Carolina Panthers')
        self.assertEqual(output[0]['display_name'],'NFL | Detroit Lions vs Carolina Panthers')

    def test_catalog_supports_substreams_without_publishing_embeds(self):
        index={'success':True,'streams':[{'category':'Cricket','streams':[{'id':1,'name':'Willow','always_live':1,'uri_name':'willow','poster':'https://example.org/willow.jpg'}]}]}
        detail={'success':True,'data':{'id':1,'sources':[{'type':'iframe','data':'https://embed.example/willow'}],'substreams':[{'id':2,'uri':'willow-2','m3u8':'https://example.org/2.m3u8'}]}}
        def fake(url,referer):
            return json.dumps(index if url.endswith('/streams') else detail)
        catalog, entries, status=ppv_catalog(fake, now=100)
        self.assertEqual(len(catalog),1)
        self.assertEqual(len(entries),1)
        self.assertEqual(entries[0]['url'],'https://example.org/2.m3u8')
        self.assertEqual(status['status'],'direct-hls')

    def test_api_outage_reports_optional_source_unavailable(self):
        def fail(*args): raise OSError('offline')
        catalog, entries, status=ppv_catalog(fail)
        self.assertEqual((catalog,entries),([],[]))
        self.assertEqual(status['status'],'unavailable')

if __name__=='__main__': unittest.main()
