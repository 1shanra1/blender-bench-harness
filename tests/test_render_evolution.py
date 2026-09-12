"""Check that evolution export uses valid chronological renders, not diagnostics."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from render_evolution import export_evolution


class EvolutionTests(unittest.TestCase):
    def test_filters_partial_crops_and_late_diagnostics_and_keeps_final(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            versions = root / 'capture/versions'
            versions.mkdir(parents=True)
            artifacts = root / 'capture/artifacts'
            artifacts.mkdir()
            assets = root / 'assets'
            assets.mkdir()
            rows = []
            for index, name in enumerate(['render_v1.png', 'crop.png', 'render_v2.png', 'render_alt.png', 'render.png', 'render_later_test.png']):
                image_path = root / 'image.png'
                Image.new('RGB', (10, 10), (index * 30, 0, 0)).save(image_path)
                data = image_path.read_bytes()
                if index == 2:
                    data = data[:40]  # Interrupted render write.
                digest = hashlib.sha256(data).hexdigest()
                (versions / digest).write_bytes(data)
                rows.append({'path': name, 'sha256': digest, 'observed_seconds': index * 10})
                if name == 'render.png':
                    (artifacts / name).write_bytes(data)
            (root / 'capture/trajectory.jsonl').write_text('\n'.join(map(json.dumps, rows)))
            frames = export_evolution(root, assets)
            self.assertEqual([f['elapsed_seconds'] for f in frames], [0, 40])
            self.assertEqual([f['final'] for f in frames], [False, True])
            for frame in frames:
                with Image.open(root / frame['src']) as image:
                    image.load()

    def test_missing_trajectory_is_empty(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(export_evolution(Path(temporary), Path(temporary)), [])

if __name__ == '__main__':
    unittest.main()
