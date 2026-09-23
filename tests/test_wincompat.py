"""Contract tests for wincompat. Run: python -m unittest discover -s tests -v

Rule tests drive the real CLI over --paths-file lists (portable: none of
these pathologies can even be created on a Windows filesystem). Scan-source
tests use a real temp git repo and a plain working tree.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "wincompat")


def run_cli(*args):
    proc = subprocess.run([sys.executable, SCRIPT, *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=ROOT)
    return proc.returncode, proc.stdout, proc.stderr


def paths_file(tmp, *paths):
    path = os.path.join(tmp, "paths.txt")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(paths) + "\n")
    return path


def git(repo, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    subprocess.run(["git", "-C", repo, *args], check=True,
                   capture_output=True, env=env)


class WincompatContract(unittest.TestCase):
    def test_dos_device_names_fail_in_any_component(self):
        with tempfile.TemporaryDirectory() as tmp:
            listing = paths_file(tmp, "NUL.txt", "src/aux/settings.json")
            code, out, _ = run_cli("--paths-file", listing,
                                   "--format", "json")
            self.assertEqual(code, 1, out)
            data = json.loads(out)
            self.assertFalse(data["ok"])
            self.assertEqual(data["counts"]["fail"], 2)
            rules = {f["rule"] for f in data["findings"]}
            self.assertEqual(rules, {"reserved-name"})
            self.assertIn("NUL.txt", out)
            self.assertIn("aux", out)

    def test_case_only_collision_is_one_finding_naming_both(self):
        with tempfile.TemporaryDirectory() as tmp:
            listing = paths_file(tmp, "README.md", "readme.md")
            code, out, _ = run_cli("--paths-file", listing, "--format", "json")
            self.assertEqual(code, 1, out)
            data = json.loads(out)
            findings = [f for f in data["findings"]
                        if f["rule"] == "case-collision"]
            self.assertEqual(len(findings), 1)
            self.assertIn("README.md", findings[0]["message"])
            self.assertIn("readme.md", findings[0]["message"])

    def test_directory_level_case_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            listing = paths_file(tmp, "Docs/a.md", "docs/b.md")
            code, out, _ = run_cli("--paths-file", listing, "--format", "json")
            self.assertEqual(code, 1, out)
            self.assertEqual(json.loads(out)["counts"]["fail"], 1)

    def test_trailing_characters_and_illegal_chars(self):
        with tempfile.TemporaryDirectory() as tmp:
            listing = paths_file(tmp, "release.md.", "build log ",
                                 "api:v1.md")
            code, out, _ = run_cli("--paths-file", listing, "--format", "json")
            self.assertEqual(code, 1, out)
            rules = {f["rule"] for f in json.loads(out)["findings"]}
            self.assertEqual(rules,
                             {"trailing-dot", "trailing-space", "illegal-char"})

    def test_overlong_path_warns_and_strict_blocks(self):
        long_path = "/".join(["deep"] * 70) + "/module.py"  # 300+ chars
        with tempfile.TemporaryDirectory() as tmp:
            listing = paths_file(tmp, long_path)
            code, out, _ = run_cli("--paths-file", listing, "--no-color")
            self.assertEqual(code, 0, out)
            self.assertIn("WARN", out)
            self.assertIn("path-too-long", out)
            code, out, _ = run_cli("--paths-file", listing, "--strict",
                                   "--no-color")
            self.assertEqual(code, 1, out)

    def test_allow_exempts_a_rule_with_a_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            listing = paths_file(tmp, "NUL.txt")
            code, out, _ = run_cli(
                "--paths-file", listing,
                "--allow", "reserved-name=historic fixture name",
                "--no-color")
            self.assertEqual(code, 0, out)
            self.assertIn("exempt", out)
            self.assertIn("ok --", out)

    def test_clean_list_is_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            listing = paths_file(tmp, "src/main.py", "README.md")
            code, out, _ = run_cli("--paths-file", listing, "--format", "json")
            self.assertEqual(code, 0, out)
            data = json.loads(out)
            self.assertTrue(data["ok"])
            self.assertEqual(data["counts"],
                             {"checked": 2, "fail": 0, "warn": 0, "exempt": 0})

    def test_git_mode_lists_tracked_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.join(tmp, "repo")
            os.makedirs(repo)
            for name in ("a.py", "README.md"):
                with open(os.path.join(repo, name), "w") as handle:
                    handle.write("x = 1\n")
            git(repo, "init", "-q")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "base")
            code, out, _ = run_cli(repo, "--format", "json")
            self.assertEqual(code, 0, out)
            data = json.loads(out)
            self.assertEqual(data["source"], "git")
            self.assertEqual(data["counts"]["checked"], 2)

    def test_missing_inputs_are_usage_errors(self):
        code, _, err = run_cli(os.path.join("nope", "dir"))
        self.assertEqual(code, 2)
        self.assertIn("not a directory", err)
        code, _, err = run_cli("--paths-file", os.path.join("nope", "list"))
        self.assertEqual(code, 2)
        self.assertIn("cannot read", err)


if __name__ == "__main__":
    unittest.main()
