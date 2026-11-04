import json
import unittest
from metadata import active, category_title, clean_title, decorate, direct_sources, pht_time, ppv_catalog, roxie_group, scheduled_start

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
        self.assertEqual(output[0]['name'],'TSN')
        self.assertEqual(output[0]['display_name'],'Shared Channels | TSN')
        self.assertEqual(output[0]['group'],'Shared Channels')

    def test_exact_match_uses_event_poster_and_common_name(self):
        output=decorate([self.entry('https://example.org/a.m3u8')], [{'name':'Detroit Lions at Carolina Panthers','poster':'https://example.org/game.jpg','starts_at':100}])
        self.assertEqual(output[0]['poster'],'https://example.org/game.jpg')
        self.assertEqual(output[0]['name'],'Detroit Lions vs Carolina Panthers')
        self.assertIn('NFL | Detroit Lions vs Carolina Panthers — Jan 1, 1970, 8:01 AM PHT', output[0]['display_name'])

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

    def test_pht_crosses_date_correctly(self):
        self.assertEqual(pht_time(1793750400), 'Nov 4, 2026, 8:00 AM PHT')
        self.assertEqual(pht_time(0), '')
        self.assertEqual(pht_time(-1), 'Jan 1, 1970, 7:59 AM PHT')

    def test_24_7_channels_never_display_misleading_schedules(self):
        self.assertEqual(scheduled_start({'tag':'24/7 channel','starts_at':1793750400}), 0)
        self.assertEqual(scheduled_start({'always_live':1,'starts_at':1793750400}), 0)

    def test_category_and_source_labels(self):
        self.assertEqual(roxie_group('https://example.org/ncaa-streams-1'), 'NCAA')
        self.assertEqual(category_title('NBA', 'NBA | Lakers vs Celtics'), 'NBA | Lakers vs Celtics')
        self.assertEqual(category_title('NBA', 'NBA Lakers vs Celtics'), 'NBA Lakers vs Celtics')
        self.assertEqual(clean_title('Watch Live: Miami Heat versus Boston Celtics - HD Stream'),
                         'Miami Heat vs Boston Celtics')

    def test_ppv_poster_is_used_when_reachable_and_falls_back_when_broken(self):
        catalog = [{'name':'Detroit Lions at Carolina Panthers',
                    'poster':'https://static.ppvservices.st/assets/thumb/test-thumbnail.jpg',
                    'starts_at':1793750400}]
        good = decorate([self.entry('https://example.org/a.m3u8')], catalog, poster_validator=lambda u: True)
        self.assertEqual(good[0]['poster'], catalog[0]['poster'])
        self.assertIn('Nov 4, 2026, 8:00 AM PHT', good[0]['display_name'])
        broken = decorate([self.entry('https://example.org/a.m3u8')], catalog, poster_validator=lambda u: False)
        self.assertTrue(broken[0]['poster'].endswith('/nfl.png'))
        self.assertEqual(good[0]['tvg_id'], broken[0]['tvg_id'])

    def test_api_outage_reports_optional_source_unavailable(self):
        def fail(*args): raise OSError('offline')
        catalog, entries, status=ppv_catalog(fail)
        self.assertEqual((catalog,entries),([],[]))
        self.assertEqual(status['status'],'unavailable')

if __name__=='__main__': unittest.main()
