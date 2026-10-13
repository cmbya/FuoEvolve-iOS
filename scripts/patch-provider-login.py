#!/usr/bin/env python3
"""Apply narrow, hash-guarded iOS fixes to a disposable upstream checkout."""
import argparse
import hashlib
from pathlib import Path

PATCHES = Path(__file__).resolve().parents[1] / 'patches/provider-login'
KEYCHAIN = 'shared/src/iosMain/kotlin/org/feeluown/mobile/IosProviderCredentialStore.kt'
SWIFT = 'iosApp/FuoEvolve/IOSNativeAudioEngine.swift'
EXPECTED = {
    KEYCHAIN: '05e15c3c58da306116f21109af813a1e556f635f63d7cb1cd479b8e6608d222d',
    SWIFT: '4af3860c3f86a58898afc12d116223e0e00d15cce11a800265e3f004fec8aa39',
}

def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Source layout drift: expected exactly one replacement anchor')
    return source.replace(old, new, 1)

def replace_between(source, start, end, replacement):
    if source.count(start) != 1 or source.count(end) != 1:
        raise ValueError('Source layout drift: missing or ambiguous block boundary')
    begin, finish = source.index(start), source.index(end)
    if finish <= begin:
        raise ValueError('Source layout drift: reversed block boundaries')
    return source[:begin] + replacement + source[finish:]

def patch_keychain(source):
    source = replace_between(source, '@OptIn(', '    override suspend fun migrateLegacyIfNeeded()',
                             (PATCHES / 'keychain-operations.kt.fragment').read_text())
    source = replace_between(source, '    private fun query(', '    private companion object {',
                             (PATCHES / 'keychain-query.kt.fragment').read_text())
    source = replace_once(source, 'import kotlinx.cinterop.ObjCObjectVar\n', '')
    source = replace_once(source, 'import kotlinx.cinterop.reinterpret\n', '')
    source = replace_once(source, 'import platform.CoreFoundation.kCFBooleanTrue\n', '''import platform.CoreFoundation.kCFBooleanTrue
import platform.CoreFoundation.CFDictionaryCreateMutable
import platform.CoreFoundation.CFDictionaryAddValue
import platform.CoreFoundation.CFMutableDictionaryRef
import platform.CoreFoundation.CFTypeRef
import platform.CoreFoundation.CFTypeRefVar
import platform.CoreFoundation.CFRelease
import platform.Foundation.CFBridgingRetain
import platform.Foundation.CFBridgingRelease
''')
    return replace_once(source, 'import platform.Security.SecItemAdd\n',
                        'import platform.Security.SecItemAdd\nimport platform.Security.SecItemUpdate\n')

def patch_swift(source):
    source = replace_once(source, '            let login = FuoWebLoginViewController(\n',
                          '            let login = FuoWebLoginViewController(\n                providerId: providerId,\n')
    return replace_between(source, 'private final class FuoWebLoginViewController:',
                           'final class IOSOAuthDeviceCodeOutput:',
                           (PATCHES / 'web-login.swift.fragment').read_text())

def apply(root):
    root = Path(root)
    originals = {}
    # Preflight all inputs before writing any file. Never apply twice or accept drift.
    for relative, digest in EXPECTED.items():
        data = (root / relative).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f'Source layout drift: {relative}; expected pinned 7e271c2 source')
        originals[relative] = data.decode('utf-8')
    outputs = {KEYCHAIN: patch_keychain(originals[KEYCHAIN]), SWIFT: patch_swift(originals[SWIFT])}
    for relative, text in outputs.items():
        (root / relative).write_text(text)
    print('Applied provider login patches (source checks only; no compilation).')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    apply(parser.parse_args().upstream)
