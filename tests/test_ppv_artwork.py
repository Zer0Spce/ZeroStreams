import unittest
from unittest.mock import patch
import artwork

class PPVArtworkTests(unittest.TestCase):
    def test_same_event_and_date_uses_poster_without_changing_stream(self):
        entry = dict(name='Philadelphia 76ers vs New York Knicks', group='NBA',
                     starts_at=1792537200, url='https://original.test/feed.m3u8', poster='placeholder')
        posters = [(artwork.event_name('Philadelphia 76ers vs. New York Knicks'),
                    artwork.event_day(1792537200), 'Basketball', 'https://example.test/match.jpg')]
        with patch.object(artwork, 'ppv_posters', return_value=posters), patch.object(artwork, 'channel_logos', return_value={}):
            artwork.enrich([entry])
        self.assertEqual(entry['poster'], 'https://example.test/match.jpg')
        self.assertEqual(entry['artwork_source'], 'ppv')
        self.assertEqual(entry['url'], 'https://original.test/feed.m3u8')

    def test_other_date_or_ambiguous_images_do_not_match(self):
        entry = dict(name='Team A vs Team B', group='NBA', starts_at=1792537200)
        name, date = artwork.event_name(entry['name']), artwork.event_day(entry['starts_at'])
        self.assertEqual(artwork.ppv_poster(entry, [(name, None, 'Basketball', 'https://example.test/a.jpg')]), '')
        self.assertEqual(artwork.ppv_poster(entry, [(name, date, 'Basketball', 'https://example.test/a.jpg'),
                                                 (name, date, 'Basketball', 'https://example.test/b.jpg')]), '')
