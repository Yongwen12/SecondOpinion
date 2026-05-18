import tempfile
import unittest
from pathlib import Path

from secondopinion.pdf_store import attach_pdf_chunks, chunk_page_text, pdf_store_dir


class PdfStoreTests(unittest.TestCase):
    def test_chunk_page_text_tracks_sections_and_appendix(self):
        chunks, section = chunk_page_text(
            paper_id="paper1",
            page=2,
            text=(
                "1 Introduction\n"
                "This paper studies review auditing.\n\n"
                "Appendix A Extra Details\n"
                "The appendix includes ablations and tables."
            ),
            initial_section="Unknown",
            max_chars=200,
        )
        self.assertEqual(section, "Appendix")
        self.assertEqual(chunks[0]["section"], "1 Introduction")
        self.assertEqual(chunks[-1]["source_type"], "appendix")

    def test_chunk_page_text_detects_heading_inside_pdf_block(self):
        chunks, section = chunk_page_text(
            paper_id="paper1",
            page=1,
            text=(
                "Under review as a conference paper at ICLR\n"
                "ABSTRACT\n"
                "We study whether review claims are grounded in paper evidence."
            ),
            initial_section="Unknown",
            max_chars=200,
        )
        self.assertEqual(section, "Abstract")
        self.assertEqual(chunks[-1]["section"], "Abstract")
        self.assertIn("review claims", chunks[-1]["text"])

    def test_attach_pdf_chunks_uses_manifest_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_path = root / "paper1.pdf"
            pdf_path.write_bytes(b"%PDF fake")
            dataset = {
                "dataset": "test",
                "source_snapshot": {
                    "source": "openreview",
                    "venue": "ICLR",
                    "year": 2024,
                    "snapshot_id": "snapshot"
                },
                "papers": [{"paper_id": "paper1"}]
            }
            manifest = {
                "pdf_root": str(root),
                "entries": [{"paper_id": "paper1", "path": "paper1.pdf", "status": "ok"}]
            }

            def fake_extractor(path, paper_id):
                self.assertEqual(Path(path), pdf_path)
                return [
                    {
                        "paper_id": paper_id,
                        "source_type": "paper",
                        "section": "Abstract",
                        "page": 1,
                        "block_type": "paragraph",
                        "text": "Evidence text.",
                        "parser_version": "test",
                    }
                ]

            enriched = attach_pdf_chunks(dataset, manifest, extractor=fake_extractor)
            self.assertEqual(enriched["evidence_store"]["chunk_count"], 1)
            self.assertEqual(enriched["papers"][0]["paper_sections"][0]["text"], "Evidence text.")

    def test_pdf_store_dir_uses_snapshot_metadata(self):
        dataset = {
            "dataset": "iclr_2024",
            "source_snapshot": {
                "source": "openreview",
                "venue": "ICLR",
                "year": 2024,
                "snapshot_id": "20260518T000000Z"
            },
        }
        self.assertEqual(
            str(pdf_store_dir(dataset, "data/pdfs")),
            "data/pdfs/openreview/iclr/2024/20260518T000000Z",
        )


if __name__ == "__main__":
    unittest.main()
