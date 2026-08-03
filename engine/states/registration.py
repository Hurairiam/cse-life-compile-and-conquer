"""
Course registration with scrolling, backlog accents and the NEW tag.

The screen windows the catalog itself — this module owns the scroll
integer and NEVER slices the list. Backlogged retakes come back pinned
to the top in red because SemesterCatalogBuilder orders them that way.
"""
import pygame

from engine.screen_manager import ScreenState
from ui.registration_screen import RegistrationScreen

__screen = None


def __ui(ctx):
    global __screen
    if __screen is None:
        __screen = RegistrationScreen(ctx.screen_w, ctx.screen_h)
    return __screen


def __catalog(ctx):
    """Full ordered catalog — backlog first. Never sliced."""
    return ctx.catalog_builder.build(ctx.full_catalog, ctx.history())


def enter(ctx):
    __ui(ctx)
    ctx.reg_scroll = 0
    ctx.play_music("main_menu")
    unmatched = ctx.catalog_builder.get_unmatched_backlog_codes()
    if unmatched:
        print("[registration] backlog codes not offered this term:", unmatched)


def __scroll_by(ctx, delta, total):
    ctx.reg_scroll = __ui(ctx).clamp_scroll(ctx.reg_scroll + delta, total)


def __toggle(ctx, course):
    manager = ctx.registration_manager
    if course in manager.get_selected_courses():
        manager.deselect_course(course)
        ctx.play_sfx("click")
    elif manager.select_course(course):
        ctx.play_sfx("click")
    else:
        ctx.play_sfx("error")          # over the credit cap


def __confirm(ctx, courses):
    if not ctx.registration_manager.confirm_registration(ctx.semester()):
        ctx.play_sfx("error")
        return
    # Baseline for next term's NEW tag: exactly once per semester.
    ctx.catalog_builder.snapshot(courses)
    ctx.play_sfx("confirm")
    ctx.go(ScreenState.EXPLORATION)


def handle_events(ctx, events):
    ui = __ui(ctx)
    courses = __catalog(ctx)
    total = len(courses)
    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                ctx.quit()
                return
            if event.key == pygame.K_DOWN:
                __scroll_by(ctx, 1, total)
            elif event.key == pygame.K_UP:
                __scroll_by(ctx, -1, total)
            elif event.key == pygame.K_PAGEDOWN:
                __scroll_by(ctx, ui.get_visible_row_count(), total)
            elif event.key == pygame.K_PAGEUP:
                __scroll_by(ctx, -ui.get_visible_row_count(), total)
            elif event.key == pygame.K_RETURN:
                __confirm(ctx, courses)
                return
        elif event.type == pygame.MOUSEWHEEL:
            __scroll_by(ctx, -event.y, total)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if ui.get_confirm_rect().collidepoint(pos):
                __confirm(ctx, courses)
                return
            if ui.get_cancel_rect().collidepoint(pos):
                ctx.play_sfx("cancel")
                ctx.registration_manager.clear_selection()
                continue
            if ui.get_scroll_up_rect().collidepoint(pos):
                __scroll_by(ctx, -1, total)
                continue
            if ui.get_scroll_down_rect().collidepoint(pos):
                __scroll_by(ctx, 1, total)
                continue
            index = ui.get_row_index_at(pos, ctx.reg_scroll, total)
            if index >= 0:
                __toggle(ctx, courses[index])


def render(ctx, screen):
    courses = __catalog(ctx)
    ctx.reg_scroll = __ui(ctx).clamp_scroll(ctx.reg_scroll, len(courses))
    __ui(ctx).render(
        screen,
        visible_courses=courses,
        selected=ctx.registration_manager.get_selected_courses(),
        confirmed=[],
        current_credits=ctx.registration_manager.get_current_selected_credits(),
        credit_limit=ctx.registration_manager.get_max_credit_limit(),
        player_name=ctx.player().get_display_name(),
        student_id=ctx.player().get_character_id(),
        semester=ctx.semester().get_semester_number(),
        backlogged=ctx.catalog_builder.get_backlogged(
            ctx.full_catalog, ctx.history()),
        scroll_offset=ctx.reg_scroll,
        newly_unlocked=ctx.catalog_builder.get_newly_unlocked(courses),
    )
