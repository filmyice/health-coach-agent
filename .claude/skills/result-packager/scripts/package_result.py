"""
result-packager: 최종 결과 병합 및 사용자 출력 생성
Step 19, 21 처리
"""
import json
import os
import sys
import uuid
os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
from pathlib import Path
from datetime import datetime, timezone

OUTPUT_JSON = Path("output/final/user_result.json")
OUTPUT_MD = Path("output/final/user_result.md")

DISCLAIMERS = [
    "이 내용은 의료적 진단이 아닙니다.",
    "복용 중인 약이나 임신·수유 중이라면 전문가 상담이 필요할 수 있어요.",
]


def load_file(path: Path, required: bool = True) -> dict | None:
    if not path.exists():
        if required:
            print(f"[ERROR] 필수 파일 없음: {path}", file=sys.stderr)
            sys.exit(1)
        print(f"[WARN] 선택 파일 없음 (건너뜀): {path}", file=sys.stderr)
        return None
    with open(path, encoding="utf-8") as f:
        if path.suffix == ".md":
            return {"content": f.read()}
        return json.load(f)


REASON_TEMPLATE = {
    "fatigue_management": {
        "철분":        "철 결핍은 피로의 주요 원인 중 하나입니다. 특히 여성에게 흔하게 나타납니다.",
        "비타민 B12":  "에너지 대사에 필수적입니다. 식사가 불규칙하다면 결핍이 생기기 쉽습니다.",
        "마그네슘":    "근육 이완과 에너지 생성에 관여하며 수면의 질 개선에도 도움이 될 수 있습니다.",
        "코엔자임 Q10":"세포 에너지 생성에 관여하여 만성 피로 개선에 도움이 될 수 있습니다.",
    },
    "sleep_management": {
        "마그네슘":  "신경 안정과 수면 유도에 도움이 될 수 있는 미네랄입니다.",
        "멜라토닌":  "수면 리듬 조절에 도움이 될 수 있습니다. 단기 사용을 권장합니다.",
        "L-테아닌":  "카페인 없이 이완 효과를 줄 수 있어 취침 전 고려해 볼 수 있습니다.",
    },
    "immunity_management": {
        "비타민 C":  "항산화 작용과 면역 세포 활성화에 도움이 될 수 있습니다.",
        "비타민 D":  "면역 조절에 관여하며, 실내 생활이 많은 경우 특히 부족하기 쉽습니다.",
        "아연":      "면역 반응과 상처 회복에 관여하는 필수 미네랄입니다.",
    },
    "eye_health": {
        "루테인":    "황반 색소 밀도 유지에 도움이 될 수 있습니다.",
        "지아잔틴":  "루테인과 함께 눈 건강 보호에 도움이 될 수 있습니다.",
        "오메가-3":  "안구 건조 개선과 눈 표면 건강 유지에 관여합니다.",
    },
    "gut_health": {
        "프로바이오틱스": "장내 유익균을 보충하여 소화 기능과 면역 균형에 도움이 될 수 있습니다.",
        "프리바이오틱스": "유익균의 먹이가 되어 장내 균형 유지에 도움이 될 수 있습니다.",
        "식이섬유":  "장 운동을 돕고 배변 규칙성 개선에 도움이 될 수 있습니다.",
    },
    "bone_health": {
        "칼슘":      "뼈와 치아의 주요 구성 성분입니다. 비타민 D와 함께 섭취하면 흡수가 향상됩니다.",
        "비타민 D":  "칼슘 흡수를 도와 뼈 건강 유지에 중요합니다.",
        "마그네슘":  "뼈 기질 형성에 관여하며 칼슘과 함께 뼈 건강에 도움이 될 수 있습니다.",
    },
    "skin_antioxidant": {
        "비타민 C":  "콜라겐 합성에 필요하며 항산화 작용으로 피부 건강에 도움이 될 수 있습니다.",
        "콜라겐":    "피부 탄력과 수분 유지에 도움이 될 수 있습니다.",
        "글루타치온": "강력한 항산화 물질로 피부 미백과 산화 스트레스 감소에 도움이 될 수 있습니다.",
    },
}

