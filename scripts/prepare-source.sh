#!/usr/bin/env bash

set -euo pipefail

repository="${XOLO_REPOSITORY:-https://github.com/xolo-gateway/xolo.git}"
ref="${XOLO_REF:?XOLO_REF doit contenir un tag, une branche ou un SHA}"

xolo_logo_src="${XOLO_LOGO_PATH:-internal/http/handler/webui/common/assets/logo.svg}"

# Langues publiées, dans l'ordre de priorité (la première sert de repli si une
# langue est absente du dépôt source).
languages=(fr en es)

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cache_dir="${root_dir}/.cache/xolo"
content_dir="${root_dir}/content"

rm -rf "${cache_dir}"

# Nettoie les répertoires de langue générés sans toucher aux fichiers
# versionnés à la racine de content/ (index.md, .gitkeep, logo.svg).
for lang in "${languages[@]}"; do
  rm -rf "${content_dir}/${lang}"
done

mkdir -p "${root_dir}/.cache" "${content_dir}"

git clone \
  --depth 1 \
  --branch "${ref}" \
  "${repository}" \
  "${cache_dir}"

if [[ ! -d "${cache_dir}/docs/fr" ]]; then
  echo "Le répertoire docs/fr est absent de ${repository}@${ref}" >&2
  exit 1
fi

for lang in "${languages[@]}"; do
  src="${cache_dir}/docs/${lang}"
  if [[ ! -d "${src}" ]]; then
    echo "docs/${lang} absent de ${repository}@${ref}, langue ignorée" >&2
    continue
  fi
  mkdir -p "${content_dir}/${lang}"
  cp -a "${src}/." "${content_dir}/${lang}/"
done

# Logo du projet (SVG) — versionné dans content/, réécrasé à chaque prepare
# pour suivre les évolutions éventuelles du fichier source.
if [[ -f "${cache_dir}/${xolo_logo_src}" ]]; then
  cp -a "${cache_dir}/${xolo_logo_src}" "${content_dir}/logo.svg"
else
  echo "Logo absent: ${cache_dir}/${xolo_logo_src}" >&2
  exit 1
fi

# Évite une publication Jekyll accidentelle.
touch "${content_dir}/.nojekyll"

echo "Documentation préparée depuis ${repository}@${ref} pour : ${languages[*]}"
