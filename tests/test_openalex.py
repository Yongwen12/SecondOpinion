import json
import unittest
from tempfile import TemporaryDirectory

from secondopinion.external_providers.openalex import OpenAlexClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class OpenAlexClientTests(unittest.TestCase):
    def test_search_works_caches_openalex_response(self):
        calls = []
        payload = {
            "results": [
                {
                    "id": "https://openalex.org/W1",
                    "doi": "https://doi.org/10.0000/example",
                    "display_name": "Retrieval Baselines",
                    "publication_year": 2022,
                    "publication_date": "2022-01-01",
                    "cited_by_count": 5,
                    "abstract_inverted_index": {
                        "Retrieval": [0],
                        "baselines": [1],
                        "include": [2],
                        "BM25": [3],
                    },
                    "primary_location": {"landing_page_url": "https://example.org/paper"},
                }
            ]
        }

        def fake_urlopen(request, timeout):
            calls.append(request.full_url)
            return FakeResponse(payload)

        with TemporaryDirectory() as tmp:
            client = OpenAlexClient(cache_root=tmp, urlopen_func=fake_urlopen)
            first = client.search_works("retrieval baseline", per_page=1, year_lte=2024)
            second = client.search_works("retrieval baseline", per_page=1, year_lte=2024)

        self.assertEqual(len(calls), 1)
        self.assertEqual(first[0]["title"], "Retrieval Baselines")
        self.assertEqual(second[0]["abstract"], "Retrieval baselines include BM25")
        self.assertEqual(client.stats_dict()["network_requests"], 1)
        self.assertEqual(client.stats_dict()["cache_hits"], 1)

    def test_offline_cache_mode_uses_cached_response(self):
        payload = {
            "results": [
                {
                    "id": "https://openalex.org/W2",
                    "display_name": "Cached Work",
                    "publication_year": 2021,
                    "publication_date": "2021-01-01",
                    "abstract_inverted_index": {"Cached": [0], "abstract": [1]},
                    "primary_location": {},
                }
            ]
        }

        with TemporaryDirectory() as tmp:
            writer = OpenAlexClient(cache_root=tmp, urlopen_func=lambda request, timeout: FakeResponse(payload))
            writer.search_works("cached query", per_page=1, year_lte=2024)

            offline = OpenAlexClient(cache_root=tmp, offline=True)
            works = offline.search_works("cached query", per_page=1, year_lte=2024)

        self.assertEqual(works[0]["title"], "Cached Work")
        self.assertEqual(offline.stats_dict()["cache_hits"], 1)


if __name__ == "__main__":
    unittest.main()
