from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []

required = [
    "README.md",
    "settings.gradle.kts",
    "build.gradle.kts",
    "app/build.gradle.kts",
    "app/src/main/java/app/subloka/MainActivity.kt",
    "feature/editor/src/main/java/app/subloka/feature/editor/EditorScreen.kt",
    ".agents/plan.md",
    ".agents/testing.md",
]
for rel in required:
    if not (ROOT / rel).exists():
        errors.append(f"missing required file: {rel}")

settings = (ROOT / "settings.gradle.kts").read_text(encoding="utf-8")
for module in [":app", ":core:domain", ":core:designsystem", ":feature:projects", ":feature:editor", ":feature:export"]:
    if f'include("{module}")' not in settings:
        errors.append(f"module not included: {module}")

all_kt = "\n".join(path.read_text(encoding="utf-8") for path in ROOT.rglob("*.kt"))
if "BottomNavigation" in all_kt or "NavigationBar(" in all_kt:
    errors.append("MVP must not use bottom navigation")
if "Translation" in re.findall(r'EditorWorkspace\.([A-Z_]+)', all_kt):
    errors.append("translation must not be an editor workspace")
for label in ["Caption", "Timing", "Style"]:
    if label.upper() not in all_kt:
        errors.append(f"workspace missing: {label}")
if "DEMO · engine belum terhubung" not in all_kt:
    errors.append("demo disclosure missing")

manifest = (ROOT / "app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
if 'android:allowBackup="false"' not in manifest:
    errors.append("allowBackup must be false for MVP baseline")

if errors:
    print("FAIL")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("PASS")
print(f"Kotlin files: {len(list(ROOT.rglob('*.kt')))}")
print(f"Project files: {len([p for p in ROOT.rglob('*') if p.is_file()])}")
print("Guardrails: no bottom navigation; Caption/Timing/Style present; demo disclosure present; backup disabled")
