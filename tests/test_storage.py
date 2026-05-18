import os
import tempfile
import unittest
from pathlib import Path

from secondopinion.storage import resolve_artifact_path


class StorageTests(unittest.TestCase):
    def test_resolve_artifact_path_uses_explicit_root_for_data_and_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                resolve_artifact_path("data/raw/sample.json", root=tmp),
                Path(tmp) / "data/raw/sample.json",
            )
            self.assertEqual(
                resolve_artifact_path("reports/audit.html", root=tmp),
                Path(tmp) / "reports/audit.html",
            )

    def test_resolve_artifact_path_keeps_source_paths_local(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                resolve_artifact_path("examples/sample_normalized_dataset.json", root=tmp),
                Path("examples/sample_normalized_dataset.json"),
            )

    def test_resolve_artifact_path_uses_env_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous = os.environ.get("SECONDOPINION_STORAGE_ROOT")
            os.environ["SECONDOPINION_STORAGE_ROOT"] = tmp
            try:
                self.assertEqual(
                    resolve_artifact_path("data/derived/result.json"),
                    Path(tmp) / "data/derived/result.json",
                )
            finally:
                if previous is None:
                    os.environ.pop("SECONDOPINION_STORAGE_ROOT", None)
                else:
                    os.environ["SECONDOPINION_STORAGE_ROOT"] = previous


if __name__ == "__main__":
    unittest.main()
