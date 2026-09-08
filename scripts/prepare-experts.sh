#!/usr/bin/env bash

# Récupère les fiches d'experts depuis xolo-gateway/org, dépôt privé, puis
# génère content/<lang>/experts.md pour chaque langue.
#
# Le dépôt étant privé, la CI passe un jeton par EXPERTS_TOKEN (PAT
# fine-grained ou GitHub App, Contents: read). Sans jeton et sans source
# locale, la page est simplement absente du build : c'est le cas des PR de
# forks et des préversions locales. EXPERTS_REQUIRED=true rend l'absence
# fatale, ce que font les workflows de publication.

set -euo pipefail

repository="${EXPERTS_REPOSITORY:-https://github.com/xolo-gateway/org.git}"
ref="${EXPERTS_REF:-main}"
subdirectory="${EXPERTS_PATH:-experts}"
required="${EXPERTS_REQUIRED:-false}"
token="${EXPERTS_TOKEN:-}"
# Court-circuite le clone : pratique en local, où le dépôt est déjà là.
source_dir="${EXPERTS_SOURCE:-}"

languages=(fr en es)

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cache_dir="${root_dir}/.cache/experts"
content_dir="${root_dir}/content"

# PyYAML vit dans l'environnement local installé par make tools, pas dans le
# Python du système.
python="${root_dir}/tools/.venv/bin/python"
if [[ ! -x "${python}" ]]; then
  python="$(command -v python3)"
fi

skip() {
  echo "Experts: $1" >&2
  if [[ "${required}" == "true" ]]; then
    echo "Experts: EXPERTS_REQUIRED=true, arrêt." >&2
    exit 1
  fi
  echo "Experts: page ignorée pour ce build." >&2
  exit 0
}

if [[ -n "${source_dir}" ]]; then
  if [[ ! -d "${source_dir}" ]]; then
    skip "EXPERTS_SOURCE=${source_dir} introuvable."
  fi
  experts_dir="${source_dir}"
else
  rm -rf "${cache_dir}"
  mkdir -p "${root_dir}/.cache"

  clone_url="${repository}"
  if [[ -n "${token}" && "${repository}" == https://* ]]; then
    clone_url="https://x-access-token:${token}@${repository#https://}"
  fi

  if ! git clone --depth 1 --branch "${ref}" "${clone_url}" "${cache_dir}" 2>/dev/null; then
    skip "clone de ${repository}@${ref} impossible (jeton absent ou invalide ?)."
  fi

  # Le jeton est écrit dans .git/config par git clone : on le retire.
  git -C "${cache_dir}" remote set-url origin "${repository}"

  experts_dir="${cache_dir}/${subdirectory}"
fi

if [[ ! -d "${experts_dir}" ]]; then
  skip "${subdirectory}/ absent de ${repository}@${ref}."
fi

for lang in "${languages[@]}"; do
  if [[ ! -d "${content_dir}/${lang}" ]]; then
    echo "Experts: content/${lang} absent, langue ignorée." >&2
    continue
  fi
  "${python}" "${root_dir}/scripts/render-experts.py" \
    --source "${experts_dir}" \
    --config "${root_dir}/zensical.${lang}.toml" \
    --language "${lang}" \
    --output "${content_dir}/${lang}"
done
