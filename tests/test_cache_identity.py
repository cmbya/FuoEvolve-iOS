import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).resolve().parents[1] / 'scripts/cache-identity.py'
spec = importlib.util.spec_from_file_location('cache_identity', p)
assert spec is not None and spec.loader is not None
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class CacheIdentityTests(unittest.TestCase):
    def test_changed_commit_can_restore_compatible_outputs(self):
        a, ap = m.identity('old', 'tools', 'X64', 'patches', 'gradle')
        b, bp = m.identity('new', 'tools', 'X64', 'patches', 'gradle')
        self.assertNotEqual(a, b)
        self.assertEqual(ap, bp)
        self.assertTrue(a.startswith(bp))

    def test_incompatible_toolchain_or_policy_cannot_restore(self):
        args = ['sha', 'tools', 'X64', 'patches', 'gradle']
        base = m.identity(*args)[1]
        for index in range(1, 5):
            changed = args.copy()
            changed[index] += '-changed'
            self.assertNotEqual(base, m.identity(*changed)[1])

    def test_workflow_preserves_validation_and_success_only_save(self):
        text = (p.parents[1] / '.github/workflows/build-ipa.yml').read_text()
        self.assertIn('restore-keys: ${{ steps.build-cache.outputs.prefix }}', text)
        self.assertIn('bash scripts/build-ipa.sh', text)
        self.assertIn("if: success() && steps.outputs-cache.outputs.cache-hit != 'true'", text)
        self.assertNotIn('kotlin.incremental.native=true', text)

if __name__ == '__main__':
    unittest.main()
