import tempfile
import unittest
from pathlib import Path

from scripts.build_model_v2_manifest import inventory, sha256_file


class ManifestTests(unittest.TestCase):
    def test_hash_and_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'faers.zip').write_bytes(b'abc')
            (root / 'notes.md').write_text('ignore')
            rows = inventory(root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['local_relative_path'], 'faers.zip')
            self.assertEqual(rows[0]['byte_size'], 3)
            self.assertEqual(rows[0]['sha256'], sha256_file(root / 'faers.zip'))


if __name__ == '__main__':
    unittest.main()