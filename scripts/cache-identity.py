"""Compatible outputs are hints only; Gradle must validate task inputs."""
import hashlib
import os
import subprocess
from pathlib import Path


def digest_files(root, patterns):
    paths = sorted({p for pattern in patterns for p in root.glob(pattern) if p.is_file()})
    h = hashlib.sha256()
    for p in paths:
        h.update(str(p.relative_to(root)).encode() + b'\0' + p.read_bytes() + b'\0')
    return h.hexdigest()


def identity(source, tools, architecture, patches, build_inputs):
    compatibility = hashlib.sha256((tools + '\0' + architecture + '\0' + patches + '\0' + build_inputs).encode()).hexdigest()
    prefix = 'ios-modules-v2-' + compatibility + '-'
    return prefix + source, prefix


if __name__ == '__main__':
    root = Path.cwd()
    upstream = root / 'upstream'
    sha = subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip()
    tools = subprocess.check_output(['xcodebuild', '-version'], text=True)
    tools += subprocess.check_output(['java', '-version'], stderr=subprocess.STDOUT, text=True)
    tools += subprocess.check_output(['xcodebuild', '-showsdks'], text=True)
    patches = digest_files(root, ['patches/**/*', 'scripts/patch-provider-login.py', 'scripts/prepare-icon.py', 'scripts/build-ipa.sh'])
    inputs = digest_files(upstream, ['**/*.gradle.kts', '**/*.gradle', '**/gradle.properties', 'gradle/**/*.toml', 'gradle/wrapper/*'])
    # Build policy is deliberately separate from workflow formatting/Release logic.
    inputs += '|iphoneos-arm64-Release|heap8g-workers2|cache-policy-v2'
    key, prefix = identity(sha, tools, os.environ['RUNNER_ARCH'], patches, inputs)
    with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
        f.write('key=' + key + '\nprefix=' + prefix + '\n')
    print('Source:', sha, '\nExact key:', key, '\nCompatible prefix:', prefix)