# 기저질환 → 영양소 상호작용 경고
CONDITION_NUTRIENT_WARNINGS = {
    "고혈압": {
        "코엔자임 Q10": ("warning", "혈압약과 CoQ10 병용 시 혈압이 추가로 낮아질 수 있어 용량 모니터링이 필요합니다."),
        "오메가-3":    ("warning", "고용량(3g 이상) 오메가-3는 혈압에 영향을 줄 수 있습니다. 의사와 상담 후 복용하세요."),
        "마그네슘":    ("info",    "마그네슘은 혈압 조절에 도움이 될 수 있습니다. 권장량 이내로 복용하세요."),
        "칼슘":        ("warning", "칼슘 채널 차단제 계열 혈압약 복용 중이라면 칼슘 보충제 복용 시간을 분리하세요."),
    },
    "당뇨": {
        "크롬":      ("consult", "당뇨약과 크롬 병용 시 혈당이 과도하게 낮아질 수 있습니다. 반드시 의사와 상담 후 복용하세요."),
        "베르베린":  ("consult", "당뇨약(메트포르민 등)과 유사 작용으로 저혈당 위험이 있습니다. 의사 상담이 필요합니다."),
        "알파리포산":("warning", "혈당 강하 효과가 중첩될 수 있습니다. 복용 중 혈당 모니터링을 권장합니다."),
        "마그네슘":  ("info",    "마그네슘은 인슐린 감수성 개선에 도움될 수 있습니다. 혈당 변화를 관찰하세요."),
    },
    "갑상선": {
        "칼슘":  ("warning", "갑상선 약(레보티록신)과 칼슘 보충제는 반드시 4시간 이상 간격을 두고 복용하세요."),
        "철분":  ("warning", "갑상선약 복용 시 철분과 동시 복용 시 흡수를 방해할 수 있습니다. 2~4시간 간격을 두세요."),
        "아연":  ("info",    "갑상선 기능 저하 시 아연이 도움될 수 있으나, 갑상선약과 시간 간격을 두고 복용하세요."),
    },
    "신장질환": {
        "칼슘":    ("consult", "신장질환이 있는 경우 칼슘 과잉 섭취는 위험할 수 있습니다. 반드시 전문가 상담 후 복용하세요."),
        "마그네슘":("consult", "신장 기능 저하 시 마그네슘 배출이 어려워 고용량 복용은 위험합니다. 전문가 상담이 필요합니다."),
        "비타민 D":("warning", "신장질환 시 비타민 D 대사가 달라집니다. 의사 처방 하에 복용하세요."),
        "오메가-3":("warning", "신장질환이 있는 경우 고용량 오메가-3는 주의가 필요합니다. 의사와 상담하세요."),
    },
    "간질환": {
        "NAC":    ("warning", "간질환 상태에 따라 NAC이 도움이 될 수도, 역효과가 날 수도 있습니다. 의사 상담이 필요합니다."),
        "밀크씨슬":("info",   "일반 간질환에는 밀크씨슬이 도움될 수 있으나, 심한 간경변의 경우 의사 상담을 권장합니다."),
        "비타민 E":("warning", "간질환이 있는 경우 고용량 비타민 E는 주의가 필요합니다. 권장량 이내로 복용하세요."),
    },
}

