import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.sample_dossier import build_sample_dossier


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'render_dossier_report.py'


class RenderDossierReportTests(unittest.TestCase):
    def test_render_outputs_single_report_document(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            dossier_path = tmp_path / 'dossier.json'
            output_path = tmp_path / 'report.md'
            dossier_path.write_text(json.dumps(build_sample_dossier(), ensure_ascii=False, indent=2), encoding='utf-8')

            result = subprocess.run(
                ['python3', str(SCRIPT), '--input', str(dossier_path), '--output', str(output_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + '\n' + result.stderr)
            self.assertTrue(output_path.exists())

            rendered = output_path.read_text(encoding='utf-8')
            self.assertIn('# Example Corp 投资研究报告', rendered)
            self.assertIn('## 执行摘要', rendered)
            self.assertIn('### 公司画像', rendered)
            self.assertIn('### 支撑判断', rendered)
            self.assertIn('## 研究过程', rendered)
            self.assertIn('## 来源附录', rendered)
            self.assertIn('截至 2026-04-13。', rendered)
            self.assertIn('### 核心管理层', rendered)
            self.assertIn('[来源 000](https://example.com/source/000)', rendered)


if __name__ == '__main__':
    unittest.main()
