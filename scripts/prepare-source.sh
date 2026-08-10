#!/usr/bin/env bash

set -euo pipefail

repository="${XOLO_REPOSITORY:-https://github.com/xolo-gateway/xolo.git}"
ref="${XOLO_REF:?XOLO_REF doit contenir un tag, une branche ou un SHA}"

xolo_logo_src="${XOLO_LOGO_PATH:-internal/http/handler/webui/common/assets/logo.svg}"

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cache_dir="${root_dir}/.cache/xolo"
content_dir="${root_dir}/content"

rm -rf "${cache_dir}"

# Nettoie le contenu généré sans toucher aux fichiers versionnés (index.md, .gitkeep, logo.svg).
find "${content_dir}" -mindepth 1 -maxdepth 1 \
  ! -name 'index.md' \
  ! -name '.gitkeep' \
  ! -name 'logo.svg' \
  -exec rm -rf {} +

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

# Filtrage linguistique : on ne copie que la version française.
cp -a "${cache_dir}/docs/fr/." "${content_dir}/"

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

echo "Documentation FR préparée depuis ${repository}@${ref}"