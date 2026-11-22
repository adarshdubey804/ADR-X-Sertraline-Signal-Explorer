"""Unit tests for the read-only Model v2 data audit utility."""
import tempfile
import unittest
from pathlib import Path

from scripts.audit_model_v2_data import discover_files, normalize_column, profile_file, sniff_delimiter


class AuditUtilityTests(unittest.TestCase):
    def test_normalize_column(self):
        self.assertEqual(normalize_column("CASE_ID"), "caseid")
        self.assertEqual(normalize_column("FDA_DT"), "fda_dt".replace("_", ""))

    def test_discovers_supported_files_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "DEMO.txt").write_text("CASEID$FDA_DT\n1$20250101\n", encoding="utf-8")
            (root / "notes.md").write_text("not a table", encoding="utf-8")
            self.assertEqual([p.name for p in discover_files(root)], ["DEMO.txt"])

    def test_profiles_faers_like_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "DEMO.txt"
            source.write_text(
                "CASEID$PRIMARYID$FDA_DT$AGE$SEX\n"
                "10$100$20250101$42$F\n"
                "11$101$20250201$55$M\n",
                encoding="utf-8",
            )
            result = profile_file(source, root)
            self.assertEqual(result["rows"], 2)
            self.assertEqual(result["detected_fields"]["case_id"], "CASEID")
            self.assertEqual(result["report_date"]["min"], "2025-01-01T00:00:00")
            self.assertEqual(result["report_date"]["max"], "2025-02-01T00:00:00")

    def test_delimiter_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "x.txt"
            source.write_text("A$B\n1$2\n", encoding="utf-8")
            self.assertEqual(sniff_delimiter(source), "$")


if __name__ == "__main__":
    unittest.main()
