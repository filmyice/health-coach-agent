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

# 알레르기 카테고리 → 음식명 키워드 매핑
ALLERGEN_KEYWORDS = {
    "유제품":   ["우유", "치즈", "요거트", "버터", "크림", "유청", "카제인", "유제품", "밀크"],
    "견과류":   ["호두", "아몬드", "캐슈넛", "땅콩", "피스타치오", "잣", "헤이즐넛", "견과", "마카다미아"],
    "해산물":   ["생선", "연어", "참치", "고등어", "새우", "오징어", "굴", "조개", "멸치", "어류", "해산물", "해조류", "미역", "김"],
    "밀·글루텐": ["밀", "글루텐", "빵", "국수", "파스타", "보리", "호밀", "통밀"],
    "채식":     ["닭", "소고기", "돼지고기", "육류", "고기", "새우", "생선", "연어", "참치", "고등어", "오징어", "굴", "조개", "멸치"],
}

# 어린이·청소년에게 부적합한 음식 키워드 (카테고리: 건강보조식품 중 성인 전용)
ADULT_ONLY_SUPPLEMENTS = [
    "홍삼", "흑염소", "녹용", "발레리안", "아슈와간다",
    "여주 추출물", "밀크시슬", "베르베린", "알파리포산",
    "NAC", "BCAA", "단백질 보충제", "L-카르니틴",
    "멜라토닌",  # 어린이 멜라토닌은 소아과 처방 필요
]

# 유아(toddler)에게 부적합한 음식 키워드
TODDLER_UNSAFE = [
    "다크초콜릿",  # 카페인·테오브로민
    "견과류", "호두", "아몬드",  # 질식 위험
    "김치",  # 고나트륨·고매운맛
    "마늘",  # 자극성
    "녹차",  # 카페인
    "커피",
]

# 연령대별 음식 제외 규칙
AGE_FOOD_EXCLUSIONS = {
    "toddler": ADULT_ONLY_SUPPLEMENTS + TODDLER_UNSAFE,
    "child":   ADULT_ONLY_SUPPLEMENTS + ["다크초콜릿", "녹차"],
    "teens":   [],  # 성인 보조식품은 teens도 허용하되, 아래 카테고리 필터로 처리
}

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


def load_profile() -> dict:
    profile_path = Path("output/intake/normalized_profile.json")
    if not profile_path.exists():
        return {}
    with open(profile_path, encoding="utf-8") as f:
        return json.load(f)


def load_allergies() -> list:
    return load_profile().get("allergies") or []


def is_allergen(food_name: str, allergies: list) -> bool:
    """음식 이름에 알레르기 키워드가 포함되어 있으면 True"""
    for allergy in allergies:
        keywords = ALLERGEN_KEYWORDS.get(allergy, [allergy])
        for kw in keywords:
            if kw in food_name:
                return True
    return False


def load_rules() -> dict:
    if not RULES_PATH.exists():
        print(f"[WARN] 룰셋 파일 없음: {RULES_PATH}", file=sys.stderr)
        return {}
    with open(RULES_PATH, encoding="utf-8") as f:
        return json.load(f)


def is_age_inappropriate(food: dict, age_group: str) -> bool:
    """연령대에 부적합한 음식이면 True."""
    # target_profile이 있는 경우 포함 여부 확인
    targets = food.get("target_profile", [])
    if targets and age_group not in targets:
        return True

    exclusions = AGE_FOOD_EXCLUSIONS.get(age_group, [])
    if not exclusions:
        return False
    name = food.get("name", "")
    for kw in exclusions:
        if kw in name:
            return True
    # 유아·어린이는 '건강보조식품' 카테고리 자체를 성인 전용 품목 필터
    if age_group in ("toddler", "child") and food.get("category") == "건강보조식품":
        return True
    return False


def recommend(goal_profile: dict, rules: dict, allergies: list, age_group: str = "unknown") -> list[dict]:
    health_goal = goal_profile.get("primary_goal", "")
    goal_rules = rules.get(health_goal, {})
    foods = goal_rules.get("foods", [])

    if not foods:
        print(f"[WARN] 룰셋에 '{health_goal}' 음식 정보 없음. 기본값 사용.", file=sys.stderr)
        return DEFAULT_FOODS

    # 연령대 부적합 음식 제외
    if age_group in AGE_FOOD_EXCLUSIONS:
        age_filtered = [f for f in foods if not is_age_inappropriate(f, age_group)]
        if len(age_filtered) >= 2:
            excluded = [f['name'] for f in foods if is_age_inappropriate(f, age_group)]
            if excluded:
                print(f"[INFO] 연령({age_group}) 부적합 음식 제외: {excluded}", file=sys.stderr)
            foods = age_filtered

    # 알레르기 음식 제외
    if allergies:
        filtered = [f for f in foods if not is_allergen(f.get("name", ""), allergies)]
        if len(filtered) >= 2:
            foods = filtered
        else:
            print(f"[WARN] 알레르기 필터 후 음식이 부족해 원본 사용 (알레르기: {allergies})", file=sys.stderr)

    # 최대 5개 (일반식품 + 건강보조식품 포함)
    return foods[:5]


def main():
    goal_profile = load_goal_profile()
    rules = load_rules()
    profile = load_profile()
    allergies = profile.get("allergies") or []
    age_group = profile.get("age_group", "unknown")

    if allergies:
        print(f"[INFO] 알레르기 필터 적용: {allergies}", file=sys.stderr)
    if age_group in AGE_FOOD_EXCLUSIONS:
        print(f"[INFO] 연령대 음식 필터 적용: {age_group}", file=sys.stderr)

    max_retries = 2
    for attempt in range(1, max_retries + 1):
        try:
            foods = recommend(goal_profile, rules, allergies, age_group)
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
