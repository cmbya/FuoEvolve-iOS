"""Static regression checks for the release version contract (no Xcode required)."""
import ast
from pathlib import Path
import textwrap
import unittest


def resolver(workflow):
    label = '确认上游版本' if '      - name: 确认上游版本\n' in workflow else 'Resolve upstream version'
    return workflow.split(f'      - name: {label}\n', 1)[1].split('      - name: ', 1)[0]


class ReleaseVersionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = globals().get('WORKFLOW')
        if cls.workflow is None:
            cls.workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/build-ipa.yml').read_text()
        cls.step = resolver(cls.workflow)

    def test_release_version_is_not_reinferred_from_git_tags(self):
        self.assertNotIn('git describe', self.step)
        self.assertNotIn("['git','describe'", self.step)

    def test_selected_version_and_tag_are_explicit_inputs(self):
        self.assertIn('RESOLVED_TAG: ${{ needs.check.outputs.tag }}', self.step)
        self.assertIn('RESOLVED_VERSION: ${{ needs.check.outputs.version }}', self.step)
        self.assertIn('VERSION="$RESOLVED_VERSION"', self.step)

    def test_checkout_must_match_selected_tag(self):
        self.assertIn('git rev-parse HEAD', self.step)
        self.assertIn('refs/tags/${RESOLVED_TAG}^{commit}', self.step)
        self.assertIn('test "$(git rev-parse HEAD)" =', self.step)

    def test_plist_uses_selected_version_without_fallback(self):
        source = textwrap.dedent(self.step.split("python3 - <<'PY'\n", 1)[1].rsplit('          PY', 1)[0])
        tree = ast.parse(source)
        assignment = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Subscript)
                                  and isinstance(t.slice, ast.Constant)
                                  and t.slice.value == 'CFBundleShortVersionString'
                                  for t in n.targets))
        self.assertEqual(ast.dump(assignment.value), ast.dump(ast.parse("os.environ['RESOLVED_VERSION']", mode='eval').body))


if __name__ == '__main__':
    unittest.main()
