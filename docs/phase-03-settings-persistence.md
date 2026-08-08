# Phase 3 — Settings Persistence

**Covers:** Change 2
**Branch:** `dev3-nangiba-gui-assets`
**Date:** 2026-08-08
**Commit:** `[Sprint 4] Persist settings across sessions`

---

## What the recon found

Persistence was not missing. `engine/settings_store.py` and `<project root>/settings.json`
already existed, already held all four options, and were already read at launch by
`AppContext` STAGE 2. This phase is a repair of that mechanism, not a new one.

Two questions the brief said to ask were already answered by the codebase, so they were
not put to the owner:

- **Where the file lives.** There is an existing convention — `settings.json` at the
  project root, anchored to the module file rather than the working directory, the same
  way `engine/save_manager.py` anchors `saves/`.
- **Whether settings are per-save or per-installation.** Per-installation.
  `settings.json` and `saves/` are separate paths and both are gitignored independently;
  nothing keys a preference to a slot. The module docstring already said so.

### Every option in the settings menu

`ui/settings_screen.py::ROW_LABELS` is the authoritative list. Four controls, no others.
All four persist.

| Option | Widget | Values | `ctx` field | JSON key |
|---|---|---|---|---|
| MUSIC VOLUME | slider | 0–100, step 5 | `ctx.music_volume` | `music_volume` |
| SFX VOLUME | slider | 0–100, step 5 | `ctx.sfx_volume` | `sfx_volume` |
| DISPLAY MODE | 2 chips | WINDOWED / FULLSCREEN | `ctx.is_fullscreen` | `fullscreen` |
| TEXT SPEED | 3 chips | SLOW / NORMAL / FAST (15/30/60 cps) | `ctx.text_speed` | `text_speed` |

APPLY and BACK are buttons, not settings.

---

## The defects

### 1. The display mode was loaded but never applied at launch

`app_context.py` STAGE 2 read `fullscreen` off disk into `ctx.is_fullscreen`, then called
`settings_store.apply_all()` — whose body is audio volumes and text speed only.
`apply_display()` had exactly one caller in the entire repository: the APPLY button at
`engine/states/settings.py:69`.

So the preference round-tripped into the file and was dropped on the way out.
`settings.json` in this checkout has said `"fullscreen": true` for some time and the game
still opened windowed every launch. This was the only one of the four options that failed
the acceptance test — volumes and text speed were already being applied correctly.

**Fix:** one call, `settings_store.apply_display(self)`, immediately after
`apply_all(self)` in STAGE 2. Both run inside `AppContext.__init__`, which `main()`
completes before entering the loop, so nothing is presented to the player in the wrong
mode — the first `pygame.display.flip()` happens after the window has already been
re-opened.

**Why it is a second call rather than being folded into `apply_all()`.** The settings
screen's BACK button reverts through `apply_all()`. Folding the display in would re-open
the window on every cancel, flashing the screen for a mode the player explicitly declined.
The two callers that do want the window re-opened — APPLY, and launch — ask for it by
name. Both `apply_display()` and `apply_all()` now carry that reasoning in their
docstrings.

### 2. `save()` was not atomic

It opened `settings.json` directly and wrote into it. A crash or a kill mid-write leaves a
truncated file, and `load()` can only read a truncated file as "use defaults" — silently
discarding every preference the player had set. The failure mode is exactly the one this
phase exists to prevent, arriving by a different road.

**Fix:** the same three-step write `engine/save_manager.py` already uses, copied
deliberately rather than invented: serialise to a string first so an unserialisable value
fails before any file is touched, write `<file>.tmp` with `flush` + `os.fsync`, then
`os.replace()` — atomic on Windows and POSIX. A failed write removes its own temp file.

### 3. Defaults were duplicated as literals

`load()` passed `70`, `80` and `"NORMAL"` as `.get()` fallbacks and `__clamp_volume()`
returned a hardcoded `70`, all alongside a `DEFAULTS` dict that declared the same values.
The duplication had already drifted: a non-numeric `sfx_volume` fell back to 70, not to
the declared sfx default of 80.

