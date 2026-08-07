"""
engine/dialogue_manager.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
OOP Pillar: Encapsulation + Separation of Concerns
DialogueManager handles ALL in-game text box rendering.
It is the only file in Ayesha's layer that imports Pygame.
It does not contain any game logic -- only rendering.
Abu Huraira's main loop calls render() every frame and
advance() when the player presses SPACE.
─────────────────────────────────────────────────────────────
Sprint 2 — Created by Ayesha Saheba Mostofa (dev4-aysha-narrative)
─────────────────────────────────────────────────────────────
REVISION — phase F2, branch nangiba-temp-01 (Nangiba Tasnim).

Re-themed to UI_STYLE_GUIDE.md under the owner's explicit
authorisation (Feature Build Plan §0.2 — "the one sanctioned
edit"). The old Arial-on-dark-blue box violated §2 (palette)
and §3 (typography); drawing is now delegated to the tan
ui/dialog_box.py card, corner brackets and all.

WHAT DID NOT CHANGE. All six original public signatures are
byte-identical and behave exactly as before:

    __init__(screen_width, screen_height)
    load_dialogue(lines, portrait_path=None)
    advance() -> bool
    is_active() -> bool
    get_current_line() -> str
    render(screen) -> None

main.py calls all six and keeps working untouched. In
particular main.py never calls update(), so render() reveals
the WHOLE line when the typewriter has not been ticked -- the
typewriter is opt-in, not a behaviour change.

WHAT WAS ADDED (additive only, nothing renamed or removed):
    update(dt), set_speaker(name), set_typewriter_enabled(flag),
    skip_reveal(), get_progress(), load_npc_dialogue(npc_id, section),
    get_speaker(), is_reveal_complete()
─────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import os

import pygame

from ui.dialog_box import TYPEWRITER_CPS, DialogBox

# Anchored to the project root so a repo-relative portrait path
# resolves the same whether the game was started from the project
# root, from an IDE, or from a shortcut.
PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The dialogue sections content/dialogues.py provides for every NPC.
DIALOGUE_SECTIONS: tuple = ("greeting", "offer", "farewell", "unavailable")


class DialogueManager:
    """
    Manages and renders dialogue sequences.
    load_dialogue() must be called before render() will show anything.
    advance() returns False when the dialogue sequence is finished.
    """

    def __init__(self, screen_width: int, screen_height: int) -> None:
        self.__dialogue_queue: list[str] = []
        self.__current_index: int = 0
        self.__is_active: bool = False
        self.__current_portrait: pygame.Surface | None = None
        self.__box: DialogBox = DialogBox(screen_width, screen_height)
        self.__speaker: str = ""
        self.__typewriter_enabled: bool = True
        # None means "never ticked" -- render() then shows the whole
        # line, which is what keeps main.py's untouched loop correct.
        self.__elapsed: float | None = None
        self.__pulse: float = 0.0

    def load_dialogue(self, lines: list[str],
                      portrait_path: str | None = None) -> None:
        """
        Loads a new dialogue sequence and optionally a portrait image.
        portrait_path should match a value from npc_roster.py with
        the emotion placeholder replaced by the actual emotion name.
        Example: assets/portraits/npc_purnno_neutral.png
        """
        self.__dialogue_queue = lines
        self.__current_index = 0
        self.__is_active = True
        self.__current_portrait = None
        self.__elapsed = None
        if portrait_path:
            self.__current_portrait = self.__load_portrait(portrait_path)

    def load_npc_chain(self, chain, portrait_path=None, display_name="") -> bool:
        """
        Loads a semester dialogue chain.

        Parameters
        ----------
        chain : DialogueChain
            Chain object from the level editor.
        portrait_path : str | None
            Portrait image path.
        display_name : str
            NPC name shown above the dialogue.

        Returns
        -------
        bool
            True if dialogue was loaded successfully.
        """
        if chain is None:
            return False

        try:
            lines = chain.get_lines()
        except AttributeError:
            return False

        if not lines:
            return False

        self.load_dialogue(lines, portrait_path)
        self.set_speaker(display_name)
        return True

    def advance(self) -> bool:
        """
        Advances to the next dialogue line.
        Returns True if there are more lines remaining.
        Returns False when the sequence is complete -- caller should
        deactivate the dialogue state in the screen manager.
        """
        self.__current_index += 1
        self.__elapsed = None if self.__elapsed is None else 0.0
        if self.__current_index >= len(self.__dialogue_queue):
            self.__is_active = False
            return False
        return True

    def is_active(self) -> bool:
        """Returns True if a dialogue sequence is currently running."""
        return self.__is_active

    def get_current_line(self) -> str:
        """Returns the current dialogue line, or empty string if inactive."""
        if not self.__is_active:
            return ""
        # Range guard, F2. load_dialogue([]) left is_active() True with an
        # empty queue, so this line raised IndexError in the pre-edit file
        # too. main.py never loads an empty list, so nothing depended on
        # the crash; returning "" matches what the docstring already
        # promised. Nothing else about the method changed.
        if not 0 <= self.__current_index < len(self.__dialogue_queue):
            return ""
        return self.__dialogue_queue[self.__current_index]

    def render(self, screen: pygame.Surface) -> None:
        """
        Renders the dialogue box, current text line, portrait, and
        the SPACE key hint. Called every frame by the main loop.
        Does nothing if is_active() is False.
        """
        if not self.__is_active or not self.__dialogue_queue:
            return

        line = self.get_current_line()
        visible = self.__visible_count(line)
        self.__box.render(screen, self.__speaker, line[:visible],
                          self.__current_portrait,
                          show_indicator=visible >= len(line),
                          pulse=self.__pulse)

    # ── additions (F2) ───────────────────────────────────────
    def update(self, dt: float) -> None:
        """
        Advance the typewriter and the continue-arrow pulse.

        Entirely optional. A caller that never calls this -- main.py,
        today -- gets the full line rendered immediately, exactly as
        before the re-theme.
        """
        try:
            step = float(dt)
        except (TypeError, ValueError):
            return
        if step < 0.0:
            return
        self.__pulse += step
        self.__elapsed = step if self.__elapsed is None \
            else self.__elapsed + step

    def set_speaker(self, name: str) -> None:
        """Set the name label drawn above the line. Empty hides nothing."""
        self.__speaker = str(name)

    def get_speaker(self) -> str:
        """The name label currently drawn."""
        return self.__speaker

    def set_typewriter_enabled(self, flag: bool) -> None:
        """
        Turn the letter-by-letter reveal on or off.

        Off means every line appears complete the moment it loads --
        the accessibility setting, and what the TEXT SPEED chips on the
        settings screen switch to at their fastest.
        """
        self.__typewriter_enabled = bool(flag)

    def is_typewriter_enabled(self) -> bool:
        """True while the letter-by-letter reveal is on."""
        return self.__typewriter_enabled

    def skip_reveal(self) -> bool:
        """
        Finish revealing the current line immediately.

        Returns False when there was nothing left to reveal, so a caller
        can use one key for "finish the line, then advance".
        """
        if not self.__is_active:
            return False
        line = self.get_current_line()
        if self.__visible_count(line) >= len(line):
            return False
        # Jump the clock far enough forward that visible_length() covers
        # the whole line -- the reveal speed stays defined in one place.
        self.__elapsed = len(line) / float(TYPEWRITER_CPS)
        return True

    def is_reveal_complete(self) -> bool:
        """True when the whole of the current line is showing."""
        if not self.__is_active:
            return True
        line = self.get_current_line()
        return self.__visible_count(line) >= len(line)

    def get_progress(self) -> tuple[int, int]:
        """
        (lines consumed, lines total) for the sequence in play.

        Reported one-based on the current line so a caller can draw
        "2 / 3" without off-by-one arithmetic; (0, 0) when inactive.
        """
        if not self.__is_active:
            return (0, 0)
        return (self.__current_index + 1, len(self.__dialogue_queue))

    def load_npc_dialogue(self, npc_id: str,
                          section: str = "greeting") -> bool:
        """
        Load one NPC's real lines from content/dialogues.py.

        `npc_id` is a content/npc_roster.py key (the canonical id source
        per Build Plan §1.3). `section` is one of DIALOGUE_SECTIONS.
        Returns False for an unknown NPC or section, leaving whatever
        was already loaded untouched -- no exception ever escapes.

        The portrait is resolved through the roster first, then through
        the art that actually shipped, then given up on in favour of the
        dialog box's placeholder block.
        """
        try:
            from content.dialogues import NPC_DIALOGUES
            from content.npc_roster import NPC_ROSTER
        except ImportError:
            return False

        if npc_id not in NPC_DIALOGUES or npc_id not in NPC_ROSTER:
            return False
        sections = NPC_DIALOGUES[npc_id]
        if section not in sections:
            return False
        lines = list(sections[section])
        if not lines:
            return False

        entry = NPC_ROSTER[npc_id]
        self.load_dialogue(lines, self.__resolve_portrait_path(npc_id, entry))
        self.set_speaker(entry.get("display_name", ""))
        return True

    # ── private helpers ──────────────────────────────────────
    def __visible_count(self, line: str) -> int:
        """
        How many characters of `line` should be showing right now.

        The whole line whenever the typewriter is off or has never been
        ticked -- that second case is what keeps main.py correct.
        """
        if not self.__typewriter_enabled or self.__elapsed is None:
            return len(line)
        return min(len(line), DialogBox.visible_length(self.__elapsed))

    def __resolve_portrait_path(self, npc_id: str, entry: dict) -> str | None:
        """
        Pick the best portrait path that exists on disk for this NPC.

        The roster declares assets/portraits/npc_<name>_{emotion}.png,
        which does not exist for anybody yet; the real art shipped to
        assets/npcs/ for Hoque and Roya only. Returning None is a normal
        outcome -- the dialog box draws its placeholder block.
        """
        variants = entry.get("portrait_variants") or ["neutral"]
        emotion = variants[0]
        short = npc_id.rsplit("_", 1)[-1]
        declared = entry.get("portrait_file", "")
        candidates = []
        if declared:
            try:
                candidates.append(declared.format(emotion=emotion))
            except (KeyError, IndexError, ValueError):
                candidates.append(declared)
        # [IMAGE PLACEHOLDER: assets/npcs/npc_<name>_<emotion>.png --
        #  96x96 emotion portraits. Only hoque and roya exist today;
        #  purnno, rafi, zayan, kabir and rahman fall through to the
        #  dialog box's PORTRAIT_FILL block (Style Guide §5.2).]
        candidates.append(f"assets/npcs/npc_{short}_{emotion}.png")
        for relative in candidates:
            if os.path.isfile(os.path.join(PROJECT_ROOT, relative)):
                return relative
        return None

    def __load_portrait(self, portrait_path: str) -> pygame.Surface | None:
        """
        Load a portrait, or return None so the box draws a placeholder.

        Tries the path as given first (so an absolute path or a path
        relative to the working directory still works), then anchored to
        the project root.
        """
        for candidate in (portrait_path,
                          os.path.join(PROJECT_ROOT, portrait_path)):
            try:
                return pygame.image.load(candidate).convert_alpha()
            except (FileNotFoundError, OSError, pygame.error, TypeError):
                continue
        return None
