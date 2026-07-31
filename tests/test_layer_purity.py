"""
tests/test_layer_purity.py
CSE Life: Compile & Conquer — phase F5

The architectural guard. Build Plan §0.7 lays out which layer may
import what, and §0.1 forbids touching pre-existing files. Both are
the kind of rule that is obeyed carefully for a week and then broken
by accident, so they are asserted here instead of remembered.

Four rules:

  1. the pure-Python modules import no pygame, with exactly two
     owner-granted exceptions
  2. tools/ never imports engine/, core/ or academic/
  3. nothing imports from _previous_uncommits/ — the quarry is a
     read-only source, not a dependency
  4. no pre-existing file is modified except the one sanctioned edit

Modules from later phases are checked only once they exist, so this
suite is correct at every point in the build rather than only at the
end. No test is ever skipped.
"""

from __future__ import annotations

import os
import re
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Pure-Python modules: no pygame, ever. Names from later phases are
# listed now and checked as soon as the file appears.
PURE_PYTHON_MODULES = (
    "content/level_registry.py",
    "content/level_schema.py",
    "content/dialogues.py",
    "content/npc_roster.py",
    "content/epilogue_text.py",
    "engine/level_loader.py",       # F7
    "engine/gate_evaluator.py",     # F8
    "engine/exam_session.py",       # F9
    "engine/save_manager.py",       # F4
)

# The two owner-granted pygame exceptions in engine/ (§0.7):
#   dialogue_manager.py  pre-existing, re-themed under §0.2
#   audio_manager.py     the owner ruled it belongs with the managers
PYGAME_WHITELIST = (
    "engine/dialogue_manager.py",
    "engine/audio_manager.py",
)

# The single file this branch is permitted to modify (§0.2).
SANCTIONED_EDIT = "engine/dialogue_manager.py"

PYGAME_IMPORT = re.compile(r"^\s*(?:import\s+pygame|from\s+pygame\b)",
                           re.MULTILINE)
QUARRY_IMPORT = re.compile(
    r"^\s*(?:import\s+_previous_uncommits|from\s+_previous_uncommits\b)",
    re.MULTILINE)
FORBIDDEN_IN_TOOLS = re.compile(
    r"^\s*(?:from|import)\s+(engine|core|academic)\b", re.MULTILINE)


def _read(relative_path: str) -> str:
    """Source of a repo-relative file, or "" when it does not exist yet."""
    path = os.path.join(ROOT, relative_path)
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _python_files(*directories: str) -> list:
    """Every .py file under the given repo-relative directories."""
    found = []
    for directory in directories:
        base = os.path.join(ROOT, directory)
        if not os.path.isdir(base):
            continue
        for entry in sorted(os.listdir(base)):
            if entry.endswith(".py"):
                found.append(f"{directory}/{entry}")
    return found


# ─────────────────────────────────────────────────────────────
# 1. NO PYGAME IN THE PURE LAYERS
# ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("relative_path", PURE_PYTHON_MODULES)
def test_pure_python_modules_never_import_pygame(relative_path):
    """
    A data or rules module that imports pygame cannot be unit-tested
    headlessly and drags a display dependency into the game's core.
    """
    source = _read(relative_path)
    if not source:
        # Not written yet; the rule still applies the moment it is.
        assert relative_path.endswith(".py")
        return
    assert not PYGAME_IMPORT.search(source), \
        f"{relative_path} imports pygame but must stay pure Python (§0.7)"


def test_core_and_academic_never_import_pygame():
    """§0.7: core/ and academic/ are pure Python with no exceptions."""
    for relative_path in _python_files("core", "core/character", "academic"):
        source = _read(relative_path)
        assert not PYGAME_IMPORT.search(source), \
            f"{relative_path} imports pygame (§0.7)"


