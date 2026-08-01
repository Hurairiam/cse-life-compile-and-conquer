"""Text placeholder. STAGE 5 replaces this with the real map."""
import pygame
from engine.screen_manager import ScreenState

BG = (20, 24, 38)
TEXT = (200, 210, 255)
DIM = (70, 75, 95)
NUM_KEYS = (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
            pygame.K_5, pygame.K_6, pygame.K_7)


def __npcs(ctx):
    return ctx.npc_manager.get_available_npcs(
        ctx.semester().get_semester_number())


def update(ctx, dt):
    if not ctx.game_clock.is_eligible_for_side_activities():
        ctx.go(ScreenState.EXAM)


def handle_events(ctx, events):
    npcs = __npcs(ctx)
    for event in events:
        if event.type != pygame.KEYDOWN:
            continue
        if event.key == pygame.K_ESCAPE:
            ctx.quit()
        elif event.key == pygame.K_e:
            ctx.go(ScreenState.EXAM)
        elif event.key in NUM_KEYS:
            index = NUM_KEYS.index(event.key)
            if index >= len(npcs):
                continue
            npc = npcs[index]
            npc_id = npc.get_character_id()
            available = npc.is_within_availability_window(ctx.player())
            section = "greeting" if available else "unavailable"
            if not ctx.dialogue_manager.load_npc_dialogue(npc_id, section):
                lines = ctx.npc_manager.get_dialogue_lines(
                    npc_id, ctx.player())
                if not lines:
                    ctx.play_sfx("error")
                    continue
                ctx.dialogue_manager.load_dialogue(lines, None)
            ctx.talked_npc_uids.add(npc_id)
            ctx.dialogue_return = ScreenState.EXPLORATION
            ctx.go(ScreenState.DIALOGUE)


def render(ctx, screen):
    screen.fill(BG)
    screen.blit(ctx.fonts["title"].render("Exploration Phase", True, TEXT),
                (40, 60))
    y = 140
    for i, npc in enumerate(__npcs(ctx)):
        ok = npc.is_within_availability_window(ctx.player())
        colour = TEXT if ok else DIM
        suffix = "" if ok else "  (unavailable right now)"
        line = "[%d] %s%s" % (i + 1, npc.get_display_name(), suffix)
        screen.blit(ctx.fonts["body"].render(line, True, colour), (60, y))
        y += 28
    hint = ctx.fonts["small"].render(
        "1-7 talk  |  E exam phase  |  ESC quit", True, DIM)
    screen.blit(hint, (ctx.screen_w // 2 - hint.get_width() // 2,
                       ctx.screen_h - 40))
