#!/usr/bin/env python3
"""Écrit zensical.<lang>.build.toml, la configuration réellement construite.

La navigation vit avec les pages, dans xolo-gateway/xolo (docs/<lang>/nav.toml),
pour qu'un déplacement de page et l'entrée de menu qui le suit partent dans le
même commit. scripts/prepare-source.sh la range sous content/.nav/<lang>.toml ;
ce script l'insère dans la configuration de la langue. Chaque entrée cite un
fichier .md relatif à docs/<lang>, comme le fait Zensical. Une version de Xolo
sans nav.toml garde la navigation déduite de l'arborescence.

La page « Trouver un expert » vient d'un troisième dépôt et peut manquer. Elle
n'est pas dans le menu : quand elle a été générée, ce script le signale au
thème (project.extra.experts_page), qui affiche son lien dans l'en-tête.
"""

import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

EXPERTS_PAGE = "experts.md"


def toml_value(value, indent=1):
    pad = "  " * indent
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, dict):
        items = ", ".join(
            f"{json.dumps(k, ensure_ascii=False)} = {toml_value(v, indent + 1)}"
            for k, v in value.items()
        )
        return "{ " + items + " }"
    if isinstance(value, list):
        lines = [f"{pad}{toml_value(v, indent + 1)}," for v in value]
        return "[\n" + "\n".join(lines) + "\n" + "  " * (indent - 1) + "]"
    raise TypeError(f"valeur de navigation inattendue : {value!r}")


def pages(nav):
    for item in nav:
        if isinstance(item, str):
            yield item
        elif isinstance(item, dict):
            for value in item.values():
                if isinstance(value, str):
                    yield value
                else:
                    yield from pages(value)


def project_header(lines, name):
    """Index de la ligne d'en-tête « [project] », hors des chaînes multi-lignes."""
    found = []
    quote = None
    for index, line in enumerate(lines):
        if quote is None and line.strip() == "[project]":
            found.append(index)
        for delimiter in ('"""', "'''"):
            if quote in (None, delimiter) and line.count(delimiter) % 2 == 1:
                quote = None if quote else delimiter
    if len(found) != 1:
        sys.exit(f"{name} : une seule table [project] est attendue")
    return found[0]


def with_experts(text, config, content):
    """Signale au thème que la page des experts existe, pour le lien d'en-tête."""
    # La clé est refusée même sans page : déclarée à la main, elle afficherait
    # un lien vers une page absente.
    if "experts_page" in config.get("project", {}).get("extra", {}):
        sys.exit("project.extra.experts_page est réservé à scripts/build-config.py")
    if not (content / EXPERTS_PAGE).is_file():
        return text
    return text.rstrip("\n") + (
        "\n\n# Ajouté par scripts/build-config.py : la page des experts a été générée.\n"
        '[project.extra.experts_page]\nlink = "experts/"\n'
    )


def build(lang):
    source = ROOT / f"zensical.{lang}.toml"
    target = ROOT / f"zensical.{lang}.build.toml"
    text = source.read_text(encoding="utf-8")
    content = ROOT / "content" / lang
    config = tomllib.loads(text)
    text = with_experts(text, config, content)
    nav_file = ROOT / "content" / ".nav" / f"{lang}.toml"
    if not nav_file.is_file():
        target.write_text(text, encoding="utf-8")
        return "navigation déduite de l'arborescence"

    with nav_file.open("rb") as handle:
        nav = tomllib.load(handle).get("nav")
    if not isinstance(nav, list) or not nav:
        sys.exit(f"{nav_file} : la clé nav doit être une liste non vide")

    missing = [p for p in pages(nav) if "://" not in p and not (content / p).is_file()]
    if missing:
        sys.exit(f"{nav_file} cite des pages absentes : {', '.join(missing)}")

    if "nav" in config.get("project", {}):
        sys.exit(f"{source.name} déclare déjà nav : retirez-la, elle vient de Xolo")

    # Insertion textuelle, pour garder les commentaires et la mise en forme du
    # fichier source : la navigation suit l'en-tête de la table [project].
    lines = text.splitlines(keepends=True)
    index = project_header(lines, source.name)
    block = (
        f"# Navigation insérée par scripts/build-config.py depuis "
        f"docs/{lang}/nav.toml de Xolo.\nnav = {toml_value(nav)}\n"
    )
    result = "".join(lines[: index + 1]) + block + "".join(lines[index + 1 :])
    if tomllib.loads(result)["project"].get("nav") != nav:
        sys.exit(f"{source.name} : la navigation insérée ne se relit pas à l'identique")
    target.write_text(result, encoding="utf-8")
    return f"navigation de Xolo, {sum(1 for _ in pages(nav))} pages"


def main():
    for lang in sys.argv[1:]:
        print(f"zensical.{lang}.build.toml : {build(lang)}")


if __name__ == "__main__":
    main()