# 복용 중인 약 → 영양소 상호작용 경고
MEDICATION_NUTRIENT_WARNINGS = {
    "혈압약": {
        "코엔자임 Q10":("warning", "혈압약과 CoQ10 병용 시 혈압이 추가로 낮아질 수 있어 모니터링이 필요합니다."),
        "마그네슘":    ("warning", "일부 혈압약과 마그네슘 병용 시 혈압이 과도하게 낮아질 수 있습니다."),
        "오메가-3":    ("warning", "오메가-3의 혈압 강하 효과와 혈압약이 중첩될 수 있습니다. 의사에게 알려주세요."),
        "칼슘":        ("warning", "칼슘 채널 차단제 계열 혈압약 복용 중 칼슘 보충제는 복용 시간을 분리하세요."),
    },
    "당뇨약": {
        "크롬":      ("consult", "당뇨약과 크롬 병용 시 저혈당 위험이 있습니다. 반드시 의사와 상담하세요."),
        "베르베린":  ("consult", "당뇨약과 베르베린은 혈당 강하 효과가 중첩됩니다. 의사 지도 하에 복용하세요."),
        "알파리포산":("warning", "당뇨약과 함께 복용 시 혈당 강하 효과가 강해질 수 있습니다. 혈당을 모니터링하세요."),
    },
    "항응고제": {
        "오메가-3":    ("consult", "항응고제(와파린 등)와 오메가-3 병용 시 출혈 위험이 높아집니다. 반드시 의사와 상담하세요."),
        "비타민 E":    ("consult", "항응고제와 비타민 E 병용 시 항응고 효과가 강해질 수 있습니다. 전문가 상담이 필요합니다."),
        "비타민 C":    ("warning", "고용량 비타민 C(1g 이상)는 와파린 효과에 영향을 줄 수 있습니다. 적정량을 유지하세요."),
        "아연":        ("warning", "항응고제와 아연 병용 시 상호작용 가능성이 있습니다. 의사에게 알려주세요."),
        "프로바이오틱스":("info", "프로바이오틱스는 장내 비타민 K 생성에 영향을 줄 수 있어 와파린 수치 모니터링이 필요합니다."),
    },
    "항우울제": {
        "L-테아닌":  ("warning", "일부 항우울제와 병용 시 진정 효과가 강해질 수 있습니다. 의사에게 알려주세요."),
        "멜라토닌":  ("warning", "SSRI/SNRI 계열 항우울제와 멜라토닌 병용 시 상호작용 가능성이 있습니다. 의사 상담을 권장합니다."),
        "마그네슘":  ("info",    "항우울제와 마그네슘 병용은 일반적으로 안전하나, 고용량 복용 시 의사에게 알려주세요."),
        "BCAA":      ("warning", "항우울제 복용 중 아미노산 보충제는 세로토닌 시스템에 영향을 줄 수 있습니다."),
    },
}

# 기저질환 → 음식 주의 키워드
CONDITION_FOOD_CAUTIONS = {
    "고혈압":   {"keywords": ["김치", "멸치", "된장", "명란"],        "note": "⚠️ 고혈압: 나트륨 함량이 높아 섭취량을 제한하는 것이 좋습니다."},
    "당뇨":     {"keywords": ["바나나", "고구마", "현미", "과일"],     "note": "⚠️ 당뇨: 혈당 상승 속도를 늦추기 위해 소량씩 나눠 섭취를 권장합니다."},
    "신장질환": {"keywords": ["바나나", "멸치", "김치", "토마토", "감자"], "note": "⚠️ 신장질환: 칼륨·인 함량이 높아 섭취량을 전문가와 상의하세요."},
    "간질환":   {"keywords": ["마늘"],                                "note": "⚠️ 간질환: 마늘을 과량 섭취하면 간에 부담을 줄 수 있습니다. 적정량을 유지하세요."},
}

NAME_EN_MAP = {
    "철분": "Iron", "비타민 B12": "Vitamin B12", "마그네슘": "Magnesium",
    "코엔자임 Q10": "CoQ10", "멜라토닌": "Melatonin", "L-테아닌": "L-Theanine",
    "비타민 C": "Vitamin C", "비타민 D": "Vitamin D", "아연": "Zinc",
    "루테인": "Lutein", "지아잔틴": "Zeaxanthin", "오메가-3": "Omega-3",
    "프로바이오틱스": "Probiotics", "프리바이오틱스": "Prebiotics",
    "식이섬유": "Dietary Fiber", "칼슘": "Calcium", "콜라겐": "Collagen",
    "글루타치온": "Glutathione",
}


