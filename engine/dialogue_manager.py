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
TASK 5 — PER-LINE PORTRAITS (Sprint 5, Nangiba).

THE ROOT CAUSE, which is not the one the brief names. The brief says
content/dialogues.py assigns a per-line emotion tag that is never read.
It does not: NPC_DIALOGUES is dict[str, dict[str, list[str]]] and holds
no emotion data at all. The portrait never changed for TWO reasons, both
in this file:

  1. load_dialogue() resolved one portrait and advance() never revisited
     it, so nothing could change the face mid-conversation; and
  2. __resolve_portrait_path() took portrait_variants[0] unconditionally
     — "neutral" for all seven NPCs — so even a caller that wanted a
     different face could not ask for one.

Both are fixed. What is still missing is DATA: no per-line emotion
exists anywhere to drive it. Supplying it means writing into Ayesha's
file, which is hers under G2 — reported as a gap, not invented here.
Two ways in are provided so it works the moment she has tags:
load_npc_dialogue(..., emotions=[...]), and authoring a section as
(line, emotion) pairs, which __split_tagged() already accepts.

STILL BYTE-IDENTICAL. load_dialogue(lines, portrait_path) with no third
argument behaves exactly as before: one portrait, held for every line.
All four existing call sites pass at most two arguments and are
unchanged, and the INTRO beats depend on precisely that.

