"""
food-recommender: 건강 목표에 맞는 음식 추천 생성
Step 4 처리
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
RULES_PATH = SKILL_DIR / "references" / "food_rules.json"
OUTPUT_PATH = Path("output/recommendation/food_candidates.json")

# 기본 폴백 음식 (룰셋 로드 실패 시 사용)
DEFAULT_FOODS = [
    {
        "name": "현미밥",
        "category": "곡류",
        "reason": "균형 잡힌 영양소 섭취에 도움이 될 수 있습니다",
        "serving_suggestion": "매일 1~2공기"
    },
    {
        "name": "브로콜리",
        "category": "채소",
        "reason": "비타민과 미네랄이 풍부하여 전반적인 건강에 도움이 될 수 있습니다",
        "serving_suggestion": "주 3회 이상, 살짝 데쳐서"
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
    foods = goal_rules.get("foods", [])

    if not foods:
        print(f"[WARN] 룰셋에 '{health_goal}' 음식 정보 없음. 기본값 사용.", file=sys.stderr)
        return DEFAULT_FOODS

    # 2~4개로 제한
    return foods[:4]


def main():
    goal_profile = load_goal_profile()
    rules = load_rules()

    max_retries = 2
    for attempt in range(1, max_retries + 1):
        try:
            foods = recommend(goal_profile, rules)
            if len(foods) >= 2:
                break
        except Exception as e:
            print(f"[WARN] 추천 생성 실패 (시도 {attempt}): {e}", file=sys.stderr)
            foods = DEFAULT_FOODS

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "health_goal": goal_profile.get("primary_goal", ""),
        "foods": foods,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[OK] 음식 추천 완료: {OUTPUT_PATH} ({len(foods)}개)")


if __name__ == "__main__":
    main()
