"""Location contract rejects ambiguous filters before touching persistence."""
import unittest

from pydantic import ValidationError

from KIDSic.dto.location import LocationCollection, LocationQuery


class LocationQueryTests(unittest.TestCase):
    def test_defaults_and_trimmed_filters(self):
        self.assertEqual(LocationQuery().city, 'Zagreb')
        query = LocationQuery(city=' Zagreb ', q=' Medo ', provider_kind='municipal')
        self.assertEqual((query.city, query.q), ('Zagreb', 'Medo'))
        self.assertEqual(LocationQuery(bbox=(15, 45, 16, 46)).bbox, (15, 45, 16, 46))

    def test_invalid_queries_are_rejected(self):
        for values in ({'city': 'Split'}, {'city': 'Osijek'}, {'city': 'Sesvete'},
                       {'city': ' '}, {'city': 'x' * 101}, {'q': 'x' * 201},
                       {'provider_kind': 'city'}, {'area': None}, {'area': ['Banfica']}, {'area': 'x' * 201}, {'limit': 1},
                       {'bbox': [15, 45, 16]}, {'bbox': [16, 45, 15, 46]},
                       {'bbox': [15, 46, 16, 45]}, {'bbox': [-181, 45, 16, 46]},
                       {'bbox': [15, -91, 16, 46]}, {'bbox': [15, 45, float('inf'), 46]},
                       {'bbox': [15, 45, float('nan'), 46]}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                LocationQuery(**values)

    def test_supported_names_and_aliases_are_accepted(self):
        for city in ('Zagreb', 'Varaždin', 'Varazdin', 'Rijeka', 'zagreba', 'varaždinu', 'rijeci'):
            with self.subTest(city=city):
                self.assertEqual(LocationQuery(city=city).city, city)

    def test_complete_empty_collection_serializes_as_geojson(self):
        result = LocationCollection(features=[], metadata={
            'total': 0, 'mapped': 0, 'unmapped': 0, 'scope': 'city',
        }).model_dump(mode='json')
        self.assertEqual(result['type'], 'FeatureCollection')
        self.assertTrue(result['metadata']['complete'])
        self.assertEqual(result['features'], [])
