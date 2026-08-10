SHELL := /usr/bin/env bash

PYTHON ?= python3
TOOLS_DIR := $(CURDIR)/tools
VENV_DIR := $(TOOLS_DIR)/.venv
BIN_DIR := $(VENV_DIR)/bin

PIP := $(BIN_DIR)/pip
ZENSICAL := $(BIN_DIR)/zensical
MIKE := $(BIN_DIR)/mike
# Le fork Mike adapté à Zensical appelle l'exécutable `zensical` dans son PATH.
export PATH := $(BIN_DIR):$(PATH)

XOLO_REPOSITORY ?= https://github.com/xolo-gateway/xolo.git
XOLO_REF ?= main
VERSION ?=
ALIASES ?=
PUSH ?= false
# Les alias sont matérialisés par des pages de redirection HTML : GitHub Pages
# ne suit pas les liens symboliques (défaut de Mike) et les copies dupliquent
# inutilement le contenu.
ALIAS_TYPE ?= redirect
DEFAULT ?= latest

.PHONY: help
help:
	@printf '%s\n' \
		"Commandes disponibles:" \
		"" \
		"  make tools                 Installe Zensical et Mike localement" \
		"  make tools-lock            Génère tools/requirements.lock" \
		"  make tools-sync            Installe depuis tools/requirements.lock" \
		"  make tools-clean           Supprime l'environnement Python local" \
		"  make prepare XOLO_REF=...  Récupère docs/fr/ depuis Xolo" \
		"  make build                 Construit la documentation" \
		"  make check                 Construit en mode strict" \
		"  make serve                 Lance le serveur local" \
		"  make preview XOLO_REF=...  Prépare et sert une version de Xolo" \
		"  make publish VERSION=...   Publie une version avec Mike" \
		"  make publish-latest ...    Publie et déplace l'alias latest" \
		"  make alias VERSION=... ALIASES=...  (Re)pointe un alias" \
		"  make set-default DEFAULT=  Redirige / vers cet alias (latest)" \
		"  make versions              Liste les versions Mike" \
		"  make delete VERSION=...    Supprime une version" \
		"  make clean                 Supprime les fichiers générés"

$(VENV_DIR)/pyvenv.cfg:
	$(PYTHON) -m venv "$(VENV_DIR)"
	"$(PIP)" install --upgrade pip setuptools wheel

.PHONY: tools
tools: $(VENV_DIR)/pyvenv.cfg
	"$(PIP)" install --requirement "$(TOOLS_DIR)/requirements.txt"

.PHONY: tools-lock
tools-lock: $(VENV_DIR)/pyvenv.cfg
	"$(PIP)" install pip-tools
	"$(BIN_DIR)/pip-compile" \
		--resolver=backtracking \
		--output-file "$(TOOLS_DIR)/requirements.lock" \
		"$(TOOLS_DIR)/requirements.txt"

.PHONY: tools-sync
tools-sync: $(VENV_DIR)/pyvenv.cfg
	"$(PIP)" install --requirement "$(TOOLS_DIR)/requirements.lock"

.PHONY: tools-clean
tools-clean:
	rm -rf "$(VENV_DIR)"

.PHONY: prepare
prepare:
	XOLO_REPOSITORY="$(XOLO_REPOSITORY)" \
	XOLO_REF="$(XOLO_REF)" \
		./scripts/prepare-source.sh

.PHONY: build
build: tools
	"$(ZENSICAL)" build --clean

.PHONY: check
check: tools
	"$(ZENSICAL)" build --clean --strict

.PHONY: serve
serve: tools
	"$(ZENSICAL)" serve

.PHONY: preview
preview: prepare serve

.PHONY: require-version
require-version:
	@test -n "$(VERSION)" || { \
		echo "VERSION est obligatoire, par exemple VERSION=1.4.0"; \
		exit 1; \
	}

.PHONY: publish
publish: require-version tools
	@args=(); \
	if [[ "$(PUSH)" == "true" ]]; then \
		args+=(--push); \
	fi; \
	if [[ -n "$(ALIASES)" ]]; then \
		args+=(--update-aliases --alias-type="$(ALIAS_TYPE)"); \
	fi; \
	"$(MIKE)" deploy "$${args[@]}" "$(VERSION)" $(ALIASES)

.PHONY: publish-latest
publish-latest: ALIASES=latest
publish-latest: publish

.PHONY: alias
alias: require-version tools
	@test -n "$(ALIASES)" || { echo "ALIASES est obligatoire"; exit 1; }; \
	args=(--update-aliases --alias-type="$(ALIAS_TYPE)"); \
	if [[ "$(PUSH)" == "true" ]]; then \
		args+=(--push); \
	fi; \
	"$(MIKE)" alias "$${args[@]}" "$(VERSION)" $(ALIASES)

.PHONY: set-default
set-default: tools
	@if [[ "$(PUSH)" == "true" ]]; then \
		"$(MIKE)" set-default --push "$(DEFAULT)"; \
	else \
		"$(MIKE)" set-default "$(DEFAULT)"; \
	fi

.PHONY: versions
versions: tools
	"$(MIKE)" list

.PHONY: delete
delete: require-version tools
	@if [[ "$(PUSH)" == "true" ]]; then \
		"$(MIKE)" delete --push "$(VERSION)"; \
	else \
		"$(MIKE)" delete "$(VERSION)"; \
	fi

.PHONY: clean
clean:
	rm -rf \
		"$(CURDIR)/site" \
		"$(CURDIR)/.cache" \
		"$(CURDIR)/.cache-zensical"