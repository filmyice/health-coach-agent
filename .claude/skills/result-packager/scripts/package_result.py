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

NAME_EN_MAP = {
    "철분": "Iron", "비타민 B12": "Vitamin B12", "마그네슘": "Magnesium",
    "코엔자임 Q10": "CoQ10", "멜라토닌": "Melatonin", "L-테아닌": "L-Theanine",
    "비타민 C": "Vitamin C", "비타민 D": "Vitamin D", "아연": "Zinc",
    "루테인": "Lutein", "지아잔틴": "Zeaxanthin", "오메가-3": "Omega-3",
    "프로바이오틱스": "Probiotics", "프리바이오틱스": "Prebiotics",
    "식이섬유": "Dietary Fiber", "칼슘": "Calcium", "콜라겐": "Collagen",
    "글루타치온": "Glutathione",
}


def build_json_result(
    health_plan: dict,
    price_comparison: dict | None,
    risk_flags: dict,
    profile: dict,
) -> dict:
    goal = health_plan.get("health_goal", "")
    nutrients_raw = health_plan.get("nutrients", [])
    cautions_raw = health_plan.get("nutrient_cautions", [])

    caution_map = {c["nutrient_name"]: c for c in cautions_raw}

    nutrients_out = []
    for n in nutrients_raw:
        name   = n.get("name", "")
        caution = caution_map.get(name, {})
        reason = (n.get("reason") or n.get("reason_seed") or
                  REASON_TEMPLATE.get(goal, {}).get(name, f"{name} 보충을 고려해 볼 수 있습니다."))
        nutrients_out.append({
            "name":    name,
            "name_en": n.get("name_en") or NAME_EN_MAP.get(name, ""),
            "reason":  reason,
            "cautions": {
                "level":               caution.get("caution_level", "info"),
                "items":               caution.get("short_cautions", []),
                "interaction_flags":   caution.get("interaction_flags", []),
                "consultation_needed": caution.get("consultation_needed", False),
            },
        })

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

    AGE_LABEL    = {"teens": "10대", "20s": "20대", "30s": "30대", "40s": "40대", "50s_plus": "50대 이상"}
    GENDER_LABEL = {"female": "여성", "male": "남성"}
    GOAL_LABEL   = {
        "fatigue_management": "피로 관리", "sleep_management": "수면 관리",
        "immunity_management": "면역 관리", "eye_health": "눈 건강",
        "gut_health": "장 건강", "bone_health": "뼈 건강",
        "skin_antioxidant": "피부·항산화",
    }

    return {
        "session_id":  str(uuid.uuid4()),
        "health_goal": goal,
        "goal_label":  GOAL_LABEL.get(goal, goal),
        "profile": {
            "age_group":    profile.get("age_group", ""),
            "gender":       profile.get("gender", ""),
            "age_label":    AGE_LABEL.get(profile.get("age_group", ""), ""),
            "gender_label": GENDER_LABEL.get(profile.get("gender", ""), ""),
        },
        "top_warning": top_warning,
        "recommendations": {
            "foods":     health_plan.get("foods", []),
            "habits":    health_plan.get("habits", []),
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

    # search_queries.json에서 nutrient_display 매핑 추출 (있을 경우)
    search_queries = load_file(Path("output/shopping/search_queries.json"), required=False)
    if search_queries and price_comparison:
        display_map = {q["nutrient"]: q.get("nutrient_display", q["nutrient"]) for q in search_queries.get("queries", [])}
        for comp in price_comparison.get("comparisons", []):
            if "nutrient_display" not in comp:
                comp["nutrient_display"] = display_map.get(comp.get("nutrient", ""), comp.get("nutrient", ""))

    json_result = build_json_result(health_plan, price_comparison, risk_flags, profile_raw)

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
