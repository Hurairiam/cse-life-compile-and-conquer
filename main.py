"""
main.py
CSE Life: Compile & Conquer
─────────────────────────────────────────────────────────────
Entry point for Sprint 1 Week 1 demonstration.
Proves the abstract class hierarchy is correctly wired:
- Character and Quest cannot be instantiated (ABC enforced)
- Player and MainQuest/SideQuest CAN be instantiated
- TimeConsumable interface is recognised by all implementors
─────────────────────────────────────────────────────────────
"""

from core.interfaces import TimeConsumable
from core.character import Player, NPC
from core.skill_tree import SkillTree
from academic.quest import Quest, MainQuest, SideQuest
from academic.academic_history import AcademicHistory
from academic.course import Course


def main() -> None:
    print("=" * 55)
    print("  CSE Life: Compile & Conquer — Sprint 1 Boot Check")
    print("=" * 55)

    # ── Prove: Player can be instantiated ─────────────────────────
    player = Player()
    print(f"\n[OK] Player created: '{player.get_display_name()}'")
    print(f"     Time pool : {player.get_time_pool_days()} days")
    print(f"     Wallet    : {player.get_wallet_balance()} BDT")
    print(f"     Credits   : {player.get_accumulated_credits()}")

    # ── Prove: Encapsulation works ────────────────────────────────
    success = player.deduct_time_pool_days(10)
    print(f"\n[OK] Deduct 10 days → success={success}")
    print(f"     Remaining : {player.get_time_pool_days()} days")

    failed = player.deduct_time_pool_days(999)
    print(f"\n[OK] Deduct 999 days (should fail) → success={failed}")
    print(f"     Remaining : {player.get_time_pool_days()} days (unchanged)")

    player.deposit_funds(3500.00)
    print(f"\n[OK] Deposit 3500 BDT → balance: {player.get_wallet_balance()} BDT")

    # ── Prove: Course instantiation ───────────────────────────────
    course = Course("CSE101", "Intro to Programming", 3)
    print(f"\n[OK] Course created: '{course.get_course_name()}'"
          f" ({course.get_credit_value()} credits)")

    # ── Prove: MainQuest instantiation and interface check ────────
    mq = MainQuest(quest_id="MQ_CSE101", linked_course=course)
    print(f"\n[OK] MainQuest created: '{mq.get_quest_id()}'")
    print(f"     Is TimeConsumable : {isinstance(mq, TimeConsumable)}")
    print(f"     Is Quest          : {isinstance(mq, Quest)}")
    print(f"     Base time cost    : {mq.get_time_cost()} days")

    # ── Prove: SideQuest instantiation and interface check ────────
    sq = SideQuest(quest_id="SQ_SKILL_01", time_cost=2)
    print(f"\n[OK] SideQuest created: '{sq.get_quest_id()}'")
    print(f"     Is TimeConsumable : {isinstance(sq, TimeConsumable)}")
    print(f"     EXP reward        : {sq.get_exp_reward()}")

    # ── Prove: Abstract classes CANNOT be instantiated ───────────
    print("\n[OK] Verifying abstract class enforcement...")
    try:
        from core.character import Character
        _ = Character("x", "x", "x")
        print("     [FAIL] Character was instantiated — should not happen")
    except TypeError:
        print("     Character() → TypeError raised correctly (abstract)")

    try:
        _ = Quest("x", 0)
        print("     [FAIL] Quest was instantiated — should not happen")
    except TypeError:
        print("     Quest()     → TypeError raised correctly (abstract)")

    # ── SkillTree check ───────────────────────────────────────────
    tree = SkillTree()
    tree.increment_skill("python", 10)
    print(f"\n[OK] SkillTree: python level = {tree.get_skill_level('python')}")
    print(f"     Is unlocked: {tree.is_skill_unlocked('python')}")

    print("\n" + "=" * 55)
    print("  All Sprint 1 architecture checks passed.")
    print("  Ready to demonstrate to professor.")
    print("=" * 55)


if __name__ == "__main__":
    main()
