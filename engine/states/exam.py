"""Text exam. STAGE 7 replaces this with ExamSession + ExamScreen."""
import pygame
from academic.quest import MainQuest
from engine.screen_manager import ScreenState

BG = (25, 18, 35)
TEXT = (200, 210, 255)
ACCENT = (80, 130, 200)
DIM = (70, 75, 95)
TIERS = ("easy", "medium", "hard")
KEYS = {pygame.K_a: "A", pygame.K_b: "B", pygame.K_c: "C", pygame.K_d: "D"}


def __courses(ctx):
    return ctx.semester().get_registered_courses()


def __reset(ctx):
    ctx.exam.update({"course_index": 0, "tier_index": 0,
                     "answers": {}, "message": None})


def __run_quest(ctx, course):
    s = ctx.exam
    quest = MainQuest(quest_id="MQ_" + course.get_course_code(),
                      linked_course=course)
    quest.attempt_qa_optimization(s["answers"])
    ctx.game_clock.process_time_consumable(quest)
    if not quest.get_is_completed():
        s["message"] = "Not enough time — course carries over."
    elif quest.evaluate_exam_result():
        s["message"] = "PASSED — %d credits awarded!" % course.get_credit_value()
    else:
        s["message"] = "FAILED — course backlogged."


def update(ctx, dt):
    s = ctx.exam
    courses = __courses(ctx)
    if s["message"] is not None or s["course_index"] >= len(courses):
        return
    course = courses[s["course_index"]]
    if not course.is_question_set_complete():
        s["tier_index"] = len(TIERS)
        __run_quest(ctx, course)


def handle_events(ctx, events):
    s = ctx.exam
    courses = __courses(ctx)
    for event in events:
        if event.type != pygame.KEYDOWN:
            continue
        if event.key == pygame.K_ESCAPE:
            ctx.quit()
            return
        if s["course_index"] >= len(courses):
            if event.key == pygame.K_SPACE:
                ctx.game_clock.check_semester_end_state()
                __reset(ctx)
                if ctx.session.get_is_frozen():
                    ctx.go(ScreenState.ENDGAME)
                else:
                    ctx.game_clock.advance_semester()
                    from engine.states import monologue
                    monologue.start_semester(
                        ctx, ctx.semester().get_semester_number(),
                        ScreenState.REGISTRATION)
                    ctx.go(ScreenState.MONOLOGUE)
            continue
        if s["message"] is not None:
            if event.key == pygame.K_SPACE:
                s["course_index"] += 1
                s["tier_index"] = 0
                s["answers"] = {}
                s["message"] = None
            continue
        if event.key in KEYS and s["tier_index"] < len(TIERS):
            s["answers"][TIERS[s["tier_index"]]] = KEYS[event.key]
            s["tier_index"] += 1
            if s["tier_index"] >= len(TIERS):
                __run_quest(ctx, courses[s["course_index"]])


def render(ctx, screen):
    screen.fill(BG)
    s = ctx.exam
    courses = __courses(ctx)
    screen.blit(ctx.fonts["title"].render("Exam Phase", True, TEXT), (40, 60))

    def hint(text):
        surf = ctx.fonts["small"].render(text, True, DIM)
        screen.blit(surf, (ctx.screen_w // 2 - surf.get_width() // 2,
                           ctx.screen_h - 40))

    if s["course_index"] >= len(courses):
        screen.blit(ctx.fonts["body"].render(
            "All exams attempted for this semester.", True, ACCENT), (40, 100))
        hint("SPACE continue  |  ESC quit")
        return

    course = courses[s["course_index"]]
    screen.blit(ctx.fonts["body"].render(
        "%s — %s (%d/%d)" % (course.get_course_code(), course.get_course_name(),
                             s["course_index"] + 1, len(courses)),
        True, ACCENT), (40, 100))

    if s["message"] is not None:
        screen.blit(ctx.fonts["title"].render(s["message"], True, TEXT),
                    (40, 160))
        hint("SPACE continue")
        return

    if s["tier_index"] >= len(TIERS):
        return
    tier = TIERS[s["tier_index"]]
    question = course.get_question(tier)
    if question is None:
        return
    screen.blit(ctx.fonts["small"].render(
        "[%s] question %d/3" % (tier.upper(), s["tier_index"] + 1), True, DIM),
        (40, 150))
    screen.blit(ctx.fonts["body"].render(
        question["question_text"], True, TEXT), (40, 180))
    y = 220
    for letter, option in question["options"].items():
        screen.blit(ctx.fonts["body"].render(
            "%s) %s" % (letter, option), True, TEXT), (60, y))
        y += 30
    hint("A / B / C / D to answer  |  ESC quit")
