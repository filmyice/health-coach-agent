"""
goal-interpreter: 정규화된 프로필 → 대표 건강 목표 해석
Step 3 처리 (스크립트 기반, 규칙 매핑)
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
GOAL_RULES_PATH = SKILL_DIR / "references" / "goal_rules.json"
PROFILE_PATH = Path("output/intake/normalized_profile.json")
OUTPUT_PATH = Path("output/intent/primary_health_goal.json")

# 성별/연령대별 해석 노트 보완
AGE_GENDER_NOTES = {
    ("fatigue_management", "female", "20s"):  "20대 여성 — 빈혈성 피로 가능성 높음, 철분·B12 우선",
    ("fatigue_management", "female", "30s"):  "30대 여성 — 직장·생활 스트레스 피로, 철분·마그네슘 중심",
    ("fatigue_management", "female", "40s"):  "40대 여성 — 호르몬 변화 피로 가능, 전문가 상담 고려",
    ("fatigue_management", "male",   "30s"):  "30대 남성 — 업무 과부하 피로, 코엔자임 Q10·B12 중심",
    ("sleep_management",   "female", "30s"):  "30대 여성 — 멜라토닌보다 마그네슘·L-테아닌 우선 권고",
    ("bone_health",        "female", "40s"):  "40대 여성 — 폐경 전후 골밀도 주의, 칼슘+D3 중심",
    ("bone_health",        "female", "50s_plus"): "50대+ 여성 — 골다공증 위험군, 전문가 상담 병행 권고",
}


def load_goal_rules() -> dict:
    if not GOAL_RULES_PATH.exists():
        print(f"[ERROR] goal_rules.json 없음: {GOAL_RULES_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(GOAL_RULES_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_profile() -> dict:
    if not PROFILE_PATH.exists():
        print(f"[ERROR] 정규화 프로필 없음: {PROFILE_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(PROFILE_PATH, encoding="utf-8") as f:
        return json.load(f)


def interpret(profile: dict, goal_rules: dict) -> dict:
    primary_goal = profile.get("health_goal", "")
    age_group    = profile.get("age_group", "unknown")
    gender       = profile.get("gender", "unknown")

    rule = goal_rules.get(primary_goal)
    if not rule:
        print(f"[WARN] goal_rules에 '{primary_goal}' 없음 — 기본값 사용", file=sys.stderr)
        rule = {"label": primary_goal, "recommendation_direction": {}, "notes": ""}

    direction = rule.get("recommendation_direction", {})
    base_notes = rule.get("notes", "")

    # 연령/성별 특화 노트 추가
    extra_note = AGE_GENDER_NOTES.get((primary_goal, gender, age_group), "")
    interpretation_notes = extra_note if extra_note else (
        f"{profile.get('raw_age_group','?')} {profile.get('raw_gender','?')}의 "
        f"{rule.get('label', primary_goal)} — {base_notes}"
    )

    return {
        "primary_goal": primary_goal,
        "primary_goal_label": rule.get("label", primary_goal),
        "secondary_goals": [],
        "interpretation_notes": interpretation_notes,
        "recommendation_direction": {
            "food_focus":    direction.get("food_focus", []),
            "habit_focus":   direction.get("habit_focus", []),
            "nutrient_focus": direction.get("nutrient_focus", []),
        },
        "age_group": age_group,
        "gender": gender,
        "interpreted_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    profile    = load_profile()
    goal_rules = load_goal_rules()
    result     = interpret(profile, goal_rules)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[OK] 건강 목표 해석 완료: {result['primary_goal_label']} ({result['interpretation_notes'][:50]}...)")


if __name__ == "__main__":
    main()
