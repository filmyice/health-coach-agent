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

# 연령대별 기본 폴백 습관
AGE_DEFAULT_HABITS = {
    "toddler": [
        {"title": "하루 1시간 야외 놀이", "description": "햇볕을 받으며 뛰어 노는 야외 활동이 성장과 면역력 증진에 도움이 됩니다", "difficulty": "쉬움", "frequency": "매일"},
        {"title": "편식 줄이기", "description": "채소·과일·단백질을 골고루 먹는 습관이 건강한 성장의 기초입니다", "difficulty": "보통", "frequency": "매일"},
        {"title": "충분한 수면 (10~12시간)", "description": "성장호르몬은 수면 중에 분비되므로 충분한 수면이 성장 발달에 필수입니다", "difficulty": "쉬움", "frequency": "매일"},
    ],
    "child": [
        {"title": "매일 1시간 활동적인 놀이", "description": "달리기·수영·자전거 등 신체 활동이 성장기 체력과 뼈 건강에 도움이 됩니다", "difficulty": "쉬움", "frequency": "매일"},
        {"title": "편식 줄이고 다양하게 먹기", "description": "채소·과일·단백질·유제품을 골고루 먹으면 성장에 필요한 영양소를 고루 섭취할 수 있습니다", "difficulty": "보통", "frequency": "매일"},
        {"title": "충분한 수면 (9~11시간)", "description": "취침 전 스마트폰을 끄고 일정한 시간에 자는 습관이 집중력과 성장에 도움이 됩니다", "difficulty": "쉬움", "frequency": "매일"},
    ],
    "teens": [
        {"title": "규칙적인 수면 (8~10시간)", "description": "성장기에는 충분한 수면이 체력 회복과 학습 능력 향상에 중요합니다", "difficulty": "쉬움", "frequency": "매일"},
        {"title": "스마트폰 사용 시간 제한", "description": "취침 1시간 전 화면을 끄면 수면의 질이 높아지고 집중력이 향상됩니다", "difficulty": "보통", "frequency": "매일"},
        {"title": "주 3회 이상 유산소 운동", "description": "달리기·수영·구기 종목 등 운동이 체력 증진과 스트레스 해소에 효과적입니다", "difficulty": "보통", "frequency": "주 3회 이상"},
    ],
}

DEFAULT_HABITS = [
    {"title": "규칙적인 수면", "description": "매일 같은 시간에 자고 일어나면 몸의 리듬이 안정되어 건강에 도움이 될 수 있습니다", "difficulty": "쉬움", "frequency": "매일"},
    {"title": "물 자주 마시기", "description": "하루 1.5~2L의 물을 나눠 마시면 신진대사에 도움이 될 수 있습니다", "difficulty": "쉬움", "frequency": "매일"},
]


def load_inputs() -> tuple[dict, dict]:
    goal_path    = Path("output/intent/primary_health_goal.json")
    profile_path = Path("output/intake/normalized_profile.json")

    if not goal_path.exists():
        print(f"[ERROR] 건강 목표 파일 없음: {goal_path}", file=sys.stderr)
        sys.exit(1)

    with open(goal_path, encoding="utf-8") as f:
        goal = json.load(f)

    profile = {}
    if profile_path.exists():
        with open(profile_path, encoding="utf-8") as f:
            profile = json.load(f)

    return goal, profile


def load_rules() -> dict:
    if not RULES_PATH.exists():
        print(f"[WARN] 룰셋 파일 없음: {RULES_PATH}", file=sys.stderr)
        return {}
    with open(RULES_PATH, encoding="utf-8") as f:
        return json.load(f)


def is_age_appropriate(habit: dict, age_group: str) -> bool:
    """연령대에 맞는 습관인지 확인."""
    targets = habit.get("target_profile", [])
    if not targets:
        return True   # target_profile 없으면 전 연령 대상
    return age_group in targets


def recommend(goal_profile: dict, profile: dict, rules: dict) -> list[dict]:
    health_goal = goal_profile.get("primary_goal", "")
    age_group   = profile.get("age_group", "unknown")

    goal_rules = rules.get(health_goal, {})
    all_habits = goal_rules.get("habits", [])

    if not all_habits:
        print(f"[WARN] 룰셋에 '{health_goal}' 습관 정보 없음. 기본값 사용.", file=sys.stderr)
        return AGE_DEFAULT_HABITS.get(age_group, DEFAULT_HABITS)

    # 연령대 필터링: 적합한 습관 → 나이 전용 → 전체 대상 순으로 구성
    age_specific = [h for h in all_habits if h.get("target_profile") and age_group in h.get("target_profile", [])]
    general      = [h for h in all_habits if not h.get("target_profile")]
    # 성인 전용(target_profile에 현재 나이 없음) 제외
    excluded     = [h for h in all_habits if h.get("target_profile") and age_group not in h.get("target_profile", [])]

    if excluded:
        titles = [h['title'] for h in excluded]
        print(f"[INFO] 연령({age_group}) 부적합 습관 제외: {titles}", file=sys.stderr)

    # 나이 전용 우선, 일반 보완 — 최대 3개
    combined = age_specific + general
    result = combined[:3]

    if len(result) < 2:
        fallbacks = AGE_DEFAULT_HABITS.get(age_group, DEFAULT_HABITS)
        existing_titles = {h['title'] for h in result}
        for fb in fallbacks:
            if fb['title'] not in existing_titles:
                result.append(fb)
            if len(result) >= 3:
                break

    return result[:3]


def main():
    goal_profile, profile = load_inputs()
    rules = load_rules()

    age_group = profile.get("age_group", "unknown")
    print(f"[INFO] 연령대: {age_group}", file=sys.stderr)

    max_retries = 2
    for attempt in range(1, max_retries + 1):
        try:
            habits = recommend(goal_profile, profile, rules)
            if habits:
                break
        except Exception as e:
            print(f"[WARN] 추천 생성 실패 (시도 {attempt}): {e}", file=sys.stderr)
            habits = AGE_DEFAULT_HABITS.get(age_group, DEFAULT_HABITS)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "health_goal": goal_profile.get("primary_goal", ""),
        "habits":      habits,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[OK] 생활습관 추천 완료: {OUTPUT_PATH} ({len(habits)}개)")


if __name__ == "__main__":
    main()