ADDED HERE: load_dialogue(..., portraits=None),
    load_npc_dialogue(..., emotions=None), get_current_portrait(),
    has_line_portraits()
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
        # -- TASK 5 (per-line portraits) --------------------------
        # The portrait paths for each line, parallel to the queue, and
        # the one to fall back on. Empty list = the old behaviour: one
        # portrait for the whole call, never revisited.
        self.__line_portraits: list[str | None] = []
        self.__fallback_portrait: pygame.Surface | None = None
        # path -> Surface|None, so a conversation that returns to an
        # emotion decodes that PNG once. None is cached too: a missing
        # file is not retried on every line.
        self.__portrait_cache: dict[str, pygame.Surface | None] = {}

    def load_dialogue(self, lines: list[str],
                      portrait_path: str | None = None,
                      portraits: list | None = None) -> None:
        """
        Loads a new dialogue sequence and optionally a portrait image.
        portrait_path should match a value from npc_roster.py with
        the emotion placeholder replaced by the actual emotion name.
        Example: assets/portraits/npc_purnno_neutral.png

        TASK 5 — `portraits` is new and OPTIONAL. Pass a list parallel
        to `lines` to make the portrait change per line; an entry may be
        None to mean "keep whatever was showing". Omit it entirely and
        this behaves exactly as it always did: `portrait_path` is loaded
        once and `advance()` never touches it, which is what the INTRO
        beats and all four existing call sites rely on.

        RAGGED INPUT IS NORMAL, not an error. Fewer portraits than
        lines, a None entry, an empty string, or a path that is not on
        disk all resolve the same way — see `__portrait_for()`: the last
        portrait that did resolve, or failing that `portrait_path`, or
        failing that the dialog box's own placeholder block. A
        conversation never renders a blank where a face was.
        """
        self.__dialogue_queue = lines
        self.__current_index = 0
        self.__is_active = True
        self.__elapsed = None
        self.__fallback_portrait = None
        if portrait_path:
            self.__fallback_portrait = self.__load_portrait(portrait_path)
        self.__line_portraits = ([] if portraits is None
                                 else [self.__clean_path(p) for p in portraits])
        self.__current_portrait = self.__portrait_for(0)

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

        TASK 5 — this is half the bug. It moved the index and left
        `__current_portrait` exactly as load_dialogue() had set it, so
        the face could not change mid-conversation however the content
        was authored. It now re-resolves the portrait for the line it
        landed on. With no per-line list that resolves to the same
        fallback every time, so single-portrait callers see no change.
        """
        self.__current_index += 1
        self.__elapsed = None if self.__elapsed is None else 0.0
        if self.__current_index >= len(self.__dialogue_queue):
            self.__is_active = False
            return False
        self.__current_portrait = self.__portrait_for(self.__current_index)
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
                          section: str = "greeting",
                          emotions: list | None = None) -> bool:
        """
        Load one NPC's real lines from content/dialogues.py.

        `npc_id` is a content/npc_roster.py key (the canonical id source
        per Build Plan §1.3). `section` is one of DIALOGUE_SECTIONS.
        Returns False for an unknown NPC or section, leaving whatever
        was already loaded untouched -- no exception ever escapes.

        The portrait is resolved through the roster first, then through
        the art that actually shipped, then given up on in favour of the
        dialog box's placeholder block.

        TASK 5 — two ways to get a face per line, both optional:

        1. Pass `emotions`, a list of variant names parallel to the
           section's lines ("happy", "stressed", ...). Names come from
           that NPC's `portrait_variants` in the roster.
        2. Author the section as (line, emotion) pairs instead of plain
           strings. `__split_tagged()` accepts either shape, so the day
           content/dialogues.py grows tags this starts working with no
           further code change — and until then plain strings load
           exactly as they always have.

        An explicit `emotions` argument wins over authored tags.
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
        lines, tagged = self.__split_tagged(sections[section])
        if not lines:
            return False

        entry = NPC_ROSTER[npc_id]
        wanted = list(emotions) if emotions is not None else tagged
        portraits = None
        if wanted:
            portraits = [self.__resolve_portrait_path(npc_id, entry, emotion)
                         for emotion in self.__pad(wanted, len(lines))]
        self.load_dialogue(lines,
                           self.__resolve_portrait_path(npc_id, entry),
                           portraits)
        self.set_speaker(entry.get("display_name", ""))
        return True

    @staticmethod
    def __split_tagged(section) -> tuple:
        """
        Split a section into (lines, emotions).

        Accepts the shape content/dialogues.py uses today — a list of
        plain strings, which yields no emotions at all — and the tagged
        shape it may grow, a list of (line, emotion) pairs. Mixed lists
        work too: an untagged entry contributes None and inherits the
        previous face.
        """
        lines: list[str] = []
        emotions: list = []
        found = False
        for entry in (section or ()):
            if isinstance(entry, (tuple, list)) and len(entry) >= 2:
                lines.append(str(entry[0]))
                emotions.append(str(entry[1]) or None)
                found = True
            else:
                lines.append(str(entry))
                emotions.append(None)
        return lines, (emotions if found else [])

    @staticmethod
    def __pad(values: list, count: int) -> list:
        """`values` grown to `count` entries with None. Never truncates
        meaning: a short list simply stops naming faces, and
        __portrait_for() holds the last one."""
        values = list(values)
        if len(values) >= count:
            return values[:count]
        return values + [None] * (count - len(values))

    # ── per-line portraits (Task 5) ──────────────────────────
    def get_current_portrait(self) -> pygame.Surface | None:
        """The portrait being drawn right now, or None for the block."""
        return self.__current_portrait

    def has_line_portraits(self) -> bool:
        """True when this sequence was loaded with a per-line list."""
        return bool(self.__line_portraits)

    @staticmethod
    def __clean_path(value) -> str | None:
        """A usable portrait path, or None for anything blank."""
        if not value:
            return None
        text = str(value).strip()
        return text or None

    def __portrait_for(self, index: int) -> pygame.Surface | None:
        """
        The portrait for one line, with the ragged cases resolved.

        Walks BACKWARDS from `index` to the most recent entry that names
        a file that actually loads, then falls back to the single
        portrait the call was loaded with. Backwards rather than
        "remember the last one drawn" so the answer depends only on the
        index — jumping straight to line 5 gives the same face as
        pressing SPACE five times.

        Every ragged case funnels through here: a short list (index past
        the end), a None or empty entry, and a path that is not on disk
        all just keep looking left. None at the end is a normal outcome
        — ui/dialog_box.py draws its PORTRAIT_FILL block.
        """
        for candidate in range(min(index, len(self.__line_portraits) - 1),
                               -1, -1):
            path = self.__line_portraits[candidate]
            if not path:
                continue
            surface = self.__cached_portrait(path)
            if surface is not None:
                return surface
        return self.__fallback_portrait

    def __cached_portrait(self, path: str) -> pygame.Surface | None:
        """Load a portrait once per path, misses included."""
        if path not in self.__portrait_cache:
            self.__portrait_cache[path] = self.__load_portrait(path)
        return self.__portrait_cache[path]

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

    def __resolve_portrait_path(self, npc_id: str, entry: dict,
                                emotion: str | None = None) -> str | None:
        """
        Pick the best portrait path that exists on disk for this NPC.

        TASK 5 — `emotion` is new and is the OTHER half of the bug. This
        method used to take `variants[0]` unconditionally, which is
        "neutral" for all seven NPCs, so every portrait in the game
        resolved to the neutral face no matter what the content wanted.
        Passing an emotion now picks that variant; passing None keeps
        the old first-variant default, so `load_npc_dialogue()` without
        emotions behaves as before.

        An unknown or misspelled emotion is not an error: the file
        simply will not be on disk, both candidates miss, and the caller
        falls back the way `__portrait_for()` describes.

        The art situation the old comment described has since changed —
        assets/portraits/ now holds all three variants for all seven
        NPCs, so the roster's declared path is the one that hits.
        Returning None is still a normal outcome for an id with no art.
        """
        variants = entry.get("portrait_variants") or ["neutral"]
        wanted = str(emotion).strip() if emotion else ""
        emotion = wanted or variants[0]
        short = npc_id.rsplit("_", 1)[-1]
        declared = entry.get("portrait_file", "")
        candidates = []
        if declared:
            try:
                candidates.append(declared.format(emotion=emotion))
            except (KeyError, IndexError, ValueError):
                candidates.append(declared)
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
