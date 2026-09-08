#!/usr/bin/env python3

"""Génère la page « Trouver un expert » d'une langue à partir des fiches YAML.

Les fiches vivent dans xolo-gateway/org, un fichier par entreprise ; les
libellés de la page vivent dans [project.extra.experts] de
zensical.<lang>.toml, comme le reste des textes propres à ce dépôt.

La page est écrite en HTML plutôt qu'en Markdown : les cartes n'ont pas
d'équivalent Markdown, et le rendu ne dépend alors d'aucune extension.
"""

from __future__ import annotations

import argparse
import html
import shutil
import sys
import tomllib
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import yaml

# Le dossier des logos, sous content/<lang>/ ; le nom est repris tel quel dans
# l'URL de la page publiée.
LOGO_DIRECTORY = Path("experts") / "logos"
PAGE_NAME = "experts.md"

DEFAULT_WEIGHT = 100
FALLBACK_LANGUAGE = "fr"

DEFAULT_LABELS = {
    "title": "Trouver un expert",
    "sponsor": "Sponsor",
    "website": "Site web",
    "empty": "Aucune entreprise n'est référencée pour le moment.",
}


class ExpertError(Exception):
    """Fiche inutilisable : le message dit quoi corriger, et où."""


@dataclass(frozen=True)
class Expert:
    slug: str
    name: str
    url: str
    description: str
    sponsor: bool
    weight: int
    logo: str | None
    logo_source: Path | None

    @property
    def sort_key(self) -> tuple[int, int, str]:
        # Les sponsors d'abord, puis le poids croissant, puis le nom.
        return (0 if self.sponsor else 1, self.weight, self.name.casefold())


def parse_expert(path: Path, language: str) -> Expert | None:
    """Lit une fiche. Rend None si elle est désactivée."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ExpertError(f"{path.name} : YAML illisible ({error}).") from error

    if not isinstance(raw, dict):
        raise ExpertError(f"{path.name} : le fichier doit contenir un objet YAML.")

    # Testé avant le reste : une fiche désactivée peut être un brouillon
    # incomplet, ce n'est pas au build de s'en plaindre.
    disabled = raw.get("disabled", False)
    if not isinstance(disabled, bool):
        raise ExpertError(f"{path.name} : « disabled » doit valoir true ou false.")
    if disabled:
        return None

    name = str(raw.get("name") or "").strip()
    if not name:
        raise ExpertError(f"{path.name} : champ « name » manquant.")

    url = str(raw.get("url") or "").strip()
    if not url:
        raise ExpertError(f"{path.name} : champ « url » manquant.")
    if urlparse(url).scheme not in {"http", "https"}:
        raise ExpertError(f"{path.name} : « url » doit commencer par http:// ou https://.")

    descriptions = raw.get("description") or {}
    if not isinstance(descriptions, dict):
        raise ExpertError(f"{path.name} : « description » doit lister les langues.")
    description = descriptions.get(language) or descriptions.get(FALLBACK_LANGUAGE)
    if not description:
        raise ExpertError(
            f"{path.name} : aucune description en « {language} » ni en « {FALLBACK_LANGUAGE} »."
        )

    weight = raw.get("weight", DEFAULT_WEIGHT)
    if not isinstance(weight, int) or isinstance(weight, bool):
        raise ExpertError(f"{path.name} : « weight » doit être un entier.")

    sponsor = raw.get("sponsor", False)
    if not isinstance(sponsor, bool):
        raise ExpertError(f"{path.name} : « sponsor » doit valoir true ou false.")

    logo = raw.get("logo")
    logo_value: str | None = None
    logo_source: Path | None = None
    if logo:
        logo = str(logo).strip()
        if urlparse(logo).scheme in {"http", "https"}:
            logo_value = logo
        else:
            logo_source = (path.parent / logo).resolve()
            if not logo_source.is_file():
                raise ExpertError(f"{path.name} : logo introuvable ({logo}).")
            if path.parent.resolve() not in logo_source.parents:
                raise ExpertError(f"{path.name} : le logo doit rester dans le dossier des fiches.")

    return Expert(
        slug=path.stem,
        name=name,
        url=url,
        description=str(description).strip(),
        sponsor=sponsor,
        weight=weight,
        logo=logo_value,
        logo_source=logo_source,
    )


def monogram(name: str) -> str:
    """Initiale de repli quand la fiche n'a pas de logo."""
    stripped = unicodedata.normalize("NFKD", name)
    for character in stripped:
        if character.isalnum():
            return character.upper()
    return "?"