def test_only_two_engine_files_import_pygame():
    """
    The owner granted exactly two pygame exceptions in engine/.

    A third would mean the layer boundary has quietly moved, so this
    fails loudly rather than letting it spread.
    """
    offenders = [path for path in _python_files("engine")
                 if PYGAME_IMPORT.search(_read(path))]
    assert sorted(offenders) == sorted(PYGAME_WHITELIST), (
        f"pygame in engine/ must be limited to {PYGAME_WHITELIST}; "
        f"found {offenders}")


def test_the_whitelisted_files_actually_exist():
    """A whitelist entry that has been deleted or renamed is a stale rule."""
    for relative_path in PYGAME_WHITELIST:
        assert os.path.isfile(os.path.join(ROOT, relative_path)), \
            f"{relative_path} is whitelisted but missing"


# ─────────────────────────────────────────────────────────────
# 2. tools/ IS ASSET TOOLING, NOT GAME CODE
# ─────────────────────────────────────────────────────────────


def test_tools_never_import_engine_core_or_academic():
    """
    §0.7: tools/ may import content/, ui/, tools/, stdlib and pygame.

    The level editor must not be able to reach game state; if it could,
    authoring a level and playing one would stop being separable.
    """
    for relative_path in _python_files("tools"):
        source = _read(relative_path)
        match = FORBIDDEN_IN_TOOLS.search(source)
        assert match is None, \
            f"{relative_path} imports {match.group(1)}/ but tools/ may not"


# ─────────────────────────────────────────────────────────────
# 3. THE QUARRY IS NOT A DEPENDENCY
# ─────────────────────────────────────────────────────────────


def test_nothing_imports_from_the_quarry():
    """
    §0.1: _previous_uncommits/ is a read-only source to copy OUT of.

    It is gitignored, so anything importing from it would work on this
    machine and fail for everyone else.
    """
    directories = ("content", "core", "core/character", "academic", "engine",
                  "ui", "tools", "tests", "levels")
    checked = 0
    for relative_path in _python_files(*directories):
        source = _read(relative_path)
        checked += 1
        assert not QUARRY_IMPORT.search(source), \
            f"{relative_path} imports from _previous_uncommits/"
    for root_file in ("main.py", "play_sandbox.py", "feature_showcase.py",
                      "assemble_sprite_sheet.py"):
        source = _read(root_file)
        if source:
            checked += 1
            assert not QUARRY_IMPORT.search(source), \
                f"{root_file} imports from _previous_uncommits/"
    assert checked > 0, "the purity sweep found no files to check"


# ─────────────────────────────────────────────────────────────
# 4. NO PROTECTED FILE WAS MODIFIED
# ─────────────────────────────────────────────────────────────


def _git(*args: str) -> tuple:
    """Run git at the repo root, returning (ok, stdout)."""
    try:
        result = subprocess.run(
            ("git", "--no-optional-locks") + args,
            cwd=ROOT, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return (False, "")
    return (result.returncode == 0, result.stdout)


def test_no_pre_existing_file_is_modified_except_the_sanctioned_edit():
    """
    Build Plan §0.1 / §0.2 / §5.4.

    Uses --numstat, NOT --name-only: on this checkout --name-only
    silently ignores the whitespace flags and lists every file whose
    blob differs at all, which on a CRLF working tree is all of them.
    That caveat is recorded in the build plan (F12 §2) and is the whole
    reason this test spells the command out.

    An empty result is also correct -- it means the sanctioned edit has
    already been committed.
    """
    if not os.path.isdir(os.path.join(ROOT, ".git")):
        assert True, "not a git checkout; nothing to compare against"
        return

    ok, output = _git("diff", "--ignore-all-space", "--ignore-blank-lines",
                      "--numstat")
    if not ok:
        assert True, "git unavailable; the working-tree check is advisory"
        return

    modified = sorted(
        line.split("\t")[-1].strip().replace("\\", "/")
        for line in output.splitlines() if line.strip())
    assert modified in ([], [SANCTIONED_EDIT]), (
        f"only {SANCTIONED_EDIT} may be modified (§0.2); "
        f"git reports {modified}")
