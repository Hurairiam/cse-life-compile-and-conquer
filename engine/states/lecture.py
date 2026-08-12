"""
The lecture sequence. One short lecture per registered course, back to
back, using the same dialogue box NPCs use — just sourced from
content/lectures.py instead of an NPC's chains.

Mirrors engine/states/exam.py's course_index pattern exactly, so the
two systems behave predictably the same way.
"""
import pygame

from content.lectures import get_lecture
from engine.screen_manager import ScreenState
from ui import skip_button

BG = (231, 214, 189)


def __courses(ctx):
    return ctx.semester().get_registered_courses()


def __current_course(ctx):
    courses = __courses(ctx)
    index = ctx.lecture["course_index"]
    return courses[index] if 0 <= index < len(courses) else None


def enter(ctx):
    ctx.lecture["course_index"] = 0
    ctx.lecture["message"] = None
    ctx.play_music("lecture")
    __ensure_loaded(ctx)


def __ensure_loaded(ctx):
    """Load the current course's lecture into the dialogue box, if not already."""
    if ctx.dialogue_manager.is_active():
        return
    course = __current_course(ctx)
    if course is None:
        return
    script = get_lecture(course.get_course_code())
    ctx.dialogue_manager.load_dialogue(script["lines"])
    ctx.dialogue_manager.set_speaker(script["title"])


def __advance(ctx):
    """SPACE: finish the current line first, then move to the next one."""
    if ctx.dialogue_manager.skip_reveal():
        return
    ctx.play_sfx("page_turn")
    if ctx.dialogue_manager.advance():
        return
    # This course's lecture is done — move to the next course
    ctx.lecture["course_index"] += 1
    if __current_course(ctx) is None:
        ctx.lecture["message"] = "ALL LECTURES ATTENDED — PRESS SPACE TO CONTINUE"
    else:
        __ensure_loaded(ctx)


def __skip(ctx):
    """
    End the lecture run now, where reading it through would have ended
    (Task 1).

    This screen's "completion" is course_index running past the last
    registered course, which sets ctx.lecture["message"] and waits for
    one more SPACE. So the skip drives that same state rather than
    jumping straight to EXPLORATION: the player still gets the closing
    line, and any later code that reads the message finds it set exactly
    as a full read-through would have left it.

    Nothing else is owed here. Unlike the side-quest reader this screen
    charges no days, unlocks nothing and completes no quest — the
    lectures are flavour between registration and the exam — so there is
    no reward path a skip could bypass.
    """
    if ctx.lecture["message"] is not None:
        return
    ctx.play_sfx("page_turn")
    courses = __courses(ctx)
    ctx.lecture["course_index"] = len(courses)
    ctx.lecture["message"] = "ALL LECTURES ATTENDED — PRESS SPACE TO CONTINUE"


def handle_events(ctx, events):
    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                ctx.quit()
                return
            if event.key == pygame.K_TAB:
                __skip(ctx)
                return
            if event.key == pygame.K_SPACE:
                if ctx.lecture["message"] is not None:
                    ctx.play_sfx("confirm")
                    ctx.go(ScreenState.EXPLORATION)
                    return
                __advance(ctx)
                return
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # The button first, so a click inside it never doubles as a
            # page turn. Only live while there are lectures left to
            # skip — once the closing line is up, a click dismisses it.
            if (ctx.lecture["message"] is None
                    and skip_button.hit(ctx.screen_w, event.pos)):
                __skip(ctx)
                return
            if ctx.lecture["message"] is not None:
                ctx.go(ScreenState.EXPLORATION)
                return
            __advance(ctx)


def update(ctx, dt):
    ctx.dialogue_manager.update(dt)


def render(ctx, screen):
    screen.fill(BG)
    if ctx.lecture["message"] is not None:
        font = ctx.fonts["body"]
        surf = font.render(ctx.lecture["message"], True, (74, 53, 39))
        screen.blit(surf, (ctx.screen_w // 2 - surf.get_width() // 2, 340))
        return
    ctx.dialogue_manager.render(screen)
    # Top-right below the HUD strip the router paints over this screen.
    # Not drawn once the closing line is up: there is nothing left to
    # skip, and a live-looking button that does nothing is worse than
    # none (Task 1).
    skip_button.render(screen, ctx.screen_w)