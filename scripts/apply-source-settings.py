#!/usr/bin/env python3
"""Sort de content/<lang> les fichiers de réglage livrés avec les pages.

Usage : apply-source-settings.py <content_dir> <lang>

- nav.toml, la navigation, est rangé sous content/.nav/<lang>.toml pour
  scripts/build-config.py, et ne doit pas être publié.
- redirects.txt liste les pages déplacées, une par ligne : « ancien/chemin/
  nouveau/chemin/ ». Chaque ligne devient une page à l'ancienne adresse qui
  renvoie vers la nouvelle (gabarit overrides/redirect.html), pour que les
  liens vers /latest/ et /main/ posés avant le déplacement tiennent toujours.
"""

import sys
from pathlib import Path
from posixpath import relpath


def main():
    content = Path(sys.argv[1])
    lang = sys.argv[2]
    docs = content / lang

    nav_target = content / ".nav" / f"{lang}.toml"
    nav_target.unlink(missing_ok=True)
    nav = docs / "nav.toml"
    if nav.is_file():
        nav_target.parent.mkdir(parents=True, exist_ok=True)
        nav.replace(nav_target)

    redirects = docs / "redirects.txt"
    if not redirects.is_file():
        return
    count = 0
    for number, line in enumerate(redirects.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2 or any(not p.endswith("/") or p.startswith("/") for p in parts):
            sys.exit(f"{redirects}:{number} : attendu « ancien/chemin/ nouveau/chemin/ »")
        # Une page de redirection s'écrit sous l'ancien chemin : il ne doit pas
        # sortir de docs/<lang>.
        if any(part in ("", ".", "..") for p in parts for part in p.rstrip("/").split("/")):
            sys.exit(f"{redirects}:{number} : chemin relatif interdit (., .. ou //)")
        old, new = parts
        page = docs / old / "index.md"
        if page.exists() or (docs / (old.rstrip("/") + ".md")).exists():
            sys.exit(f"{redirects}:{number} : {old} est encore une page")
        if not (docs / new / "index.md").is_file() and not (docs / (new.rstrip("/") + ".md")).is_file():
            sys.exit(f"{redirects}:{number} : la cible {new} n'existe pas")
        page.parent.mkdir(parents=True, exist_ok=True)
        target = relpath(new, old) + "/"
        page.write_text(
            "---\n"
            "template: redirect.html\n"
            f"redirect: {target}\n"
            "search:\n  exclude: true\n"
            "---\n\n"
            f"# Page déplacée\n\n[{new}]({target})\n",
            encoding="utf-8",
        )
        count += 1
    redirects.unlink()
    print(f"{lang} : {count} redirections")


if __name__ == "__main__":
    main()