def _load_caution_rules() -> dict:
    rules_path = (Path(__file__).parent.parent.parent /
                  "caution-generator" / "references" / "caution_rules.json")
    if rules_path.exists():
        with open(rules_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _load_nutrient_rules() -> dict:
    rules_path = (Path(__file__).parent.parent.parent /
                  "nutrient-recommender" / "references" / "nutrient_rules.json")
    if rules_path.exists():
        with open(rules_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _load_food_rules() -> dict:
    rules_path = (Path(__file__).parent.parent.parent /
                  "food-recommender" / "references" / "food_rules.json")
    if rules_path.exists():
        with open(rules_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _load_habit_rules() -> dict:
    rules_path = (Path(__file__).parent.parent.parent /
                  "habit-recommender" / "references" / "habit_rules.json")
    if rules_path.exists():
        with open(rules_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _inject_extra_warnings(nutrient_name: str, caution: dict, conditions: list, medications: list) -> dict:
    """기저질환·복용약에 따라 영양소 주의사항 보강."""
    caution = dict(caution)
    items = list(caution.get("items", []))
    level = caution.get("level", "info")
    level_order = {"info": 0, "warning": 1, "consult": 2}

    for cond in conditions:
        warnings = CONDITION_NUTRIENT_WARNINGS.get(cond, {})
        if nutrient_name in warnings:
            lvl, msg = warnings[nutrient_name]
            if f"[{cond}]" not in " ".join(items):
                items.append(f"[{cond}] {msg}")
            if level_order.get(lvl, 0) > level_order.get(level, 0):
                level = lvl

    for med in medications:
        if med == "없음":
            continue
        warnings = MEDICATION_NUTRIENT_WARNINGS.get(med, {})
        if nutrient_name in warnings:
            lvl, msg = warnings[nutrient_name]
            if f"[{med}]" not in " ".join(items):
                items.append(f"[{med}] {msg}")
            if level_order.get(lvl, 0) > level_order.get(level, 0):
                level = lvl

    caution["items"] = items
    caution["level"] = level
    caution["consultation_needed"] = caution.get("consultation_needed", False) or (level == "consult")
    return caution


def _apply_condition_food_notes(foods: list, conditions: list) -> list:
    """기저질환에 따라 음식 serving_suggestion에 주의 메모 추가."""
    result = []
    for f in foods:
        f = dict(f)
        name = f.get("name", "")
        notes = []
        for cond in conditions:
            rule = CONDITION_FOOD_CAUTIONS.get(cond, {})
            for kw in rule.get("keywords", []):
                if kw in name:
                    notes.append(rule["note"])
                    break
        if notes:
            original = f.get("serving_suggestion", "")
            f["serving_suggestion"] = original + " " + " ".join(notes) if original else " ".join(notes)
        result.append(f)
    return result


def build_json_result(
    health_plan: dict,
    price_comparison: dict | None,
    risk_flags: dict,
    profile: dict,
    extra_goals: list | None = None,
) -> dict:
    goal = health_plan.get("health_goal", "")
    nutrients_raw = health_plan.get("nutrients", [])
    cautions_raw = health_plan.get("nutrient_cautions", [])

    conditions  = profile.get("conditions", []) or []
    medications = profile.get("medications", []) or []
    age_group   = profile.get("age_group", "unknown")

    # 연령대별 하루 권장량 override 맵 (recommend_nutrient.py와 동일 데이터)
    AGE_DAILY_INTAKE_OVERRIDES = {
        "toddler":  {"비타민 D": {"amount": "400~600IU", "note": "유아(3~6세) 권장량"}, "칼슘": {"amount": "700~1,000mg", "note": "유아(3~6세) 권장량"}, "철분": {"amount": "7~10mg", "note": "유아(3~6세) 권장량"}, "오메가-3": {"amount": "500~700mg", "note": "유아 DHA 포함 권장량"}},
        "child":    {"비타민 D": {"amount": "600~1,000IU", "note": "어린이(7~12세) 권장량"}, "칼슘": {"amount": "1,000~1,200mg", "note": "어린이(7~12세) 성장기 권장량"}, "철분": {"amount": "8~10mg", "note": "어린이(7~12세) 권장량"}, "오메가-3": {"amount": "700~1,000mg", "note": "어린이 뇌발달·집중력"}},
        "teens":    {"칼슘": {"amount": "1,000~1,300mg", "note": "성장기 권장량 (성인보다 높음)"}, "비타민 D": {"amount": "600~1,000IU", "note": "성장기 칼슘 흡수 촉진"}, "철분": {"amount": "11~15mg", "note": "성장기 권장량"}},
        "20s":      {"철분": {"amount": "10~18mg", "note": "여성 18mg, 남성 10mg"}},
        "30s":      {"코엔자임 Q10": {"amount": "100~200mg", "note": "30대부터 체내 합성 감소"}, "오메가-3": {"amount": "1,000~2,000mg", "note": "30대 심혈관·뇌 건강 유지"}},
        "40s":      {"코엔자임 Q10": {"amount": "100~300mg", "note": "40대 이후 증량 권장"}, "비타민 D": {"amount": "800~1,000IU", "note": "40대 이후 흡수율 저하"}},
        "50s":      {"칼슘": {"amount": "1,000~1,200mg", "note": "50대 이후 골밀도 감소 예방"}, "비타민 D": {"amount": "800~2,000IU", "note": "50대 이후 증량 권장"}, "비타민 B12": {"amount": "2.4~4mcg", "note": "50대 이후 흡수율 저하"}},
        "60s":      {"칼슘": {"amount": "1,200mg", "note": "60대 이상 골다공증 예방"}, "비타민 D": {"amount": "1,000~2,000IU", "note": "60대 이상 낙상·골절 예방"}, "비타민 B12": {"amount": "2.4~6mcg", "note": "60대 이상 설하정 권장"}, "마그네슘": {"amount": "320~420mg", "note": "60대 이상 근육 경련·수면 개선"}, "오메가-3": {"amount": "1,000~2,000mg", "note": "60대 이상 심혈관·인지 기능"}},
        "70s_plus": {"칼슘": {"amount": "1,200mg", "note": "70대 이상 필수 보충"}, "비타민 D": {"amount": "1,500~2,000IU", "note": "70대 이상 상위 권장량"}, "비타민 B12": {"amount": "4~6mcg", "note": "70대 이상 설하정·주사 권장"}, "마그네슘": {"amount": "320~420mg", "note": "70대 이상 낙상·인지 기능"}, "오메가-3": {"amount": "1,000~2,000mg", "note": "70대 이상 심혈관·치매 예방"}, "비타민 C": {"amount": "100~200mg", "note": "70대 이상 면역·항산화"}},
        "50s_plus": {"칼슘": {"amount": "1,000~1,200mg", "note": "50대 이상 골밀도 감소 예방"}, "비타민 D": {"amount": "800~2,000IU", "note": "50대 이상 증량 권장"}, "비타민 B12": {"amount": "2.4~4mcg", "note": "50대 이상 흡수율 저하"}},
    }
    _age_overrides = AGE_DAILY_INTAKE_OVERRIDES.get(age_group, {})

    caution_map = {c["nutrient_name"]: c for c in cautions_raw}

    nutrients_out = []
    for n in nutrients_raw:
        name   = n.get("name", "")
        caution = caution_map.get(name, {})
        reason = (n.get("reason") or n.get("reason_seed") or
                  REASON_TEMPLATE.get(goal, {}).get(name, f"{name} 보충을 고려해 볼 수 있습니다."))
        base_caution = {
            "level":               caution.get("caution_level", "info"),
            "items":               caution.get("short_cautions", []),
            "interaction_flags":   caution.get("interaction_flags", []),
            "consultation_needed": caution.get("consultation_needed", False),
        }
        enriched_caution = _inject_extra_warnings(name, base_caution, conditions, medications)
        nutrients_out.append({
            "name":         name,
            "name_en":      n.get("name_en") or NAME_EN_MAP.get(name, ""),
            "reason":       reason,
            "goal_key":     goal,
            "daily_intake": n.get("daily_intake"),
            "best_time":    n.get("best_time"),
            "cautions":     enriched_caution,
        })

    # 2번째 목표 영양 성분 보충 (중복 제외, 최대 2개)
    secondary_goals = [g for g in (extra_goals or []) if g and g != goal]
    if secondary_goals:
        nutrient_rules = _load_nutrient_rules()
        caution_rules  = _load_caution_rules()
        existing_en = {n["name_en"] for n in nutrients_out}
        added = 0
        for sec_goal in secondary_goals[:1]:  # 1개 2차 목표만 처리
            sec_label = sec_goal  # GOAL_LABEL은 아래에서 처리
            for rule_n in sorted(
                nutrient_rules.get(sec_goal, {}).get("nutrients", []),
                key=lambda x: x.get("priority", 99),
            ):
                if added >= 2:
                    break
                name_en = rule_n.get("name_en", "")
                if not name_en or name_en in existing_en:
                    continue
                cr = caution_rules.get(name_en, {})
                reason = (REASON_TEMPLATE.get(sec_goal, {}).get(rule_n.get("name", ""), "")
                          or rule_n.get("reason_seed", f"{rule_n.get('name', '')} 보충을 고려해 볼 수 있습니다."))
                sec_base_caution = {
                    "level":               cr.get("caution_level", "info"),
                    "items":               cr.get("short_cautions", []),
                    "interaction_flags":   cr.get("interaction_flags", []),
                    "consultation_needed": cr.get("consultation_needed", False),
                }
                sec_enriched = _inject_extra_warnings(rule_n.get("name", ""), sec_base_caution, conditions, medications)
                sec_name = rule_n.get("name", "")
                nutrients_out.append({
                    "name":         sec_name,
                    "name_en":      name_en,
                    "reason":       reason,
                    "goal_key":     sec_goal,
                    "daily_intake": _age_overrides.get(sec_name) or rule_n.get("daily_intake"),
                    "best_time":    rule_n.get("best_time"),
                    "cautions":     sec_enriched,
                })
                existing_en.add(name_en)
                added += 1

    # 음식 추천에 goal_key 부여 + 기저질환 주의 메모 적용 + 2차 목표 음식 1개 보충
    foods_raw = [{**f, "goal_key": goal} for f in health_plan.get("foods", [])]
    foods_out = _apply_condition_food_notes(foods_raw, conditions)
    if secondary_goals:
        food_rules = _load_food_rules()
        existing_food_names = {f.get("name", "") for f in foods_out}
        for sec_goal in secondary_goals[:1]:
            for rule_f in food_rules.get(sec_goal, {}).get("foods", []):
                f_name = rule_f.get("name", "")
                if f_name and f_name not in existing_food_names:
                    foods_out.append({**rule_f, "goal_key": sec_goal})
                    break  # 최대 1개

    # 습관 추천에 goal_key 부여 + 2차 목표 습관 1개 보충
    habits_out = [{**h, "goal_key": goal} for h in health_plan.get("habits", [])]
    if secondary_goals:
        habit_rules = _load_habit_rules()
        existing_habit_titles = {h.get("title", "") for h in habits_out}
        for sec_goal in secondary_goals[:1]:
            for rule_h in habit_rules.get(sec_goal, {}).get("habits", []):
                h_title = rule_h.get("title", "")
                if h_title and h_title not in existing_habit_titles:
                    habits_out.append({**rule_h, "goal_key": sec_goal})
                    break  # 최대 1개

    shopping_section: dict = {"available": False}
    if price_comparison:
        shopping_section = {
            "available": True,
            "comparisons": price_comparison.get("comparisons", []),
            "disclaimer": price_comparison.get("disclaimer", ""),
        }

    flags = risk_flags.get("flags", {})
    top_warning = None
    if flags.get("consult_required"):
        top_warning = "일부 추천 성분은 개인 건강 상태에 따라 전문가 상담이 필요할 수 있습니다."
    if age_group in ("toddler", "child") and not top_warning:
        age_label_str = "유아(3~6세)" if age_group == "toddler" else "어린이(7~12세)"
        top_warning = f"⚠️ {age_label_str} 영양제는 반드시 소아과 전문의와 상담 후 복용하세요. 성인용 제품은 절대 복용하지 마세요."

    real_meds = [m for m in medications if m and m != "없음"]
    if (conditions or real_meds) and not top_warning:
        parts = []
        if conditions:
            parts.append(f"기저질환({', '.join(conditions)})")
        if real_meds:
            parts.append(f"복용 중인 약({', '.join(real_meds)})")
        top_warning = f"{' 및 '.join(parts)}이 확인되었습니다. 영양 성분 복용 전 반드시 담당 의사 또는 약사와 상담하세요."

    AGE_LABEL    = {"toddler": "유아 (3~6세)", "child": "어린이 (7~12세)",
                    "teens": "10대", "20s": "20대", "30s": "30대", "40s": "40대",
                    "50s_plus": "50대 이상", "50s": "50대", "60s": "60대", "70s_plus": "70대 이상"}
    GENDER_LABEL = {"female": "여성", "male": "남성"}
    GOAL_LABEL   = {
        "fatigue_management": "피로 관리", "sleep_management": "수면 관리",
        "immunity_management": "면역 관리", "eye_health": "눈 건강",
        "gut_health": "장 건강", "bone_health": "뼈 건강",
        "skin_antioxidant": "피부·항산화", "weight_management": "체중 관리",
        "blood_sugar_management": "혈당 관리", "stress_management": "스트레스 관리",
        "exercise_recovery": "운동 관리", "cardiovascular_health": "심혈관 건강",
        "hair_health": "모발 건강", "liver_health": "간 건강",
    }

    # Build goal_labels list (primary goal + any secondary goals)
    all_goal_keys = [goal] + [g for g in (extra_goals or []) if g and g != goal]
    goal_labels = [GOAL_LABEL.get(g, g) for g in all_goal_keys]

    return {
        "session_id":  str(uuid.uuid4()),
        "health_goal": goal,
        "goal_label":  GOAL_LABEL.get(goal, goal),
        "goal_labels": goal_labels,
        "profile": {
            "age_group":    profile.get("age_group", ""),
            "gender":       profile.get("gender", ""),
            "age_label":    AGE_LABEL.get(profile.get("age_group", ""), ""),
            "gender_label": GENDER_LABEL.get(profile.get("gender", ""), ""),
        },
        "top_warning": top_warning,
        "recommendations": {
            "foods":     foods_out,
            "habits":    habits_out,
            "nutrients": nutrients_out,
        },
        "shopping":    shopping_section,
        "disclaimers": DISCLAIMERS,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def build_md_result(json_result: dict, health_summary_md: str) -> str:
    # health_summary_md가 이미 H1 제목을 포함하는 경우 중복 방지
    stripped = health_summary_md.strip()
    if stripped.startswith("# "):
        lines = [stripped]
    else:
        lines = ["# 나를 위한 건강 제안\n", stripped]

    if json_result.get("top_warning"):
        lines.insert(1, f"\n> ⚠️ {json_result['top_warning']}\n")

    lines.append("")

    shopping = json_result.get("shopping", {})
    if shopping.get("available"):
        lines.append("\n---\n\n## 관련 상품 가격 비교\n")
        for comp in shopping.get("comparisons", []):
            # 내부 키(iron) 대신 표시명이 있으면 우선 사용
            nutrient_label = comp.get("nutrient_display") or comp.get("nutrient", "")
            lines.append(f"### {nutrient_label}")
            if comp.get("recommended"):
                rec = comp["recommended"]
                lines.append(f"- **추천 판매처**: [{rec.get('product_name', '')}]({rec.get('url', '#')}) — {rec.get('total_price', 0):,}원 ({rec.get('recommendation_reason', '')})")
            if comp.get("lowest_price"):
                low = comp["lowest_price"]
                lines.append(f"- **최저가**: [{low.get('product_name', '')}]({low.get('url', '#')}) — {low.get('total_price', 0):,}원")
            lines.append("")
        lines.append(f"_{shopping.get('disclaimer', '')}_\n")

    # 면책 문구가 이미 포함된 경우 중복 추가 방지
    already_has_disclaimer = any(d in health_summary_md for d in DISCLAIMERS)
    if not already_has_disclaimer:
        lines.append("---")
        for d in DISCLAIMERS:
            lines.append(f"> {d}")

    return "\n".join(lines)


def main():
    health_plan = load_file(Path("output/recommendation/final_health_plan.json"), required=True)
    health_summary = load_file(Path("output/content/final_health_summary.md"), required=False)
    price_comparison = load_file(Path("output/shopping/price_comparison.json"), required=False)
    risk_flags = load_file(Path("output/risk/risk_flags.json"), required=False) or {}
    profile_raw = load_file(Path("output/intake/normalized_profile.json"), required=False) or {}

    # 다중 목표 지원: raw_minimal_input.json에서 health_goals 읽기
    raw_input = load_file(Path("output/intake/raw_minimal_input.json"), required=False) or {}
    extra_goals_korean = raw_input.get("health_goals", [])
    # 내부 코드값으로 변환 (GOAL_MAP은 normalize.py에 있으므로 인라인 처리)
    GOAL_MAP_LOCAL = {
        "피로 관리": "fatigue_management", "수면 관리": "sleep_management",
        "면역 관리": "immunity_management", "눈 건강": "eye_health",
        "장 건강": "gut_health", "뼈 건강": "bone_health",
        "피부·항산화": "skin_antioxidant", "체중 관리": "weight_management",
        "혈당 관리": "blood_sugar_management", "스트레스 관리": "stress_management",
        "운동 관리": "exercise_recovery", "심혈관 건강": "cardiovascular_health",
        "모발 건강": "hair_health", "간 건강": "liver_health",
    }
    extra_goals = [GOAL_MAP_LOCAL.get(g, g) for g in extra_goals_korean if g]

    # search_queries.json에서 nutrient_display 매핑 추출 (있을 경우)
    search_queries = load_file(Path("output/shopping/search_queries.json"), required=False)
    if search_queries and price_comparison:
        display_map = {q["nutrient"]: q.get("nutrient_display", q["nutrient"]) for q in search_queries.get("queries", [])}
        for comp in price_comparison.get("comparisons", []):
            if "nutrient_display" not in comp:
                comp["nutrient_display"] = display_map.get(comp.get("nutrient", ""), comp.get("nutrient", ""))

    json_result = build_json_result(health_plan, price_comparison, risk_flags, profile_raw, extra_goals)

    summary_md = health_summary.get("content", "") if health_summary else ""
    md_result = build_md_result(json_result, summary_md)

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(json_result, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(md_result)

    print(f"[OK] 최종 결과 생성 완료")
    print(f"     JSON: {OUTPUT_JSON}")
    print(f"     MD:   {OUTPUT_MD}")


if __name__ == "__main__":
    main()
