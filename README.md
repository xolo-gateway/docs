# xolo-gateway/docs

Construit, versionne et déploie la documentation de
[Xolo](https://github.com/xolo-gateway/xolo) sur GitHub Pages.

Le Markdown source vit dans `xolo-gateway/xolo` sous `docs/fr/`. Ce dépôt ne
contient que la tuyauterie : Zensical pour le rendu, Mike pour le versionnement
sur la branche `gh-pages`.

Site public : [xolo-gateway.org](https://xolo-gateway.org)

## Utilisation locale

Il faut Python ≥ 3.10 et Git. Tout passe par le `Makefile`, qui installe ses
outils dans `tools/.venv/` (jamais versionné).

```bash
make tools-sync                  # installe Zensical + Mike
make preview XOLO_REF=main       # sert la doc de xolo@main sur localhost
make preview XOLO_REF=v0.55.0    # sert la doc d'un tag publié
make check XOLO_REF=main         # build strict, échoue sur lien mort ou warning
```

## Ce qui est publié

| URL       | Contenu                              |
| --------- | ------------------------------------ |
| `/X.Y.Z/` | Doc figée du tag `vX.Y.Z`            |
| `/main/`  | Doc de `xolo-gateway/xolo@main`      |
| `/latest/`| Redirige vers le dernier tag publié  |
| `/dev/`   | Redirige vers `/main/`               |
| `/`       | Redirige vers `/latest/`             |

Les alias et l'index racine sont des pages HTML de redirection
(`mike --alias-type=redirect`), pas des liens symboliques. GitHub Pages ne suit
pas les symlinks, ce qui donnait des `/latest/` cassés jusqu'ici.

Le `v` du tag est retiré : `v0.55.0` atterrit dans `/0.55.0/`. Seuls les tags
`vMAJEUR.MINEUR.PATCH` publient. Les tags internes type
`v2026.3.11-main.2338.b7f62f8` sont ignorés.

## Déclenchement

`xolo-gateway/xolo/.github/workflows/docs.yml` envoie un `repository_dispatch`
vers ce dépôt à chaque push :

| Événement sur `xolo`  | Dispatch       | Workflow ici          | Sortie                          |
| --------------------- | -------------- | --------------------- | ------------------------------- |
| Tag `vX.Y.Z`          | `xolo-release` | `publish-version.yml` | `/X.Y.Z/`, `/latest/`, `/`      |
| Push sur `main`       | `xolo-main`    | `publish-main.yml`    | `/main/`, `/dev/`               |

`publish-main.yml` tourne aussi chaque jour à 06:00 UTC et à chaque push sur le
`main` de ce dépôt, pour rattraper un dispatch perdu.

Chaque workflow clone Xolo au bon ref, copie `docs/fr/` vers `content/`,
construit en mode strict, publie avec Mike, puis déploie `gh-pages` via
`actions/deploy-pages`.

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

En ligne de commande :

```bash
make publish VERSION=0.55.1 ALIASES=latest PUSH=true
make set-default DEFAULT=latest PUSH=true    # régénère l'index racine
make alias VERSION=0.55.1 ALIASES=latest PUSH=true   # repointe sans rebuild
make versions                                # liste ce qui est publié
make delete VERSION=0.55.0 PUSH=true         # supprime une version
```

Une version publiée est immuable. Une faute dans `0.55.0` se corrige en
publiant `0.55.1`, pas en réécrivant `0.55.0`.

## Limites

- Seule la version française est publiée (`docs/fr/`).
- Pas de thème custom, `variant = "modern"` par défaut.

## Structure

```
.github/workflows/
├── check.yml              build strict sur PR
├── publish-version.yml    tag Xolo → /X.Y.Z/ + /latest/ + /
└── publish-main.yml       main Xolo, cron → /main/ + /dev/
scripts/
├── prepare-source.sh      clone Xolo, copie filtrée de docs/fr/
└── normalize-version.sh   retire le v, valide le semver
tools/requirements.lock    zensical + mike, généré par make tools-lock
content/index.md           page d'accueil, le reste est généré
overrides/                 surcharges de thème Zensical
zensical.toml              configuration du générateur
Makefile                   point d'entrée unique
```

## Licence

Voir la licence du projet Xolo principal.
