"""
refinement-manager: 보정 질문 판단 및 추천 보정
Step 8, 10 처리
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

DECISION_OUTPUT = Path("output/decision/refinement_needed.json")
REFINED_OUTPUT = Path("output/recommendation/refined_recommendations.json")
REFINED_CAUTIONS_OUTPUT = Path("output/recommendation/refined_nutrient_cautions.json")

# 보정 질문 후보 풀
QUESTION_POOL = [
    {"id": "r1", "text": "실내 생활이 많은가요?", "options": ["예", "아니요", "모르겠어요"],
     "purpose": "비타민 D 추천 우선순위 결정"},
    {"id": "r2", "text": "식사가 불규칙한가요?", "options": ["예", "아니요", "가끔"],
     "purpose": "종합 비타민 및 식이 추천 조정"},
    {"id": "r3", "text": "잠이 부족한가요?", "options": ["예", "아니요", "가끔"],
     "purpose": "수면 관련 성분 추천 조정"},
    {"id": "r4", "text": "화면을 오래 보나요?", "options": ["예", "아니요"],
     "purpose": "눈 건강 관련 성분 추천 조정"},
    {"id": "r5", "text": "운동이 부족한 편인가요?", "options": ["예", "아니요", "보통"],
     "purpose": "근력·에너지 관련 추천 조정"},
]

# 건강 목표별 추천 보정 질문 (최대 2개)
GOAL_QUESTIONS = {
    "fatigue_management": ["r2", "r3"],
    "sleep_management": ["r3", "r1"],
    "immunity_management": ["r1", "r2"],
    "eye_health": ["r4", "r1"],
    "gut_health": ["r2", "r5"],
    "bone_health": ["r1", "r5"],
    "skin_antioxidant": ["r1", "r2"],
}


def load_candidates() -> dict:
    paths = {
        "food": Path("output/recommendation/food_candidates.json"),
        "habit": Path("output/recommendation/habit_candidates.json"),
        "nutrient": Path("output/recommendation/nutrient_candidates.json"),
        "caution": Path("output/recommendation/nutrient_cautions.json"),
    }
    result = {}
    for key, p in paths.items():
        if p.exists():
            with open(p, encoding="utf-8") as f:
                result[key] = json.load(f)
    return result


def decide_refinement(candidates: dict) -> dict:
    """보정 질문 필요 여부 판단 (규칙 기반 + 에이전트가 이 결과를 참고해 최종 판단)."""
    nutrient_data = candidates.get("nutrient", {})
    nutrients = nutrient_data.get("nutrients", [])
    health_goal = nutrient_data.get("health_goal", "")

    # 영양 성분이 2개 이상이고 우선순위가 비슷하면 보정 질문 필요
    refinement_needed = len(nutrients) >= 2

    question_ids = GOAL_QUESTIONS.get(health_goal, ["r2", "r3"])
    questions = [q for q in QUESTION_POOL if q["id"] in question_ids]

    return {
        "refinement_needed": refinement_needed,
        "questions": questions if refinement_needed else [],
        "reason": f"영양 성분 후보 {len(nutrients)}개 — 추가 정보로 우선순위 결정 가능" if refinement_needed else "1차 추천으로 충분함",
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }


def apply_refinement(candidates: dict, answers: list) -> tuple[dict, dict]:
    """보정 질문 응답을 기반으로 추천 항목 재정렬."""
    nutrients = candidates.get("nutrient", {}).get("nutrients", [])
    cautions = candidates.get("caution", {}).get("cautions", [])

    answer_map = {a["question"]: a["answer"] for a in answers}

    # 실내 생활 많음 → 비타민 D 우선순위 상승
    if answer_map.get("실내 생활이 많은가요?") == "예":
        for n in nutrients:
            if "비타민 D" in n.get("name", "") or "vitamin_d" in n.get("name_en", "").lower():
                n["priority"] = max(1, n.get("priority", 99) - 2)

    # 잠 부족 → 마그네슘 우선순위 상승
    if answer_map.get("잠이 부족한가요?") == "예":
        for n in nutrients:
            if "마그네슘" in n.get("name", "") or "magnesium" in n.get("name_en", "").lower():
                n["priority"] = max(1, n.get("priority", 99) - 1)

    nutrients.sort(key=lambda x: x.get("priority", 99))

    refined_recommendations = {
        "health_goal": candidates.get("nutrient", {}).get("health_goal", ""),
        "foods": candidates.get("food", {}).get("foods", []),
        "habits": candidates.get("habit", {}).get("habits", []),
        "nutrients": nutrients,
        "refined_at": datetime.now(timezone.utc).isoformat(),
    }

    refined_cautions = {
        "cautions": cautions,
        "refined_at": datetime.now(timezone.utc).isoformat(),
    }

    return refined_recommendations, refined_cautions


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "decide"

    if mode == "decide":
        candidates = load_candidates()
        decision = decide_refinement(candidates)

        DECISION_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with open(DECISION_OUTPUT, "w", encoding="utf-8") as f:
            json.dump(decision, f, ensure_ascii=False, indent=2)

        print(f"[OK] 보정 질문 판단 완료: refinement_needed={decision['refinement_needed']}")

    elif mode == "refine":
        answers_path = Path("output/intake/refinement_answers.json")
        if not answers_path.exists():
            print("[WARN] 보정 답변 없음. 1차 추천 유지.", file=sys.stderr)
            sys.exit(0)

        with open(answers_path, encoding="utf-8") as f:
            answers_data = json.load(f)
        answers = answers_data.get("refinement_answers", answers_data.get("answers", []))

        candidates = load_candidates()
        refined_rec, refined_caut = apply_refinement(candidates, answers)

        REFINED_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with open(REFINED_OUTPUT, "w", encoding="utf-8") as f:
            json.dump(refined_rec, f, ensure_ascii=False, indent=2)
        with open(REFINED_CAUTIONS_OUTPUT, "w", encoding="utf-8") as f:
            json.dump(refined_caut, f, ensure_ascii=False, indent=2)

        print(f"[OK] 추천 보정 완료: {REFINED_OUTPUT}")
    else:
        print(f"[ERROR] 알 수 없는 모드: {mode}. 'decide' 또는 'refine' 사용.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
