"""
nutrient-recommender: 건강 목표에 맞는 영양 성분 후보 생성
Step 6 처리
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
RULES_PATH = SKILL_DIR / "references" / "nutrient_rules.json"
OUTPUT_PATH = Path("output/recommendation/nutrient_candidates.json")


def load_inputs() -> tuple[dict, dict]:
    goal_path = Path("output/intent/primary_health_goal.json")
    profile_path = Path("output/intake/normalized_profile.json")

    for p in [goal_path, profile_path]:
        if not p.exists():
            print(f"[ERROR] 필요 파일 없음: {p}", file=sys.stderr)
            sys.exit(1)

    with open(goal_path, encoding="utf-8") as f:
        goal = json.load(f)
    with open(profile_path, encoding="utf-8") as f:
        profile = json.load(f)

    return goal, profile


def load_rules() -> dict:
    if not RULES_PATH.exists():
        print(f"[WARN] 룰셋 파일 없음: {RULES_PATH}", file=sys.stderr)
        return {}
    with open(RULES_PATH, encoding="utf-8") as f:
        return json.load(f)


def recommend(goal: dict, profile: dict, rules: dict) -> list[dict]:
    health_goal = goal.get("primary_goal", "")
    age_group = profile.get("age_group", "unknown")
    gender = profile.get("gender", "unknown")

    goal_rules = rules.get(health_goal, {})
    all_nutrients = goal_rules.get("nutrients", [])

    # 나이대·성별 필터링 (target_profile이 있는 경우)
    filtered = []
    for n in all_nutrients:
        targets = n.get("target_profile", [])
        if not targets or age_group in targets or gender in targets:
            filtered.append(n)

    # 우선순위 정렬 후 1~3개로 제한
    filtered.sort(key=lambda x: x.get("priority", 99))
    return filtered[:3]


def main():
    goal, profile = load_inputs()
    rules = load_rules()

    max_retries = 2
    for attempt in range(1, max_retries + 1):
        try:
            nutrients = recommend(goal, profile, rules)
            if nutrients:
                break
        except Exception as e:
            print(f"[WARN] 추천 생성 실패 (시도 {attempt}): {e}", file=sys.stderr)
            if attempt == max_retries:
                print("[WARN] 영양 성분 추천 생략", file=sys.stderr)
                nutrients = []

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "health_goal": goal.get("primary_goal", ""),
        "nutrients": nutrients,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[OK] 영양 성분 추천 완료: {OUTPUT_PATH} ({len(nutrients)}개)")


if __name__ == "__main__":
    main()
