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
# Progress monitor is independent of compiler output; never kill an active build
# merely because the compiler is silent. Thread dumps aid stall diagnosis.
(
  tick=0
  while sleep 60; do
    tick=$((tick + 1))
    {
      echo "=== BUILD HEARTBEAT minute=$tick $(date -u) ==="
      ps -axo pid,ppid,%cpu,rss,etime,comm | python3 -c 'import sys; lines=sys.stdin.readlines(); print(lines[0].strip()); print("".join(l for l in lines[1:] if any(k in l.lower() for k in ["java", "konan", "clang", "swift", "xcodebuild"])))'
      vm_stat
      df -h "$ROOT"
    } | tee -a "$ROOT/logs/resources.log"
    if [ $((tick % 10)) -eq 0 ]; then
      jps -l > "$ROOT/logs/java-processes.txt" 2>&1 || true
      while read -r pid name; do
        case "$name" in
          *GradleDaemon*|*Kotlin*)
            jcmd "$pid" Thread.print > "$ROOT/logs/threads-${tick}-${pid}.txt" 2>&1 || true
            ;;
        esac
      done < "$ROOT/logs/java-processes.txt"
    fi
  done
) &
MONITOR_PID=$!
trap 'kill "$MONITOR_PID" 2>/dev/null || true' EXIT
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
