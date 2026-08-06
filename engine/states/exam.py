"""
The exam. One ExamSession per registered course, run back to back.

Per course:
    ExamSession(course, skill_tree) -> start() -> tick/submit x3
    -> MainQuest.attempt_qa_optimization(session.get_answers())
    -> GameClock.process_time_consumable(quest)      <-- the ONLY charge
    -> ScreenState.EXAM_RESULT shows the card
The session itself awards nothing; MainQuest.execute_action() records
completion, awards credits and backlogs a failure.

ctx.exam is the run bookkeeping:
    course_index  which registered course is being sat
    message       set only when a course had to be skipped
"""
import pygame

from academic.quest import MainQuest
from engine.exam_session import ExamSession, QUESTION_TIME_LIMIT_SECONDS
from engine.screen_manager import ScreenState

LETTER_KEYS = {pygame.K_a: "A", pygame.K_b: "B",
               pygame.K_c: "C", pygame.K_d: "D"}
BG = (231, 214, 189)


def __courses(ctx):
    return ctx.semester().get_registered_courses()


def __current_course(ctx):
    courses = __courses(ctx)
    index = ctx.exam["course_index"]
    return courses[index] if 0 <= index < len(courses) else None


def enter(ctx):
    # Music is set centrally by engine/soundtrack.py via the router:
    # every screen takes the "menu" track except EXAM, which is silent.
    __ensure_session(ctx)


def __ensure_session(ctx):
    """
    Build and start a session for the current course, if there is one.

    BUG FIX (Iteration 7): the original guard was
    `ctx.exam_session is not None and not ctx.exam_session.is_finished()`.
    The instant a course's 3rd answer was submitted, is_finished()
    became True — and on the very next update() call, THIS guard would
    then be False, so it silently REBUILT a fresh ExamSession for the
    same course before update()'s own `if session.is_finished():` check
    ever got a chance to run. That overwrote the just-finished session
    (and its graded ExamResult) with a brand new ungraded one, so
    __finish_course() never fired and the exam silently never
    completed. Caught this via a full headless run: state stayed on
    EXAM forever instead of reaching EXAM_RESULT.

    Fix: only build a new session when there is NO session at all.
    __finish_course()/__next_course()/close_semester() already reset
    ctx.exam_session to None exactly when it's time for a new one —
    "finished but not yet None" is a valid, meaningful state that
    update()'s own is_finished() check must be allowed to observe.
    """
    if ctx.exam_session is not None:
        return
    course = __current_course(ctx)
    if course is None:
        ctx.exam_session = None
        return
    if not course.is_question_set_complete():
        ctx.exam_session = None                # never read a stale result
        # no questions -> straight through
        __finish_course(ctx, course, {})
        return
    ctx.exam_session = ExamSession(
        course, skill_tree=ctx.player().get_skill_tree())
    ctx.exam_session.start()
    ctx.exam_focus = -1


def __finish_course(ctx, course, answers):
    """The one hand-off. Runs MainQuest through the clock, then routes."""
    quest = MainQuest(quest_id="MQ_" + course.get_course_code(),
                      linked_course=course)
    quest.attempt_qa_optimization(answers)
    ctx.game_clock.process_time_consumable(quest)
    ctx.exam_quest = quest

    if not quest.get_is_completed():
        # No days left to cover this exam. check_semester_end_state()
        # backlogs it later, so nothing extra is needed here.
        ctx.exam["message"] = "NOT ENOUGH TIME LEFT THIS SEMESTER"
        ctx.exam_result = None
        ctx.exam_session = None
        __next_course(ctx)
        return

    quest.evaluate_exam_result()
    ctx.exam_result = (ctx.exam_session.get_result()
                       if ctx.exam_session is not None else None)
    ctx.exam_session = None
    ctx.go(ScreenState.EXAM_RESULT)


def __next_course(ctx):
    ctx.exam["course_index"] += 1
    ctx.exam["answers"] = {}
    ctx.exam["tier_index"] = 0
    ctx.exam_session = None


def close_semester(ctx):
    """Every course attempted: close the term and route onward."""
    ctx.game_clock.check_semester_end_state()
    ctx.exam.update({"course_index": 0, "tier_index": 0,
                     "answers": {}, "message": None})
    ctx.exam_session = None
    ctx.exam_result = None
    if ctx.session.get_is_frozen():
        ctx.go(ScreenState.ENDGAME)
        return
    ctx.game_clock.advance_semester()
    ctx.gates_cleared = set()
    ctx.prop_trigger_counts = {}
    from engine.states import monologue
    monologue.start_semester(ctx, ctx.semester().get_semester_number(),
                             ScreenState.REGISTRATION)
    ctx.go(ScreenState.MONOLOGUE)


# ── frame ──────────────────────────────────────────────────────

def update(ctx, dt):
    ctx.exam_screen.update(dt)

    if __current_course(ctx) is None:
        return                                  # waiting on SPACE, see render

    __ensure_session(ctx)
    session = ctx.exam_session
    if session is None or not session.is_started():
        return
    if session.tick(dt):
        ctx.exam_screen.trigger_time_up()
        ctx.play_sfx("error")
        ctx.exam_focus = -1
    if session.is_finished():
        course = __current_course(ctx)
        answers = session.get_answers()
        ctx.exam["answers"] = dict(answers)
        __finish_course(ctx, course, answers)


def __submit(ctx, letter):
    session = ctx.exam_session
    if session is None or session.is_finished():
        return
    if session.submit_answer(letter):
        ctx.play_sfx("select")
        ctx.exam_focus = -1


def handle_events(ctx, events):
    session = ctx.exam_session
    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                ctx.quit()
                return
            if __current_course(ctx) is None and event.key == pygame.K_SPACE:
                close_semester(ctx)
                return
            if ctx.exam["message"] is not None and event.key == pygame.K_SPACE:
                ctx.exam["message"] = None
                return
            if event.key in LETTER_KEYS:
                __submit(ctx, LETTER_KEYS[event.key])
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if session is None:
                continue
            letters = session.get_current_option_letters()
            rects = ctx.exam_screen.get_option_rects(len(letters))
            for index, rect in enumerate(rects):
                if rect.collidepoint(event.pos):
                    ctx.exam_focus = index
                    ctx.play_sfx("click")
                    break
            else:
                if (ctx.exam_screen.get_submit_rect().collidepoint(event.pos)
                        and 0 <= ctx.exam_focus < len(letters)):
                    __submit(ctx, letters[ctx.exam_focus])


# ── drawing ────────────────────────────────────────────────────

def render(ctx, screen):
    course = __current_course(ctx)
    session = ctx.exam_session

    if course is None or session is None:
        screen.fill(BG)
        font = ctx.fonts["body"]
        text = (ctx.exam["message"]
                or "ALL EXAMS ATTEMPTED — PRESS SPACE TO CONTINUE")
        surf = font.render(text, True, (74, 53, 39))
        screen.blit(surf, (ctx.screen_w // 2 - surf.get_width() // 2, 340))
        return

    question = session.get_current_question() or {}
    ctx.exam_screen.render(
        screen,
        course_code=course.get_course_code(),
        course_name=course.get_course_name(),
        tier=session.get_current_tier() or "",
        tier_index=session.get_tier_index(),
        question_lines=question.get("question_text", ""),
        options=question.get("options", {}),
        focused_index=ctx.exam_focus,
        seconds_left=session.get_time_remaining(),
        seconds_limit=QUESTION_TIME_LIMIT_SECONDS,
    )
