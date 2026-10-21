import unittest
from unittest.mock import patch
import artwork

class ArtworkTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(artwork, "ppv_posters", return_value=[])
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_exact_channel_then_league_then_existing_fallback(self):
        entries = [dict(name='ESPN', group='Live', poster='assets/logos/live.png'),
                   dict(name='Team A vs Team B', group='NBA', poster='assets/logos/nba.png'),
                   dict(name='FSP — Shared Feed', group='Soccer', poster='assets/logos/soccer.png')]
        with patch.object(artwork, 'channel_logos', return_value={'espn': 'https://example.test/espn.png'}), patch.object(
            artwork, 'league_logo', side_effect=lambda group: 'https://example.test/nba.png' if group == 'NBA' else ''
        ):
            artwork.enrich(entries)
        self.assertEqual(entries[0]['artwork_source'], 'iptv-org')
        self.assertEqual(entries[1]['artwork_source'], 'thesportsdb')
        self.assertEqual(entries[2]['poster'], 'assets/logos/soccer.png')

    def test_existing_event_artwork_is_preserved(self):
        entries = [dict(name='Game', group='NBA', poster='https://example.test/event.png')]
        with patch.object(artwork, 'channel_logos', return_value={}), patch.object(artwork, 'league_logo') as lookup:
            artwork.enrich(entries)
        lookup.assert_not_called()
        self.assertEqual(entries[0]['poster'], 'https://example.test/event.png')

    def test_no_entries_do_not_fetch_artwork(self):
        with patch.object(artwork, 'channel_logos') as lookup:
            self.assertEqual(artwork.enrich([]), [])
        lookup.assert_not_called()

