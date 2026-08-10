#!/usr/bin/env bash

set -euo pipefail

version="${1:?Une version est requise}"

case "${version}" in
  v*)
    version="${version#v}"
    ;;
esac

if [[ ! "${version}" =~ ^[0-9]+\.[0-9]+\.[0-9]+([-.+][0-9A-Za-z.-]+)?$ ]]; then
  echo "Version invalide: ${version}" >&2
  exit 1
fi

printf '%s\n' "${version}"