def render_card(expert: Expert, labels: dict[str, str]) -> str:
    name = html.escape(expert.name)
    parts = ['<article class="xolo-expert">', '  <div class="xolo-expert__head">']

    if expert.logo:
        parts.append(
            f'    <img class="xolo-expert__logo" src="{html.escape(expert.logo)}" alt="{name}" loading="lazy">'
        )
    else:
        parts.append(
            f'    <span class="xolo-expert__monogram" aria-hidden="true">{html.escape(monogram(expert.name))}</span>'
        )

    pill = ""
    if expert.sponsor:
        pill = f'<span class="xolo-expert__pill">{html.escape(labels["sponsor"])}</span>'
    parts.append(f'    <p class="xolo-expert__name">{name}{pill}</p>')
    parts.append("  </div>")
    parts.append(f'  <p class="xolo-expert__description">{html.escape(expert.description)}</p>')

    host = urlparse(expert.url).netloc.removeprefix("www.")
    parts.append(
        f'  <p class="xolo-expert__link"><a href="{html.escape(expert.url)}"'
        f' rel="noopener nofollow">{html.escape(host)} →</a></p>'
    )
    parts.append("</article>")
    return "\n".join(parts)


def render_page(experts: list[Expert], labels: dict[str, str]) -> str:
    lines = [f"# {labels['title']}", ""]
    if labels.get("intro"):
        lines += [labels["intro"], ""]

    if experts:
        lines.append('<div class="xolo-experts">')
        for expert in experts:
            lines.append(render_card(expert, labels))
        lines.append("</div>")
    else:
        lines.append(f'<p class="xolo-experts__empty">{html.escape(labels["empty"])}</p>')

    if labels.get("outro"):
        lines += ["", labels["outro"]]

    return "\n".join(lines) + "\n"


def read_labels(config_path: Path) -> dict[str, str]:
    with config_path.open("rb") as handle:
        config = tomllib.load(handle)
    labels = dict(DEFAULT_LABELS)
    labels.update(config.get("project", {}).get("extra", {}).get("experts", {}))
    return labels


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="dossier des fiches YAML")
    parser.add_argument("--config", required=True, type=Path, help="zensical.<lang>.toml")
    parser.add_argument("--language", required=True, help="code de langue (fr, en, es)")
    parser.add_argument("--output", required=True, type=Path, help="content/<lang>")
    arguments = parser.parse_args()

    labels = read_labels(arguments.config)

    # Les fichiers préfixés par « _ » sont des modèles, pas des fiches.
    paths = sorted(
        path
        for path in arguments.source.glob("*.y*ml")
        if not path.name.startswith("_")
    )

    experts: list[Expert] = []
    errors: list[str] = []
    disabled = 0
    for path in paths:
        try:
            expert = parse_expert(path, arguments.language)
        except ExpertError as error:
            errors.append(str(error))
            continue
        if expert is None:
            disabled += 1
            continue
        experts.append(expert)

    if errors:
        for error in errors:
            print(f"Experts: {error}", file=sys.stderr)
        return 1

    experts.sort(key=lambda expert: expert.sort_key)

    logo_directory = arguments.output / LOGO_DIRECTORY
    shutil.rmtree(logo_directory, ignore_errors=True)

    published: list[Expert] = []
    for expert in experts:
        if expert.logo_source is None:
            published.append(expert)
            continue
        logo_directory.mkdir(parents=True, exist_ok=True)
        # Le nom de la fiche, pas celui du fichier source : deux entreprises
        # peuvent toutes deux appeler leur logo « logo.svg ».
        destination = logo_directory / (expert.slug + expert.logo_source.suffix)
        shutil.copyfile(expert.logo_source, destination)
        published.append(
            Expert(**{**expert.__dict__, "logo": LOGO_DIRECTORY.as_posix() + "/" + destination.name})
        )

    page = arguments.output / PAGE_NAME
    page.write_text(render_page(published, labels), encoding="utf-8")

    summary = f"Experts: {len(published)} fiche(s) rendues dans {page.relative_to(page.parents[2])}"
    if disabled:
        summary += f", {disabled} désactivée(s)"
    print(summary, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
