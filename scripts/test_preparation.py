"""Tests de build-config.py et apply-source-settings.py (make test).

Chaque test monte une arborescence content/ synthétique dans un dossier
temporaire : la CI construit Xolo main, dont les sources ne livrent pas encore
nav.toml ni redirects.txt, et n'exercerait pas ces chemins autrement.
"""

import importlib.util
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CONFIG = '''[project]
site_name = "Xolo"
docs_dir = "content/fr"

[project.extra.home]
tagline = """
Une ligne qui contient
[project]
dans une chaîne multi-lignes.
"""

[project.extra.experts]
title = "Trouver un expert"
'''

NAV = '''nav = [
  { "Accueil" = "index.md" },
  { "Guides" = [
    { "Vue d'ensemble" = "guides/index.md" },
    { "Un guide" = "guides/un.md" },
  ] },
]
'''


class BuildConfigTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.module = load("build-config")
        self.module.ROOT = self.root
        (self.root / "zensical.fr.toml").write_text(CONFIG, encoding="utf-8")
        for page in ("index.md", "guides/index.md", "guides/un.md"):
            path = self.root / "content" / "fr" / page
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Page\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def write_nav(self, text):
        path = self.root / "content" / ".nav" / "fr.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def built(self):
        self.module.build("fr")
        return tomllib.loads((self.root / "zensical.fr.build.toml").read_text(encoding="utf-8"))

    def test_without_nav_keeps_the_source(self):
        self.module.build("fr")
        self.assertEqual((self.root / "zensical.fr.build.toml").read_text(encoding="utf-8"), CONFIG)

    def test_nested_sections_round_trip(self):
        self.write_nav(NAV)
        config = self.built()
        self.assertEqual(config["project"]["nav"], tomllib.loads(NAV)["nav"])
        self.assertIn("[project]\ndans", config["project"]["extra"]["home"]["tagline"])

    def test_missing_page_stops_the_build(self):
        self.write_nav(NAV.replace("guides/un.md", "guides/absent.md"))
        with self.assertRaises(SystemExit) as raised:
            self.module.build("fr")
        self.assertIn("guides/absent.md", str(raised.exception))

    def test_experts_page_is_declared_only_when_generated(self):
        self.assertNotIn("experts_page", self.built()["project"]["extra"])
        (self.root / "content" / "fr" / "experts.md").write_text("# Experts\n", encoding="utf-8")
        self.assertEqual(self.built()["project"]["extra"]["experts_page"], {"link": "experts/"})

    def test_experts_page_key_is_reserved(self):
        (self.root / "zensical.fr.toml").write_text(
            CONFIG + '\n[project.extra.experts_page]\nlink = "experts/"\n', encoding="utf-8"
        )
        with self.assertRaises(SystemExit):
            self.module.build("fr")


class ApplySourceSettingsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.content = Path(self.tmp.name) / "content"
        self.docs = self.content / "fr"
        for page in ("exploitation/installation.md", "guides/index.md"):
            path = self.docs / page
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Page\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, redirects):
        (self.docs / "redirects.txt").write_text(redirects, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "apply-source-settings.py"), str(self.content), "fr"],
            capture_output=True,
            text=True,
        )

    def test_writes_a_redirect_page_and_moves_the_nav(self):
        (self.docs / "nav.toml").write_text(NAV, encoding="utf-8")
        result = self.run_script(
            "# commentaire\n"
            "administration/installation/ exploitation/installation/\n"
            "utilisation/guides/ guides/\n"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (self.docs / "administration/installation/index.md").read_text(encoding="utf-8")
        self.assertIn("redirect: ../../exploitation/installation/", page)
        self.assertIn("template: redirect.html", page)
        self.assertTrue((self.docs / "utilisation/guides/index.md").is_file())
        self.assertFalse((self.docs / "redirects.txt").exists())
        self.assertFalse((self.docs / "nav.toml").exists())
        self.assertTrue((self.content / ".nav" / "fr.toml").is_file())

    def test_refuses_paths_leaving_the_tree(self):
        for line in ("../../evil/ guides/\n", "a/../b/ guides/\n", "a//b/ guides/\n", "old/ ../guides/\n"):
            with self.subTest(line=line):
                result = self.run_script(line)
                self.assertNotEqual(result.returncode, 0)
        self.assertFalse((Path(self.tmp.name) / "evil").exists())

    def test_refuses_a_redirect_from_an_existing_page(self):
        result = self.run_script("guides/ exploitation/installation/\n")
        self.assertNotEqual(result.returncode, 0)

    def test_refuses_a_missing_target(self):
        result = self.run_script("ancien/ absent/\n")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
