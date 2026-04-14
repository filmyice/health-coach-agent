"""
intake-normalizer: 프론트엔드 JSON 입력 검증 및 정규화
Step 1~2 처리
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

# 허용 enum 정의
ALLOWED_HEALTH_GOALS = [
    "피로 관리", "수면 관리", "면역 관리", "눈 건강", "장 건강", "뼈 건강", "피부·항산화",
    "체중 관리", "혈당 관리", "스트레스 관리", "운동 관리", "심혈관 건강", "모발 건강", "간 건강",
]
ALLOWED_AGE_GROUPS = ["10대", "20대", "30대", "40대", "50대", "60대", "70대 이상", "50대 이상", "unknown"]
ALLOWED_GENDERS = ["여성", "남성", "unknown"]

# 내부 코드값 매핑
GOAL_MAP = {
    "피로 관리": "fatigue_management",
    "수면 관리": "sleep_management",
    "면역 관리": "immunity_management",
    "눈 건강": "eye_health",
    "장 건강": "gut_health",
    "뼈 건강": "bone_health",
    "피부·항산화": "skin_antioxidant",
    "체중 관리": "weight_management",
    "혈당 관리": "blood_sugar_management",
    "스트레스 관리": "stress_management",
    "운동 관리": "exercise_recovery",
    "심혈관 건강": "cardiovascular_health",
    "모발 건강": "hair_health",
    "간 건강": "liver_health",
}

AGE_MAP = {
    "10대": "teens",
    "20대": "20s",
    "30대": "30s",
    "40대": "40s",
    "50대": "50s",
    "60대": "60s",
    "70대 이상": "70s_plus",
    "50대 이상": "50s_plus",
    "unknown": "unknown",
}

GENDER_MAP = {
    "여성": "female",
    "남성": "male",
    "unknown": "unknown",
}

OUTPUT_DIR = Path("output/intake")


def validate_input(data: dict) -> list[str]:
    """스키마 검증. 오류 목록 반환."""
    errors = []
    if "health_goal" not in data:
        errors.append("필수 필드 누락: health_goal")
    elif data["health_goal"] not in ALLOWED_HEALTH_GOALS:
        errors.append(f"허용되지 않은 health_goal 값: {data['health_goal']}")

    age = data.get("age_group", "unknown")
    if age not in ALLOWED_AGE_GROUPS:
        errors.append(f"허용되지 않은 age_group 값: {age}")

    gender = data.get("gender", "unknown")
    if gender not in ALLOWED_GENDERS:
        errors.append(f"허용되지 않은 gender 값: {gender}")

    return errors


def normalize(data: dict) -> dict:
    """입력값을 내부 표준 포맷으로 변환."""
    return {
        "health_goal": GOAL_MAP.get(data["health_goal"], data["health_goal"]),
        "age_group": AGE_MAP.get(data.get("age_group", "unknown"), "unknown"),
        "gender": GENDER_MAP.get(data.get("gender", "unknown"), "unknown"),
        "raw_health_goal": data["health_goal"],
        "raw_age_group": data.get("age_group", "unknown"),
        "raw_gender": data.get("gender", "unknown"),
        "normalized_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    input_path = Path("output/intake/raw_minimal_input.json")
    if not input_path.exists():
        print(f"[ERROR] 입력 파일 없음: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    # Step 1: 검증
    max_retries = 2
    for attempt in range(1, max_retries + 1):
        errors = validate_input(data)
        if not errors:
            break
        print(f"[WARN] 검증 실패 (시도 {attempt}/{max_retries}): {errors}", file=sys.stderr)
        if attempt == max_retries:
            print(json.dumps({"error": "INPUT_VALIDATION_FAILED", "details": errors}))
            sys.exit(2)

    # Step 2: 정규화
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    normalized = normalize(data)

    out_path = OUTPUT_DIR / "normalized_profile.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)

    print(f"[OK] 정규화 완료: {out_path}")
    print(json.dumps(normalized, ensure_ascii=False))


if __name__ == "__main__":
    main()
