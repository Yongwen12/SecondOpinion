import os
import tempfile
import unittest
from pathlib import Path

from secondopinion.llm_client import load_dotenv


class LLMClientTests(unittest.TestCase):
    def test_load_dotenv_sets_missing_values_without_overriding_existing(self):
        previous_key = os.environ.get("OPENAI_API_KEY")
        previous_model = os.environ.get("SECONDOPINION_CLAIM_MODEL")
        os.environ["OPENAI_API_KEY"] = "existing"
        os.environ.pop("SECONDOPINION_CLAIM_MODEL", None)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / ".env"
                path.write_text(
                    "\n".join(
                        [
                            "OPENAI_API_KEY=from-file",
                            "SECONDOPINION_CLAIM_MODEL='claim-model'",
                        ]
                    ),
                    encoding="utf-8",
                )
                load_dotenv(path)
            self.assertEqual(os.environ["OPENAI_API_KEY"], "existing")
            self.assertEqual(os.environ["SECONDOPINION_CLAIM_MODEL"], "claim-model")
        finally:
            if previous_key is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = previous_key
            if previous_model is None:
                os.environ.pop("SECONDOPINION_CLAIM_MODEL", None)
            else:
                os.environ["SECONDOPINION_CLAIM_MODEL"] = previous_model


if __name__ == "__main__":
    unittest.main()
