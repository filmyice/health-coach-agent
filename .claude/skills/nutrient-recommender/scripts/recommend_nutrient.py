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

# 알레르기 → 제외할 영양 성분 매핑
ALLERGEN_NUTRIENT_EXCLUSIONS = {
    "해산물": ["오메가-3"],
}

# 어린이(7~12세)에게 부적합한 영양 성분 (성인 전용)
CHILD_EXCLUDED_NUTRIENTS = [
    "코엔자임 Q10", "멜라토닌", "L-테아닌", "베르베린", "알파리포산",
    "NAC", "BCAA", "글루타치온", "콜라겐", "밀크시슬", "밀크씨슬",
    "크롬", "여주 추출물", "아슈와간다", "발레리안", "단백질 보충제",
    "녹차 추출물", "식이섬유 (프리바이오틱스)",
]

# 어린이에게 허용되는 영양 성분
CHILD_ALLOWED_NUTRIENTS = [
    "비타민 D", "칼슘", "철분", "아연", "비타민 C", "오메가-3",
    "마그네슘", "프로바이오틱스", "비타민 B12", "프리바이오틱스",
    "비타민 E", "비타민 A", "엽산", "식이섬유", "루테인",
]

# extra_note에서 임신·수유 감지 키워드
PREGNANCY_KEYWORDS = ["임신", "임산부", "수유", "모유"]
# 임신·수유 시 제외할 영양 성분
PREGNANCY_EXCLUDED_NUTRIENTS = ["멜라토닌"]


