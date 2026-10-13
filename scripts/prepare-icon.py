"""Add upstream's icon to the iOS asset catalog, failing on layout drift."""
import json
import struct
import sys
from pathlib import Path

root = Path(sys.argv[1])
assets = root / 'iosApp/FuoEvolve/Assets.xcassets'
icon = assets / 'AppIcon.appiconset'
icon.mkdir(parents=True, exist_ok=True)
blob = (root / 'desktopApp/packaging/icons/fuoevolve.icns').read_bytes()
assert blob[:4] == b'icns'
pos = 8
found = False
while pos < len(blob):
    tag = blob[pos:pos+4]
    length = struct.unpack('>I', blob[pos+4:pos+8])[0]
    assert length >= 8 and pos+length <= len(blob)
    if tag == b'ic10':
        png = blob[pos+8:pos+length]
        assert png[:8] == b'\x89PNG\r\n\x1a\n'
        assert struct.unpack('>II', png[16:24]) == (1024, 1024)
        (icon/'source.png').write_bytes(png)
        found = True
    pos += length
assert found, 'Upstream 1024px icon missing'
(assets/'Contents.json').write_text(json.dumps({'info': {'author': 'xcode', 'version': 1}}))
(icon/'Contents.json').write_text(json.dumps({'images': [{'filename': 'AppIcon.png', 'idiom': 'universal', 'platform': 'ios', 'size': '1024x1024'}], 'info': {'author': 'xcode', 'version': 1}}))
p = root/'iosApp/FuoEvolve.xcodeproj/project.pbxproj'
s = p.read_text()
def insert(marker, text):
    global s
    assert s.count(marker) == 1, f'Project layout drift: {marker}'
    s = s.replace(marker, text + '\n' + marker)
insert('/* End PBXBuildFile section */', '        B10000000000000000000001 = {isa = PBXBuildFile; fileRef = B10000000000000000000002; };')
insert('/* End PBXFileReference section */', '        B10000000000000000000002 = {isa = PBXFileReference; lastKnownFileType = folder.assetcatalog; path = Assets.xcassets; sourceTree = "<group>"; };')
marker = '                A10000000000000000011 /* FuoEvolveApp.swift */,'
assert s.count(marker) == 1
s = s.replace(marker, '                B10000000000000000000002 /* Assets.xcassets */,\n' + marker)
marker = '                A10000000000000000020 /* Frameworks */,'
assert s.count(marker) == 1
s = s.replace(marker, marker + '\n                B10000000000000000000003 /* Resources */,')
insert('/* Begin PBXGroup section */', '/* Begin PBXResourcesBuildPhase section */\n        B10000000000000000000003 = {isa = PBXResourcesBuildPhase; buildActionMask = 2147483647; files = (B10000000000000000000001,); runOnlyForDeploymentPostprocessing = 0; };\n/* End PBXResourcesBuildPhase section */')
assert 'ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;' in s
p.write_text(s)
print('Prepared upstream 1024px icon and asset catalog resource phase')
