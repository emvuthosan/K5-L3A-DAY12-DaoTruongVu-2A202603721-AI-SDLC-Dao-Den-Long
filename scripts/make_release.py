"""Builds the v1.0.0 release bundle: dist/dao-den-long-v1.0.0.zip (runnable: needs only Python 3.9+ and a browser).

  python3 scripts/make_release.py

Upload to GitHub with:  gh release create v1.0.0 dist/dao-den-long-v1.0.0.zip --title v1.0.0 --notes-file CHANGELOG.md
(or via the web UI: Releases > Draft a new release > tag v1.0.0 > attach the zip).
"""
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = "v1.0.0"
INCLUDE_FILES = ["README.md", "LICENSE", "CREDITS.md", "CHANGELOG.md", "game.contract.json", "play.sh", "play.bat"]
INCLUDE_DIRS = ["game", "docs/proof/phase4"]


def main():
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    out = os.path.join(ROOT, "dist", f"dao-den-long-{VERSION}.zip")
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in INCLUDE_FILES:
            z.write(os.path.join(ROOT, f), f"dao-den-long-{VERSION}/{f}")
            n += 1
        for d in INCLUDE_DIRS:
            for base, dirs, files in os.walk(os.path.join(ROOT, d)):
                dirs[:] = [x for x in dirs if x != "__pycache__"]
                for name in files:
                    if name.endswith((".pyc", ".tmp")):
                        continue
                    full = os.path.join(base, name)
                    z.write(full, f"dao-den-long-{VERSION}/" + os.path.relpath(full, ROOT).replace(os.sep, "/"))
                    n += 1
    print(f"{out} ({n} files, {os.path.getsize(out) // 1024} KB)")


if __name__ == "__main__":
    sys.exit(main())
