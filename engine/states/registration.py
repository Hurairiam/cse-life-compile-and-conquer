"""Course registration. STAGE 9 adds scrolling + backlog accents."""
import pygame
from engine.screen_manager import ScreenState
from ui.registration_screen import (
    RegistrationScreen, FIRST_ROW_Y, FOOTER_Y, ROW_PITCH)

MAX_ROWS = (FOOTER_Y - FIRST_ROW_Y) // ROW_PITCH

__screen = None


def __ui(ctx):
    global __screen
    if __screen is None:
        __screen = RegistrationScreen(ctx.screen_w, ctx.screen_h)
    return __screen


def __courses(ctx):
    return ctx.registration_manager.build_semester_catalog(
        ctx.full_catalog, ctx.history())[:MAX_ROWS]


def enter(ctx):
    ctx.play_music("main_menu")


def handle_events(ctx, events):
    ui = __ui(ctx)
    courses = __courses(ctx)
    rects = ui.get_course_row_rects(len(courses))
    for event in events:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            ctx.quit()
            return
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            continue
        pos = event.pos
        if ui.get_confirm_rect().collidepoint(pos):
            if ctx.registration_manager.confirm_registration(ctx.semester()):
                ctx.play_sfx("confirm")
                ctx.go(ScreenState.EXPLORATION)
        elif ui.get_cancel_rect().collidepoint(pos):
            ctx.play_sfx("cancel")
            ctx.registration_manager.clear_selection()
        else:
            for i, rect in enumerate(rects):
                if rect.collidepoint(pos):
                    course = courses[i]
                    selected = ctx.registration_manager.get_selected_courses()
                    if course in selected:
                        ctx.registration_manager.deselect_course(course)
                    else:
                        ctx.registration_manager.select_course(course)
                    ctx.play_sfx("click")
                    break


def render(ctx, screen):
    ui = __ui(ctx)
    ui.render(
        screen,
        visible_courses=__courses(ctx),
        selected=ctx.registration_manager.get_selected_courses(),
        confirmed=[],
        current_credits=ctx.registration_manager.get_current_selected_credits(),
        credit_limit=ctx.registration_manager.get_max_credit_limit(),
        player_name=ctx.player().get_display_name(),
        student_id=ctx.player().get_character_id(),
        semester=ctx.semester().get_semester_number(),
    )
