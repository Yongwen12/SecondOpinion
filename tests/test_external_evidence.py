import unittest

from secondopinion.external_evidence import (
    attach_external_evidence_to_paper,
    collect_external_evidence_for_claims,
    deterministic_plan,
    enrich_dataset_with_external_evidence,
)


class FakeOpenAlexClient:
    def __init__(self):
        self.queries = []

    def search_works(self, query, *, per_page=5, year_lte=None):
        self.queries.append({"query": query, "per_page": per_page, "year_lte": year_lte})
        return [
            {
                "id": "https://openalex.org/W1",
                "doi": "https://doi.org/10.0000/example",
                "title": "Retrieval Baselines for Evidence Grounded Reasoning",
                "abstract": "This paper compares BM25, dense retrieval, and cross encoder baselines for evidence grounded reasoning.",
                "publication_year": 2022,
                "publication_date": "2022-05-01",
                "cited_by_count": 42,
                "url": "https://openalex.org/W1",
            }
        ]

    def stats_dict(self):
        return {"network_requests": len(self.queries)}


class FakeClaimClient:
    def complete_json(self, *, model, messages, schema_name, schema):
        return {
            "claims": [
                {
                    "claim_text": "The paper lacks comparison to standard retrieval baselines.",
                    "claim_type": "baseline",
                    "importance": "major",
                    "source_field": "weaknesses",
                    "source_sentence": "The paper lacks comparison to standard retrieval baselines.",
                    "rationale": "The reviewer criticizes baseline coverage.",
                }
            ]
        }


class ExternalEvidenceTests(unittest.TestCase):
    def test_deterministic_plan_selects_baseline_claim(self):
        paper = {
            "title": "Modular Retrieval Networks",
            "abstract": "We compare retrieval models for reasoning.",
            "venue": "ICLR",
            "year": 2024,
        }
        claims = [
            {
                "claim_text": "The paper lacks comparison to standard retrieval baselines.",
                "claim_type": "baseline",
                "importance": "major",
            },
            {
                "claim_text": "The writing is clear.",
                "claim_type": "writing",
                "importance": "minor",
            },
        ]
        plan = deterministic_plan(paper, claims)
        self.assertTrue(plan[0]["needs_external_evidence"])
        self.assertFalse(plan[1]["needs_external_evidence"])
        self.assertTrue(plan[0]["queries"])

    def test_collect_external_evidence_uses_guidelines_and_openalex(self):
        paper = {
            "paper_id": "p1",
            "title": "Modular Retrieval Networks",
            "abstract": "We compare retrieval models for reasoning.",
            "venue": "ICLR",
            "year": 2024,
        }
        claims = [
            {
                "claim_text": "The paper lacks comparison to standard retrieval baselines.",
                "claim_type": "baseline",
                "importance": "major",
            }
        ]
        openalex = FakeOpenAlexClient()
        records, manifest = collect_external_evidence_for_claims(
            paper,
            claims,
            providers=("venue_guidelines", "openalex"),
            llm_client=None,
            openalex_client=openalex,
        )
        self.assertGreaterEqual(manifest["record_count"], 2)
        self.assertTrue(any(record["source_type"] == "venue_guideline" for record in records))
        self.assertTrue(any(record["source_type"] == "external_reference" for record in records))
        self.assertEqual(openalex.queries[0]["year_lte"], 2024)
        self.assertIn("openalex_stats", manifest)

    def test_attach_external_evidence_to_paper_sections(self):
        paper = {"paper_sections": []}
        records = [
            {
                "source_type": "external_reference",
                "section": "OpenAlex related paper: Retrieval Baselines",
                "page": None,
                "text": "Retrieval baselines include BM25.",
                "metadata": {"stable_id": "W1"},
            }
        ]
        updated = attach_external_evidence_to_paper(paper, records)
        self.assertEqual(len(updated["paper_sections"]), 1)
        self.assertEqual(paper["paper_sections"], [])

    def test_enrich_dataset_with_external_evidence_adds_manifest(self):
        dataset = {
            "dataset": "sample",
            "papers": [
                {
                    "paper_id": "p1",
                    "title": "Modular Retrieval Networks",
                    "abstract": "We compare retrieval models for reasoning.",
                    "venue": "ICLR",
                    "year": 2024,
                    "reviews": [
                        {
                            "review_id": "r1",
                            "weaknesses": "The paper lacks comparison to standard retrieval baselines.",
                        }
                    ],
                }
            ],
        }
        enriched, manifest = enrich_dataset_with_external_evidence(
            dataset,
            claim_llm_client=FakeClaimClient(),
            collector_llm_client=None,
            providers=("venue_guidelines",),
        )
        self.assertEqual(manifest["provider_counts"]["venue_guidelines"], 1)
        self.assertEqual(enriched["external_evidence"]["record_count"], 1)
        self.assertIn("openalex_stats", enriched["external_evidence"])
        self.assertEqual(enriched["papers"][0]["paper_sections"][0]["source_type"], "venue_guideline")


if __name__ == "__main__":
    unittest.main()
