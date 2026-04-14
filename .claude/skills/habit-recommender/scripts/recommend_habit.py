"""
habit-recommender: 건강 목표에 맞는 생활습관·운동 추천 생성
Step 5 처리
"""
import json
import os
import sys
os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
from pathlib import Path
from datetime import datetime, timezone

SKILL_DIR = Path(__file__).parent.parent
RULES_PATH = SKILL_DIR / "references" / "habit_rules.json"
OUTPUT_PATH = Path("output/recommendation/habit_candidates.json")

DEFAULT_HABITS = [
    {
        "title": "규칙적인 수면",
        "description": "매일 같은 시간에 자고 일어나면 몸의 리듬이 안정되어 건강에 도움이 될 수 있습니다",
        "difficulty": "쉬움",
        "frequency": "매일"
    },
    {
        "title": "물 자주 마시기",
        "description": "하루 1.5~2L의 물을 나눠 마시면 신진대사에 도움이 될 수 있습니다",
        "difficulty": "쉬움",
        "frequency": "매일"
    },
]


def load_goal_profile() -> dict:
    goal_path = Path("output/intent/primary_health_goal.json")
    if not goal_path.exists():
        print(f"[ERROR] 건강 목표 파일 없음: {goal_path}", file=sys.stderr)
        sys.exit(1)
    with open(goal_path, encoding="utf-8") as f:
        return json.load(f)


def load_rules() -> dict:
    if not RULES_PATH.exists():
        print(f"[WARN] 룰셋 파일 없음: {RULES_PATH}", file=sys.stderr)
        return {}
    with open(RULES_PATH, encoding="utf-8") as f:
        return json.load(f)


def recommend(goal_profile: dict, rules: dict) -> list[dict]:
    health_goal = goal_profile.get("primary_goal", "")
    goal_rules = rules.get(health_goal, {})
    habits = goal_rules.get("habits", [])

    if not habits:
        print(f"[WARN] 룰셋에 '{health_goal}' 습관 정보 없음. 기본값 사용.", file=sys.stderr)
        return DEFAULT_HABITS

    # 1~3개로 제한
    return habits[:3]


def main():
    goal_profile = load_goal_profile()
    rules = load_rules()

    max_retries = 2
    for attempt in range(1, max_retries + 1):
        try:
            habits = recommend(goal_profile, rules)
            if habits:
                break
        except Exception as e:
            print(f"[WARN] 추천 생성 실패 (시도 {attempt}): {e}", file=sys.stderr)
            habits = DEFAULT_HABITS

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "health_goal": goal_profile.get("primary_goal", ""),
        "habits": habits,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[OK] 생활습관 추천 완료: {OUTPUT_PATH} ({len(habits)}개)")


if __name__ == "__main__":
    main()
