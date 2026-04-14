"""
caution-generator: 추천 영양 성분별 주의사항 생성
Step 7 처리
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
RULES_PATH = SKILL_DIR / "references" / "caution_rules.json"
OUTPUT_PATH = Path("output/recommendation/nutrient_cautions.json")

DEFAULT_CAUTION = {
    "caution_level": "info",
    "short_cautions": ["전문가와 상담 후 복용을 권장합니다"],
    "interaction_flags": [],
    "duplicate_risk": False,
    "consultation_needed": False,
}


def load_inputs() -> tuple[dict, dict]:
    nutrient_path = Path("output/recommendation/nutrient_candidates.json")
    profile_path = Path("output/intake/normalized_profile.json")

    for p in [nutrient_path, profile_path]:
        if not p.exists():
            print(f"[ERROR] 필요 파일 없음: {p}", file=sys.stderr)
            sys.exit(1)

    with open(nutrient_path, encoding="utf-8") as f:
        nutrients = json.load(f)
    with open(profile_path, encoding="utf-8") as f:
        profile = json.load(f)

    return nutrients, profile


def load_rules() -> dict:
    if not RULES_PATH.exists():
        print(f"[WARN] 주의사항 룰 DB 없음: {RULES_PATH}", file=sys.stderr)
        return {}
    with open(RULES_PATH, encoding="utf-8") as f:
        return json.load(f)


def generate_caution(nutrient: dict, profile: dict, rules: dict) -> dict:
    name_en = nutrient.get("name_en", "")
    name = nutrient.get("name", "")
    rule = rules.get(name_en) or rules.get(name, {})

    if not rule:
        caution = dict(DEFAULT_CAUTION)
        caution["short_cautions"] = nutrient.get("caution_seed", ["복용 전 전문가 상담을 권장합니다"])
        return {"nutrient_name": name, **caution}

    # 프로필 기반 상담 필요 여부 판단
    consultation_needed = rule.get("consultation_needed", False)
    gender = profile.get("gender", "unknown")
    if gender == "female" and rule.get("female_consult", False):
        consultation_needed = True

    return {
        "nutrient_name": name,
        "caution_level": rule.get("caution_level", "info"),
        "short_cautions": rule.get("short_cautions", []),
        "interaction_flags": rule.get("interaction_flags", []),
        "duplicate_risk": rule.get("duplicate_risk", False),
        "consultation_needed": consultation_needed,
    }


def main():
    nutrients_data, profile = load_inputs()
    rules = load_rules()

    nutrients = nutrients_data.get("nutrients", [])
    cautions = []

    for nutrient in nutrients:
        max_retries = 2
        for attempt in range(1, max_retries + 1):
            try:
                caution = generate_caution(nutrient, profile, rules)
                cautions.append(caution)
                break
            except Exception as e:
                print(f"[WARN] '{nutrient.get('name')}' 주의사항 생성 실패 (시도 {attempt}): {e}", file=sys.stderr)
                if attempt == max_retries:
                    fallback = {"nutrient_name": nutrient.get("name", ""), **DEFAULT_CAUTION}
                    cautions.append(fallback)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "cautions": cautions,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[OK] 주의사항 생성 완료: {OUTPUT_PATH} ({len(cautions)}개)")


if __name__ == "__main__":
    main()
