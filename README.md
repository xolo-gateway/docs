# xolo-gateway/docs

Construit, versionne et déploie la documentation de
[Xolo](https://github.com/xolo-gateway/xolo) sur GitHub Pages.

Le Markdown source vit dans `xolo-gateway/xolo` sous `docs/fr/`, `docs/en/` et
`docs/es/`. Ce dépôt ne contient que la tuyauterie : Zensical pour le rendu,
Mike pour le versionnement sur la branche `gh-pages`.

Site public : [xolo-gateway.org](https://xolo-gateway.org)

## Une langue, un build

Zensical ne permet qu'une langue canonique par build (limitation HTML5 : un
seul attribut `lang` par document). Chaque langue est donc un build Zensical
indépendant, avec sa propre configuration (`zensical.fr.toml`,
`zensical.en.toml`, `zensical.es.toml`) et son propre `docs_dir`
(`content/fr`, `content/en`, `content/es`) — ce qui donne à chaque langue sa
navigation propre, sans mélange. Le sélecteur de langue dans l'en-tête
(`project.extra.alternate`) fait le pont entre les trois : cliquer dessus
renvoie vers la dernière version publiée de la langue cible, pas vers la page
équivalente (les arbres de contenu sont indépendants, il n'y a pas de mapping
page à page entre langues).

Le français reste **sans préfixe** pour préserver les URLs historiques
(`xolo-gateway.org/latest/`, `/main/`, `/X.Y.Z/`) ; anglais et espagnol sont
publiés sous `/en/` et `/es/`.

## Utilisation locale

Il faut Python ≥ 3.10 et Git. Tout passe par le `Makefile`, qui installe ses
outils dans `tools/.venv/` (jamais versionné). La variable `DOC_LANG`
(`fr` par défaut) sélectionne la langue.

```bash
make tools-sync                            # installe Zensical + Mike
make preview XOLO_REF=main                 # sert le français de xolo@main
make preview DOC_LANG=en XOLO_REF=main     # sert l'anglais de xolo@main
make check-all XOLO_REF=main               # build strict des 3 langues
```

## Ce qui est publié

| URL          | Contenu                                    |
| ------------ | ------------------------------------------- |
| `/X.Y.Z/`    | Doc FR figée du tag `vX.Y.Z`                |
| `/main/`     | Doc FR de `xolo-gateway/xolo@main`          |
| `/latest/`   | Redirige vers le dernier tag FR publié      |
| `/dev/`      | Redirige vers `/main/`                      |
| `/`          | Redirige vers `/latest/`                    |
| `/en/X.Y.Z/`, `/en/main/`, `/en/latest/`, `/en/dev/` | Idem, en anglais |
| `/es/X.Y.Z/`, `/es/main/`, `/es/latest/`, `/es/dev/` | Idem, en espagnol |

Les alias et l'index racine sont des pages HTML de redirection
(`mike --alias-type=redirect`), pas des liens symboliques. GitHub Pages ne suit
pas les symlinks, ce qui donnait des `/latest/` cassés jusqu'ici.

Le `v` du tag est retiré : `v0.55.0` atterrit dans `/0.55.0/`. Seuls les tags
`vMAJEUR.MINEUR.PATCH` publient. Les tags internes type
`v2026.3.11-main.2338.b7f62f8` sont ignorés.

Chaque langue a son propre `versions.json` Mike (stocké sous son préfixe de
déploiement), donc son propre historique de versions indépendant.

## Déclenchement

`xolo-gateway/xolo/.github/workflows/docs.yml` envoie un `repository_dispatch`
vers ce dépôt à chaque push :

| Événement sur `xolo`  | Dispatch       | Workflow ici          | Sortie                                    |
| --------------------- | -------------- | --------------------- | ------------------------------------------ |
| Tag `vX.Y.Z`          | `xolo-release` | `publish-version.yml` | `/X.Y.Z/`, `/latest/`, `/` (+ `/en/`, `/es/`) |
| Push sur `main`       | `xolo-main`    | `publish-main.yml`    | `/main/`, `/dev/` (+ `/en/`, `/es/`)       |

`publish-main.yml` tourne aussi chaque jour à 06:00 UTC et à chaque push sur le
`main` de ce dépôt, pour rattraper un dispatch perdu.

Chaque workflow clone Xolo au bon ref, copie `docs/{fr,en,es}/` vers
`content/{fr,en,es}/`, construit les 3 langues en mode strict, les publie avec
Mike, puis déploie `gh-pages` via `actions/deploy-pages`.

Le pont inter-dépôts a besoin du secret `DOCS_DISPATCH_TOKEN` sur
`xolo-gateway/xolo` : un PAT fine-grained ou un token de GitHub App avec
`Contents: read & write` sur `xolo-gateway/docs`. Le `GITHUB_TOKEN` par défaut
ne peut pas déclencher un workflow dans un autre dépôt.

## Publication manuelle

Onglet Actions, workflow "Publish Xolo documentation", bouton Run workflow :

| Input           | Exemple   | Rôle                                  |
| --------------- | --------- | ------------------------------------- |
| `xolo_ref`      | `v0.55.0` | Tag, branche ou SHA Xolo              |
| `version`       | _(vide)_  | Nom public, déduit du ref par défaut  |
| `update_latest` | `true`    | Déplacer l'alias `latest`             |

En ligne de commande, pour les 3 langues d'un coup :

```bash
make publish-all VERSION=0.55.1 ALIASES=latest PUSH=true
make set-default-all DEFAULT=latest PUSH=true   # régénère les 3 index racines
```

Ou pour une seule langue (`DOC_LANG=fr|en|es`, défaut `fr`) :

```bash
make publish DOC_LANG=en VERSION=0.55.1 ALIASES=latest PUSH=true
make alias DOC_LANG=en VERSION=0.55.1 ALIASES=latest PUSH=true   # repointe sans rebuild
make versions DOC_LANG=en                                        # liste ce qui est publié
make delete DOC_LANG=en VERSION=0.55.0 PUSH=true                 # supprime une version
```

Une version publiée est immuable. Une faute dans `0.55.0` se corrige en
publiant `0.55.1`, pas en réécrivant `0.55.0`.

## Limites

- Le sélecteur de langue renvoie vers la dernière version de la langue
  cible, pas vers la page équivalente : les 3 arbres de contenu sont des
  builds indépendants, sans mapping page à page entre langues.
- Pas de thème custom, `variant = "modern"` par défaut.

## Structure

```
.github/workflows/
├── check.yml              build strict des 3 langues sur PR
├── publish-version.yml    tag Xolo → /X.Y.Z/ + /latest/ + / (fr, en, es)
└── publish-main.yml       main Xolo, cron → /main/ + /dev/ (fr, en, es)
scripts/
├── prepare-source.sh      clone Xolo, copie docs/{fr,en,es}/ vers content/
└── normalize-version.sh   retire le v, valide le semver
tools/requirements.lock    zensical + mike, généré par make tools-lock
content/.gitkeep           le contenu de content/ est entièrement généré
overrides/                 surcharges de thème Zensical (partagées)
zensical.fr.toml           config Zensical pour le français (sans préfixe)
zensical.en.toml           config Zensical pour l'anglais (/en/)
zensical.es.toml           config Zensical pour l'espagnol (/es/)
Makefile                   point d'entrée unique (DOC_LANG=fr|en|es)
```

## Licence

Voir la licence du projet Xolo principal.