# ── 연령대별 영양소 조정 ──────────────────────────────────────────
AGE_NUTRIENT_CONFIG = {
    "toddler": {  # 유아 3~6세
        "priority_boost": ["비타민 D", "칼슘", "철분", "아연", "비타민 C", "오메가-3"],
        "daily_intake_overrides": {
            "비타민 D":  {"amount": "400~600IU",  "note": "유아(3~6세) 권장량. 햇볕 노출이 적은 경우 반드시 보충하세요. 소아과 상담 권장."},
            "칼슘":      {"amount": "700~1,000mg","note": "유아(3~6세) 뼈·치아 성장 권장량. 우유·유제품으로 섭취하는 것이 가장 좋습니다."},
            "철분":      {"amount": "7~10mg",     "note": "유아(3~6세) 권장량. 빈혈 예방·뇌 발달에 필수. 반드시 소아과 지도 하에 복용하세요."},
            "아연":      {"amount": "3~5mg",      "note": "유아(3~6세) 권장량. 성장·면역에 필수. 과량 섭취 시 구역감이 생길 수 있습니다."},
            "비타민 C":  {"amount": "15~25mg",    "note": "유아(3~6세) 권장량. 과일·채소로 자연 섭취를 우선하세요."},
            "오메가-3":  {"amount": "500~700mg",  "note": "유아(3~6세) 뇌 발달·시력에 중요한 DHA 포함 오메가-3. 소아용 제품을 선택하세요."},
            "마그네슘":  {"amount": "80~130mg",   "note": "유아(3~6세) 권장량. 신경·근육 발달에 도움이 됩니다."},
            "프로바이오틱스": {"amount": "10억~100억 CFU", "note": "유아용 프로바이오틱스. 장 건강·면역에 도움이 됩니다. 소아 전용 제품을 사용하세요."},
        },
        "age_reason_prefix": "유아기(3~6세)에는",
        "top_warning": "⚠️ 어린이 영양제는 반드시 소아과 전문의와 상담 후 복용하세요. 과량 섭취는 성장에 해로울 수 있습니다.",
    },
    "child": {  # 어린이 7~12세
        "priority_boost": ["비타민 D", "칼슘", "철분", "오메가-3", "아연", "비타민 C"],
        "daily_intake_overrides": {
            "비타민 D":  {"amount": "600~1,000IU", "note": "어린이(7~12세) 권장량. 실내 생활이 많다면 보충이 필요합니다."},
            "칼슘":      {"amount": "1,000~1,200mg","note": "어린이(7~12세) 성장기 뼈·치아 형성 핵심 영양소. 우유와 함께 섭취를 권장합니다."},
            "철분":      {"amount": "8~10mg",      "note": "어린이(7~12세) 권장량. 특히 여아는 초경 후 더 많이 필요합니다."},
            "오메가-3":  {"amount": "700~1,000mg", "note": "어린이(7~12세) 뇌 발달·집중력·시력에 중요한 DHA 포함 오메가-3."},
            "아연":      {"amount": "5~8mg",       "note": "어린이(7~12세) 권장량. 성장·면역·상처 회복에 필수입니다."},
            "비타민 C":  {"amount": "25~45mg",     "note": "어린이(7~12세) 권장량. 면역·철분 흡수 보조에 도움이 됩니다."},
            "마그네슘":  {"amount": "130~240mg",   "note": "어린이(7~12세) 권장량. 근육·신경 발달, 수면의 질에 도움이 됩니다."},
            "프로바이오틱스": {"amount": "100억~500억 CFU", "note": "어린이(7~12세) 장 건강·면역 강화. 어린이 전용 제품을 선택하세요."},
        },
        "age_reason_prefix": "성장기 어린이(7~12세)에는",
        "top_warning": "⚠️ 어린이 영양제는 반드시 소아과 전문의와 상담 후 복용하세요. 성인용 제품은 절대 복용하지 마세요.",
    },
    "teens": {
        "priority_boost": ["칼슘", "비타민 D", "철분", "아연", "비타민 C"],
        "daily_intake_overrides": {
            "칼슘":      {"amount": "1,000~1,300mg", "note": "성장기 권장량 (성인보다 높음). 뼈·치아 형성에 필수입니다."},
            "비타민 D":  {"amount": "600~1,000IU",   "note": "성장기 칼슘 흡수 촉진. 하루 30분 이상 햇볕 노출을 병행하세요."},
            "철분":      {"amount": "11~15mg",        "note": "성장기 및 여성 월경 시 더 많이 필요합니다."},
            "아연":      {"amount": "8~11mg",         "note": "성장·면역·상처 회복에 필수적인 성장기 영양소입니다."},
        },
        "age_reason_prefix": "성장기(10대)에는",
    },
    "20s": {
        "priority_boost": ["철분", "비타민 B12", "마그네슘", "비타민 C", "아연"],
        "daily_intake_overrides": {
            "철분":     {"amount": "10~18mg", "note": "여성 월경기: 18mg, 남성: 10mg. 비타민 C와 함께 섭취하면 흡수율이 높아집니다."},
            "마그네슘": {"amount": "280~350mg", "note": "스트레스·피로가 많은 20대에 부족하기 쉬운 미네랄입니다."},
            "비타민 D": {"amount": "400~800IU", "note": "20대 일반 권장량. 실내 생활이 많거나 햇볕 노출이 부족한 경우 보충을 고려하세요."},
        },
        "age_reason_prefix": "활동량이 많은 20대에는",
    },
    "30s": {
        "priority_boost": ["코엔자임 Q10", "마그네슘", "비타민 B12", "오메가-3"],
        "daily_intake_overrides": {
            "코엔자임 Q10": {"amount": "100~200mg", "note": "30대부터 체내 합성량이 감소하기 시작합니다. 조기 보충을 권장합니다."},
            "오메가-3":     {"amount": "1,000~2,000mg", "note": "30대 심혈관·뇌 건강 유지를 위해 꾸준한 섭취를 권장합니다."},
        },
        "age_reason_prefix": "체력 변화가 시작되는 30대에는",
    },
    "40s": {
        "priority_boost": ["코엔자임 Q10", "오메가-3", "비타민 D", "마그네슘", "비타민 B12"],
        "daily_intake_overrides": {
            "코엔자임 Q10": {"amount": "100~300mg",   "note": "40대 이후 심혈관·에너지 대사 지원. 지용성이므로 식사와 함께 복용하세요."},
            "비타민 D":     {"amount": "800~1,000IU", "note": "40대 이후 흡수율 저하로 권장량이 높아집니다."},
            "오메가-3":     {"amount": "1,000~2,000mg", "note": "40대 혈중 중성지방·혈압 관리에 중요합니다."},
        },
        "age_reason_prefix": "중년기(40대)에는",
    },
    "50s": {
        "priority_boost": ["칼슘", "비타민 D", "비타민 B12", "오메가-3", "코엔자임 Q10"],
        "daily_intake_overrides": {
            "칼슘":      {"amount": "1,000~1,200mg", "note": "50대 이후 골밀도 감소 예방을 위해 성인 기준보다 더 필요합니다."},
            "비타민 D":  {"amount": "800~2,000IU",  "note": "50대 이후 피부 합성 능력 저하로 증량 복용을 권장합니다."},
            "비타민 B12":{"amount": "2.4~4mcg",     "note": "50대 이후 위산 감소로 흡수율이 떨어집니다. 설하정(혀 밑)이나 메틸코발라민 형태를 권장합니다."},
        },
        "age_reason_prefix": "갱년기·중장년기(50대)에는",
    },
    "60s": {
        "priority_boost": ["칼슘", "비타민 D", "비타민 B12", "오메가-3", "마그네슘", "프로바이오틱스"],
        "daily_intake_overrides": {
            "칼슘":      {"amount": "1,200mg",       "note": "60대 이상 골다공증 예방 권장량. 비타민 D와 함께 복용하면 흡수율이 높아집니다."},
            "비타민 D":  {"amount": "1,000~2,000IU", "note": "60대 이상 낙상·골절 예방을 위한 증량 권장. 혈중 농도 검사 후 조절하세요."},
            "비타민 B12":{"amount": "2.4~6mcg",      "note": "60대 이상 흡수율 크게 저하. 설하정(혀 밑) 또는 주사 형태를 고려하세요."},
            "마그네슘":  {"amount": "320~420mg",      "note": "60대 이상 근육 경련·수면 장애·변비 개선에 도움이 됩니다."},
            "오메가-3":  {"amount": "1,000~2,000mg",  "note": "60대 이상 심혈관·인지 기능 보호에 더욱 중요합니다."},
        },
        "age_reason_prefix": "노년 초입(60대)에는",
    },
    "70s_plus": {
        "priority_boost": ["칼슘", "비타민 D", "비타민 B12", "오메가-3", "마그네슘", "비타민 C", "프로바이오틱스"],
        "daily_intake_overrides": {
            "칼슘":      {"amount": "1,200mg",        "note": "70대 이상 골다공증·낙상 위험으로 필수 보충 성분입니다."},
            "비타민 D":  {"amount": "1,500~2,000IU",  "note": "70대 이상 피부 합성 능력이 현저히 감소합니다. 상위 권장량 복용을 권장합니다."},
            "비타민 B12":{"amount": "4~6mcg",         "note": "70대 이상 결핍 위험이 높습니다. 설하정·주사 형태를 우선적으로 권장합니다."},
            "마그네슘":  {"amount": "320~420mg",       "note": "70대 이상 근육 경련·낙상 예방, 인지 기능·수면에도 도움이 됩니다."},
            "오메가-3":  {"amount": "1,000~2,000mg",   "note": "70대 이상 심혈관·치매 예방에 더욱 중요합니다."},
            "비타민 C":  {"amount": "100~200mg",       "note": "70대 이상 면역·항산화·피부 콜라겐 합성 지원에 필요합니다."},
        },
        "age_reason_prefix": "고령기(70대 이상)에는",
    },
    "50s_plus": {  # legacy 호환
        "priority_boost": ["칼슘", "비타민 D", "비타민 B12", "오메가-3", "코엔자임 Q10"],
        "daily_intake_overrides": {
            "칼슘":      {"amount": "1,000~1,200mg", "note": "50대 이상 골밀도 감소 예방을 위해 더 필요합니다."},
            "비타민 D":  {"amount": "800~2,000IU",  "note": "50대 이상 피부 합성 능력 저하로 증량 복용을 권장합니다."},
            "비타민 B12":{"amount": "2.4~4mcg",     "note": "50대 이상 흡수율 감소. 메틸코발라민 형태를 권장합니다."},
        },
        "age_reason_prefix": "50대 이상에는",
    },
    "unknown": {
        "priority_boost": [],
        "daily_intake_overrides": {},
        "age_reason_prefix": "",
    },
}


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


