"""
risk-flagger: 위험 플래그 계산
Step 11 처리
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

OUTPUT_PATH = Path("output/risk/risk_flags.json")

# 안전 질문 후보 (Level 3)
SAFETY_QUESTIONS = [
    {"id": "sq1", "text": "복용 중인 약이 있나요?", "flag": "has_medication",
     "options": ["없음", "있음 (처방약)", "있음 (일반의약품)", "잘 모르겠어요"]},
    {"id": "sq2", "text": "임신·수유 중인가요?", "flag": "pregnancy_or_breastfeeding",
     "options": ["아니요", "임신 중", "수유 중"]},
    {"id": "sq3", "text": "알레르기나 기저질환이 있나요?", "flag": "chronic_condition",
     "options": ["없음", "알레르기 있음", "기저질환 있음", "둘 다 있음"]},
    {"id": "sq4", "text": "이미 복용 중인 영양제가 있나요?", "flag": "duplicate_supplement",
     "options": ["없음", "있음", "잘 모르겠어요"]},
]

# 위험 트리거 응답 매핑
HIGH_RISK_ANSWERS = {
    "has_medication": ["있음 (처방약)", "있음 (일반의약품)"],
    "pregnancy_or_breastfeeding": ["임신 중", "수유 중"],
    "chronic_condition": ["알레르기 있음", "기저질환 있음", "둘 다 있음"],
    "duplicate_supplement": ["있음"],
}


def load_inputs() -> tuple[dict, list]:
    profile_path = Path("output/intake/normalized_profile.json")
    safety_path = Path("output/intake/safety_answers.json")

    if not profile_path.exists():
        print(f"[ERROR] 프로필 파일 없음: {profile_path}", file=sys.stderr)
        sys.exit(1)

    with open(profile_path, encoding="utf-8") as f:
        profile = json.load(f)

    safety_answers = []
    if safety_path.exists():
        with open(safety_path, encoding="utf-8") as f:
            data = json.load(f)
            safety_answers = data.get("safety_answers", [])

    return profile, safety_answers


def calculate_flags(profile: dict, safety_answers: list) -> dict:
    flags = {
        "has_medication": False,
        "pregnancy_or_breastfeeding": False,
        "chronic_condition": False,
        "allergy": False,
        "duplicate_supplement": False,
        "consult_required": False,
    }
    flag_details = []

    # 안전 질문 응답 기반 플래그 계산
    answer_map = {a["question"]: a["answer"] for a in safety_answers}
    for q in SAFETY_QUESTIONS:
        answer = answer_map.get(q["text"])
        if answer in HIGH_RISK_ANSWERS.get(q["flag"], []):
            flags[q["flag"]] = True
            flag_details.append({"flag": q["flag"], "trigger": answer})

    # 알레르기와 기저질환 분리
    if flags.get("chronic_condition"):
        for a in safety_answers:
            if "알레르기" in a.get("answer", ""):
                flags["allergy"] = True

    # consult_required 자동 설정
    if any([flags["has_medication"], flags["pregnancy_or_breastfeeding"],
            flags["chronic_condition"], flags["allergy"], flags["duplicate_supplement"]]):
        flags["consult_required"] = True

    return flags, flag_details


def needs_safety_questions(profile: dict, safety_answers: list) -> bool:
    """안전 질문이 아직 수집되지 않았으면 True 반환."""
    return len(safety_answers) == 0


def main():
    profile, safety_answers = load_inputs()

    max_retries = 2
    for attempt in range(1, max_retries + 1):
        try:
            flags, flag_details = calculate_flags(profile, safety_answers)
            break
        except Exception as e:
            print(f"[WARN] 플래그 계산 실패 (시도 {attempt}): {e}", file=sys.stderr)
            if attempt == max_retries:
                print("[ESCALATE] 위험 플래그 계산 불확실 → safety-reviewer 호출 필요", file=sys.stderr)
                flags = {k: False for k in ["has_medication", "pregnancy_or_breastfeeding",
                                             "chronic_condition", "allergy", "duplicate_supplement"]}
                flags["consult_required"] = True
                flag_details = [{"flag": "escalated", "trigger": "calculation_failed"}]

    safety_questions_needed = needs_safety_questions(profile, safety_answers)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "flags": flags,
        "flag_details": flag_details,
        "safety_questions_needed": safety_questions_needed,
        "safety_questions": SAFETY_QUESTIONS if safety_questions_needed else [],
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    active_flags = [k for k, v in flags.items() if v]
    print(f"[OK] 위험 플래그 계산 완료: {OUTPUT_PATH}")
    print(f"     활성 플래그: {active_flags if active_flags else '없음'}")


if __name__ == "__main__":
    main()