**Fix:** `DEFAULTS` is the only place those numbers are written down. `__clamp_volume()`
takes the fallback as an argument so each key lands on its own default.

---

## Owner rulings

1. **Fullscreen keeps the bare `pygame.FULLSCREEN` flag.** Every stub-test block in the
   repo uses `pygame.SCALED | pygame.FULLSCREEN`, which would preserve the desktop
   resolution and letterbox instead of forcing a 1280×720 mode change. Adding `SCALED`
   was declined: `apply_display()` is shared with the in-game APPLY button, so changing
   the flag would change what APPLY does too — a visible behaviour change beyond
   persistence. Launch now reproduces exactly what APPLY already did.
2. **The non-atomic write is fixed in this phase.** Same file, same feature, and a
   truncated `settings.json` is a persistence failure.

---

## What was deliberately left alone

- **Corrupt-file handling was already correct** and was not rewritten, only extended.
  `json.JSONDecodeError` and `UnicodeDecodeError` are both `ValueError` subclasses, and a
  payload that parses but is not an object was already guarded. The added `UnicodeDecodeError`
  in the `except` clause is documentation of intent, not a behaviour change.
- **Settings still persist on APPLY only**, and BACK still reverts to the snapshot taken
  in `enter()`. That is the existing live-edit contract, not a bug.
- **The sliders are still click-only in game** (no drag, unlike the stub test). Not a
  persistence concern.
- **No new options were added** — out of scope per the brief.
- **`main.py` was not touched.** pygame-ce returns the *same* `Surface` object from a
  repeat `set_mode()` (verified), so the surface `main()` captures once stays valid across
  the launch-time mode swap and the render loop needs no change.

---

## Files changed

| File | Δ | Why |
|---|---|---|
| `engine/settings_store.py` | +92 / −19 | atomic write, defaults de-duplicated, `apply_display()` guarded and documented |
| `engine/app_context.py` | +10 / −2 | one `apply_display()` call in STAGE 2, plus the comment explaining why it is separate from `apply_all()` |

No new files. `settings.json` and `saves/` are gitignored, so the change is code-only.

---

## Merge-conflict risk

**Zero.** `git merge-tree` against `origin/main` with these changes applied produces 0
conflict markers.

`engine/settings_store.py` was on the recon's "identical to main, safest to extend" list
and this phase is its first divergence. `engine/app_context.py` diverges from main only in
STAGE 4 (the dialogue-branch fields); the new line is in STAGE 2, nowhere near it.

---

## Verification

Headless (`SDL_VIDEODRIVER=dummy`), against a sandboxed `SETTINGS_PATH` in a temp
directory so the real `settings.json` was never written. 26 checks, all passing.

| # | Case | Result |
|---|---|---|
| 1 | Missing file → full `DEFAULTS` | pass |
| 2 | Round-trip all four options at non-default values; no `.tmp` left behind | pass |
| 3 | Truncated JSON, JSON array, empty file, non-UTF-8 bytes → `DEFAULTS`, no crash | pass |
| 4 | One bad value keeps the other three; bad `sfx_volume` → 80, not 70 | pass |
| 5 | Volumes out of range clamp to 0 / 100 | pass |
| 6 | Unserialisable payload refused, previous file intact, no `.tmp` | pass |
| 7 | `set_mode()` windowed as `main()` does → build `AppContext` → surface flags now carry `FULLSCREEN`; all four `ctx` fields and both `TYPEWRITER_CPS` bindings correct | pass |
| 8 | Relaunch with `fullscreen: false` puts the window back | pass |
| 9 | The `Surface` `main()` captured is the same object after the swap, and still drawable | pass |

**Manual acceptance** (the brief's own test, to be run on a real display): open settings,
move both sliders, pick FULLSCREEN, pick a text speed, press APPLY, quit, relaunch. All
four come back as they were left, and the window is already in the chosen mode before the
title screen draws.
