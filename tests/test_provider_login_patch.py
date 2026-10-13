"""Linux source/patch regressions; NOT iOS runtime or compiler tests."""
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import tempfile
import unittest

BUILDER = Path(__file__).resolve().parents[1]
UPSTREAM = Path(os.environ.get('FUO_UPSTREAM', str(BUILDER.parent / 'FuoEvolve-upstream')))
KEYCHAIN = 'shared/src/iosMain/kotlin/org/feeluown/mobile/IosProviderCredentialStore.kt'
SWIFT = 'iosApp/FuoEvolve/IOSNativeAudioEngine.swift'

class ProviderLoginPatchTests(unittest.TestCase):
    def load_patch(self):
        script = BUILDER / 'scripts/patch-provider-login.py'
        self.assertTrue(script.exists(), 'provider login patch script is missing')
        spec = importlib.util.spec_from_file_location('patch_provider_login', script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_original_bad_cast_is_removed_by_real_patch(self):
        original = (UPSTREAM / KEYCHAIN).read_text()
        self.assertIn('attributes as platform.CoreFoundation.CFDictionaryRef', original)
        patch = self.load_patch()
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as directory:
            root = Path(directory)
            for name in (KEYCHAIN, SWIFT):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(UPSTREAM / name, root / name)
            patch.apply(root)
            result = (root / KEYCHAIN).read_text()
            self.assertNotIn(' as platform.CoreFoundation.CFDictionaryRef', result)
            for token in ('CFDictionaryCreateMutable', 'CFBridgingRetain', 'CFBridgingRelease', 'CFRelease', 'CFTypeRefVar', 'finally', 'SecItemUpdate'):
                self.assertIn(token, result)
            self.assertIn('if (includeData) {', result)
            self.assertIn('CFDictionaryAddValue(query, kSecMatchLimit, kSecMatchLimitOne)', result)
            self.assertNotIn('ObjCObjectVar', result)
            self.assertNotIn('NSUserDefaults', result)
            patched = {name: (root / name).read_bytes() for name in (KEYCHAIN, SWIFT)}
            with self.assertRaisesRegex(ValueError, 'Source layout drift'):
                patch.apply(root)
            self.assertEqual(patched, {name: (root / name).read_bytes() for name in patched})
            self.assertNotIn('kSecMatchLimit', result.split('override suspend fun write')[1].split('override suspend fun migrateLegacyIfNeeded')[0])

    def test_cookie_scope_and_completion_guards(self):
        patch = self.load_patch()
        result = patch.patch_swift((UPSTREAM / SWIFT).read_text())
        for token in ('providerId: providerId', 'WKHTTPCookieStoreObserver', 'WKUIDelegate',
                      'domain == root || domain.hasSuffix("." + root)',
                      'cookie.expiresDate', 'cookieDomainAllowed(cookie.domain)',
                      'didComplete', 'guard !self.didComplete',
                      'group.allSatisfy', '!group.isEmpty',
                      'collectCookies(manual: true)', 'collectCookies(manual: false)',
                      'customUserAgent', 'UIAlertController', 'presentationControllerDidDismiss',
                      'navigationAction.targetFrame == nil'):
            self.assertIn(token, result)
        controller = result.split('private final class FuoWebLoginViewController:')[1].split('final class IOSOAuthDeviceCodeOutput:')[0]
        self.assertNotIn('print(', controller)
        self.assertNotIn('URLSession', controller)
        self.assertIn('case "netease": return ["163.com"]', controller)
        self.assertIn('case "qqmusic": return ["qq.com"]', controller)
        self.assertIn('case "bilibili": return ["bilibili.com"]', controller)
        self.assertIn('default: return []', controller)

    def test_rejects_drift_before_writing_any_target(self):
        patch = self.load_patch()
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as directory:
            root = Path(directory)
            for name in (KEYCHAIN, SWIFT):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(UPSTREAM / name, root / name)
            (root / SWIFT).write_text((root / SWIFT).read_text() + '// drift\n')
            before = {name: (root / name).read_bytes() for name in (KEYCHAIN, SWIFT)}
            with self.assertRaisesRegex(ValueError, 'Source layout drift'):
                patch.apply(root)
            self.assertEqual(before, {name: (root / name).read_bytes() for name in before})

    def test_keeps_unrelated_audio_and_legacy_migration(self):
        patch = self.load_patch()
        swift = (UPSTREAM / SWIFT).read_text()
        updated = patch.patch_swift(swift)
        self.assertEqual(swift.split('final class IOSWebLoginOutput:')[0],
                         updated.split('final class IOSWebLoginOutput:')[0])
        self.assertEqual(swift.split('final class IOSOAuthDeviceCodeOutput:')[1],
                         updated.split('final class IOSOAuthDeviceCodeOutput:')[1])
        original = (UPSTREAM / KEYCHAIN).read_text()
        migration = original.split('    override suspend fun migrateLegacyIfNeeded()')[1].split('    private fun query(')[0]
        self.assertIn(migration, patch.patch_keychain(original))
        ua = updated.split('if providerId == "qqmusic" || providerId == "netease" {')[1].split('        }')[0]
        self.assertIn('customUserAgent', ua)
        self.assertNotIn('bilibili', ua)
        self.assertEqual(updated.count('webView.customUserAgent ='), 1)
        self.assertIn('providerId == "bilibili" ? .mobile : .desktop', updated)
        self.assertLess(updated.index('webView.customUserAgent ='), updated.index('webView.load(URLRequest(url: url))', updated.index('private final class FuoWebLoginViewController:')))

    def test_domain_guard_security_truth_table_static_model(self):
        # Model of the exact Swift predicate, not execution of WKWebView/Swift.
        result = self.load_patch().patch_swift((UPSTREAM / SWIFT).read_text())
        self.assertIn('domain == root || domain.hasSuffix("." + root)', result)
        import re
        roots = {provider: re.findall(r'"([^"]+)"', values)
                 for provider, values in re.findall(r'case "([^"]+)": return \[([^\]]+)\]', result)}
        def allowed(provider, raw):
            domain = raw.lower()
            if domain.startswith('.'):
                domain = domain[1:]
            return any(domain == root or domain.endswith('.' + root) for root in roots.get(provider, []))
        for provider, raw, expected in [
            ('bilibili', '.bilibili.com', True), ('bilibili', 'passport.bilibili.com', True),
            ('bilibili', 'BILIBILI.COM', True), ('bilibili', 'evilbilibili.com', False),
            ('bilibili', 'bilibili.com.evil.example', False), ('bilibili', '.qq.com', False),
            ('qqmusic', '.qq.com', True), ('qqmusic', 'ptlogin2.qq.com', True),
            ('qqmusic', 'evilqq.com', False), ('netease', 'music.163.com', True),
            ('netease', '163.com.evil.example', False), ('unknown', 'qq.com', False),
        ]:
            with self.subTest(provider=provider, raw=raw):
                self.assertEqual(allowed(provider, raw), expected)

    def test_workflow_applies_patch_before_build(self):
        workflow = (BUILDER / '.github/workflows/build-ipa.yml').read_text()
        self.assertIn('default: 7e271c262c6c5495be5d1b680748ac4ba9e5bf0e', workflow)
        self.assertLess(workflow.index('python3 scripts/patch-provider-login.py upstream'),
                        workflow.index('bash scripts/build-ipa.sh'))
        self.assertNotIn('push:', workflow)

if __name__ == '__main__':
    unittest.main()