def apply_age_adjustments(nutrients: list, age_group: str, gender: str) -> list:
    """연령대에 따라 우선순위 및 하루 권장량을 조정한다."""
    config = AGE_NUTRIENT_CONFIG.get(age_group, AGE_NUTRIENT_CONFIG["unknown"])
    boost_list = config.get("priority_boost", [])
    overrides  = config.get("daily_intake_overrides", {})
    prefix     = config.get("age_reason_prefix", "")

    result = []
    for n in nutrients:
        n = dict(n)
        name = n.get("name", "")

        # 우선순위 boost
        if name in boost_list:
            boost_amount = len(boost_list) - boost_list.index(name)
            n["priority"] = max(0, n.get("priority", 99) - boost_amount)
            n["age_boosted"] = True  # 이 나이대에 특히 중요한 성분 표시

        # 하루 권장량 override
        if name in overrides:
            n["daily_intake"] = overrides[name]

        # 연령 맞춤 컨텍스트를 reason_seed에 합치지 않고 별도 필드로 분리
        if prefix and n.get("age_boosted"):
            n["age_context"] = prefix  # e.g. "체력 변화가 시작되는 30대에는"

        result.append(n)

    # priority 재정렬
    result.sort(key=lambda x: x.get("priority", 99))
    return result


def recommend(goal: dict, profile: dict, rules: dict) -> list[dict]:
    health_goal = goal.get("primary_goal", "")
    age_group   = profile.get("age_group", "unknown")
    gender      = profile.get("gender", "unknown")
    allergies   = profile.get("allergies") or []
    extra_note  = profile.get("extra_note", "")

    goal_rules   = rules.get(health_goal, {})
    all_nutrients = goal_rules.get("nutrients", [])

    # 1. 나이대·성별 필터링
    filtered = []
    for n in all_nutrients:
        targets = n.get("target_profile", [])
        if not targets or age_group in targets or gender in targets:
            filtered.append(n)

    # 1-1. 어린이(7~12세) 전용 허용 목록 필터링
    if age_group == "child":
        before = [n["name"] for n in filtered]
        filtered = [n for n in filtered if n.get("name") in CHILD_ALLOWED_NUTRIENTS]
        excluded = [name for name in before if name not in [n["name"] for n in filtered]]
        if excluded:
            print(f"[INFO] 어린이 부적합 영양소 제외: {excluded}", file=sys.stderr)

    # 2. 연령대 우선순위·권장량 조정
    filtered = apply_age_adjustments(filtered, age_group, gender)

    # 3. 알레르기 기반 영양 성분 제외
    excluded_by_allergy = set()
    for allergy in allergies:
        excluded_by_allergy.update(ALLERGEN_NUTRIENT_EXCLUSIONS.get(allergy, []))
    if excluded_by_allergy:
        before = [n["name"] for n in filtered]
        filtered = [n for n in filtered if n.get("name") not in excluded_by_allergy]
        after = [n["name"] for n in filtered]
        removed = [n for n in before if n not in after]
        if removed:
            print(f"[INFO] 알레르기({allergies}) 성분 제외: {removed}", file=sys.stderr)

    # 4. 임신·수유 감지 → 특정 성분 제외
    is_pregnant_or_nursing = any(kw in extra_note for kw in PREGNANCY_KEYWORDS)
    if is_pregnant_or_nursing:
        before = [n["name"] for n in filtered]
        filtered = [n for n in filtered if n.get("name") not in PREGNANCY_EXCLUDED_NUTRIENTS]
        after = [n["name"] for n in filtered]
        removed = [n for n in before if n not in after]
        if removed:
            print(f"[INFO] 임신·수유로 인한 성분 제외: {removed}", file=sys.stderr)

    # 5. 상위 1~3개 반환
    return filtered[:3]


def main():
    goal, profile = load_inputs()
    rules = load_rules()

    age_group = profile.get("age_group", "unknown")
    print(f"[INFO] 연령대: {age_group}", file=sys.stderr)

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
        "nutrients":   nutrients,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[OK] 영양 성분 추천 완료: {OUTPUT_PATH} ({len(nutrients)}개)")


if __name__ == "__main__":
    main()
