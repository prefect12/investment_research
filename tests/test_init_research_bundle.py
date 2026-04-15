import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'init_research_bundle.py'


class InitResearchBundleTests(unittest.TestCase):
    def test_env_default_base_dir_is_used(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env = os.environ.copy()
            env['CODEX_EQUITY_DOSSIERS_DIR'] = tmpdir
            result = subprocess.run(
                [
                    'python3',
                    str(SCRIPT),
                    '--company',
                    'Example Corp',
                    '--ticker',
                    'EXM',
                    '--exchange',
                    'NASDAQ',
                    '--research-date',
                    '2026-04-13',
                ],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + '\n' + result.stderr)
            self.assertIn(tmpdir, result.stdout)
            self.assertIn('[完成] bundle:', result.stdout)


if __name__ == '__main__':
    unittest.main()
