import unittest
from metadata import clean_title, decorate

class MetadataTests(unittest.TestCase):
    def entry(self, url, name='Detroit Lions vs Carolina Panthers', provider='RoxieStreams'):
        return {'name':name,'group':'NFL','url':url,'page':'https://example.org/event','provider':provider}

    def test_titles_match_across_site_wording(self):
        self.assertEqual(clean_title('  Detroit Lions at Carolina Panthers '), 'Detroit Lions at Carolina Panthers')
        self.assertEqual(clean_title('LA Clippers vs. Utah Jazz'), 'LA Clippers vs. Utah Jazz')

    def test_duplicate_urls_removed_and_alternates_numbered(self):
        a=self.entry('https://example.org/a.m3u8')
        b=self.entry('https://example.org/b.m3u8', provider='RoxieStreams')
        output=decorate([a,a,b])
        self.assertEqual(len(output),2)
        self.assertFalse(any('RoxieStreams' in entry['display_name'] for entry in output))
        self.assertTrue(all(e['poster'].endswith('nfl.png') for e in output))
        self.assertEqual(output[0]['display_name'], a['name'])
        self.assertEqual(output[1]['display_name'], a['name'])
        self.assertEqual(len({e['tvg_id'] for e in output}),2)
        self.assertEqual(output,decorate([b,a,a]))

    def test_repeated_url_for_different_events_is_not_mislabeled(self):
        output=decorate([self.entry('https://example.org/tsn.m3u8'), self.entry('https://example.org/tsn.m3u8','Formula 1')])
        self.assertEqual(len(output), 2)
        self.assertEqual({e['display_name'] for e in output}, {'Detroit Lions vs Carolina Panthers', 'Formula 1'})
        self.assertEqual(len({e['tvg_id'] for e in output}), 2)

if __name__=='__main__': unittest.main()


