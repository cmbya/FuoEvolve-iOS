#!/usr/bin/env bash
set -euo pipefail
ROOT="$(pwd)"
mkdir -p "$ROOT/logs" "$ROOT/output"
cd "$ROOT/upstream"
git show-ref --verify --quiet refs/heads/master || git branch master origin/master
SHA="$(git rev-parse HEAD)"
{
  echo "upstream=feeluown/FuoEvolve"
  echo "commit=$SHA"
  xcodebuild -version
  java -version 2>&1
} | tee "$ROOT/logs/environment.txt"
xcodebuild -project iosApp/FuoEvolve.xcodeproj -scheme FuoEvolve \
  -configuration Release -sdk iphoneos -destination 'generic/platform=iOS' \
  -derivedDataPath "$ROOT/build" ARCHS=arm64 ONLY_ACTIVE_ARCH=YES \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY='' \
  build 2>&1 | tee "$ROOT/logs/xcodebuild.log"
APP="$ROOT/build/Build/Products/Release-iphoneos/FuoEvolve.app"
test -d "$APP"
EXEC=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$APP/Info.plist")
test -s "$APP/$EXEC"
xcrun lipo "$APP/$EXEC" -verify_arch arm64
xcrun vtool -show-build "$APP/$EXEC" | tee "$ROOT/logs/macho-platform.txt"
grep -Eq 'platform[[:space:]]+IOS$' "$ROOT/logs/macho-platform.txt"
mkdir -p "$ROOT/package/Payload"
ditto "$APP" "$ROOT/package/Payload/FuoEvolve.app"
IPA="$ROOT/output/FuoEvolve-${SHA:0:12}-unsigned.ipa"
(cd "$ROOT/package" && zip -qry -y "$IPA" Payload)
unzip -t "$IPA" > "$ROOT/logs/zip-check.txt"
cp "$ROOT/logs/environment.txt" "$ROOT/output/build-info.txt"
shasum -a 256 "$IPA" > "$ROOT/output/SHA256SUMS.txt"
echo "Unsigned iPhone device IPA: $IPA"
