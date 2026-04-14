"""
Step 12: 최종 통합 추천 생성 — 스크립트 파트
에이전트가 판단한 우선순위를 기반으로 refined_recommendations + cautions 를
final_health_plan.json 으로 통합한다.
에이전트가 이 스크립트를 호출하기 전에 필요한 파일들이 존재해야 한다.
"""
import json
import sys
import os
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from pathlib import Path
from datetime import datetime, timezone

OUTPUT_PATH = Path("output/recommendation/final_health_plan.json")

CANDIDATE_PATHS = [
    # 보정된 추천 우선, 없으면 1차 추천 사용
    ("refined", Path("output/recommendation/refined_recommendations.json")),
    ("initial", Path("output/recommendation/food_candidates.json")),
]
CAUTION_PATHS = [
    Path("output/recommendation/refined_nutrient_cautions.json"),
    Path("output/recommendation/nutrient_cautions.json"),
]
RISK_PATH = Path("output/risk/risk_flags.json")


def load_json(path: Path) -> dict | None:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def load_recommendations() -> dict:
    """보정된 추천 또는 1차 추천 로드."""
    refined = load_json(Path("output/recommendation/refined_recommendations.json"))
    if refined:
        print("[INFO] 보정된 추천 사용 (refined_recommendations.json)")
        return refined

    print("[INFO] 1차 추천 사용 (refined_recommendations 없음)")
    foods   = load_json(Path("output/recommendation/food_candidates.json")) or {}
    habits  = load_json(Path("output/recommendation/habit_candidates.json")) or {}
    nutrients = load_json(Path("output/recommendation/nutrient_candidates.json")) or {}
    return {
        "health_goal": nutrients.get("health_goal", foods.get("health_goal", "")),
        "foods":    foods.get("foods", []),
        "habits":   habits.get("habits", []),
        "nutrients": nutrients.get("nutrients", []),
    }


def load_cautions() -> list:
    for p in CAUTION_PATHS:
        data = load_json(p)
        if data:
            return data.get("cautions", [])
    return []


def validate_balance(foods: list, habits: list, nutrients: list) -> list[str]:
    """추천 균형 검증."""
    warnings = []
    if len(nutrients) > len(foods) + len(habits):
        warnings.append("영양 성분이 음식·생활습관 추천보다 많음 — 균형 조정 필요")
    if not foods:
        warnings.append("음식 추천 없음")
    if not habits:
        warnings.append("생활습관 추천 없음")
    return warnings


def main():
    recs = load_recommendations()
    cautions = load_cautions()
    risk_flags = load_json(RISK_PATH) or {}

    foods     = recs.get("foods", [])
    habits    = recs.get("habits", [])
    nutrients = recs.get("nutrients", [])

    # 균형 검증
    balance_warnings = validate_balance(foods, habits, nutrients)
    for w in balance_warnings:
        print(f"[WARN] {w}", file=sys.stderr)

    # 영양 성분에 주의사항 매핑
    caution_map = {c["nutrient_name"]: c for c in cautions}
    nutrients_with_cautions = []
    for n in nutrients:
        name = n.get("name", "")
        caution = caution_map.get(name, {
            "caution_level": "info",
            "short_cautions": ["복용 전 전문가 상담을 권장합니다"],
            "interaction_flags": [],
            "duplicate_risk": False,
            "consultation_needed": False,
        })
        nutrients_with_cautions.append({**n, "caution": caution})

    # consult_required 플래그 반영
    flags = risk_flags.get("flags", {})
    top_warning = None
    if flags.get("consult_required"):
        top_warning = "일부 추천 성분은 개인 건강 상태에 따라 전문가 상담이 필요할 수 있습니다."

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "health_goal":  recs.get("health_goal", ""),
        "top_warning":  top_warning,
        "foods":        foods,
        "habits":       habits,
        "nutrients":    nutrients_with_cautions,
        "nutrient_cautions": cautions,
        "balance_validated": len(balance_warnings) == 0,
        "assembled_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[OK] 최종 건강 플랜 통합 완료: {OUTPUT_PATH}")
    print(f"     음식 {len(foods)}개 | 습관 {len(habits)}개 | 영양성분 {len(nutrients)}개")


if __name__ == "__main__":
    main()
