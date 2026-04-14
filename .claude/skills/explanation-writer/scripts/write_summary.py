"""
explanation-writer: 최종 건강 플랜 → 자연어 설명 Markdown 생성
Step 13 처리 (템플릿 기반 자동화)
"""
import json
import os
import sys
from urllib.parse import quote
os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
from pathlib import Path
from datetime import datetime, timezone

HEALTH_PLAN_PATH = Path("output/recommendation/final_health_plan.json")
RISK_FLAGS_PATH  = Path("output/risk/risk_flags.json")
PROFILE_PATH     = Path("output/intake/normalized_profile.json")
OUTPUT_PATH      = Path("output/content/final_health_summary.md")

GOAL_LABEL = {
    "fatigue_management":    "피로 관리",
    "sleep_management":      "수면 관리",
    "immunity_management":   "면역 관리",
    "eye_health":            "눈 건강",
    "gut_health":            "장 건강",
    "bone_health":           "뼈 건강",
    "skin_antioxidant":      "피부·항산화",
    "weight_management":     "체중 관리",
    "blood_sugar_management":"혈당 관리",
    "stress_management":     "스트레스 관리",
    "exercise_recovery":     "운동 관리",
    "cardiovascular_health": "심혈관 건강",
    "hair_health":           "모발 건강",
    "liver_health":          "간 건강",
}

AGE_LABEL = {
    "teens": "10대", "20s": "20대", "30s": "30대",
    "40s": "40대", "50s_plus": "50대 이상", "unknown": "성인",
}
GENDER_LABEL = {"female": "여성", "male": "남성", "unknown": ""}

CAUTION_ICON = {"warning": "⚠️", "consult": "🚨", "info": "ℹ️"}

# 음식 아이콘 매핑
FOOD_ICONS: dict[str, str] = {
    "블루베리": "🫐", "토마토": "🍅", "아보카도": "🥑", "연어": "🐟",
    "고등어": "🐟", "브로콜리": "🥦", "시금치": "🥬", "견과류": "🥜",
    "아몬드": "🥜", "호두": "🥜", "달걀": "🥚", "요거트": "🥛",
    "우유": "🥛", "치즈": "🧀", "귤": "🍊", "오렌지": "🍊",
    "키위": "🥝", "바나나": "🍌", "사과": "🍎", "포도": "🍇",
    "딸기": "🍓", "당근": "🥕", "고구마": "🍠", "현미": "🍚",
    "오트밀": "🌾", "두부": "🫘", "콩": "🫘", "김치": "🥗",
    "녹차": "🍵", "물": "💧", "생강": "🫚", "마늘": "🧄",
    "올리브유": "🫒", "아마씨": "🌱",
    "닭가슴살": "🍗", "귀리": "🌾", "다크초콜릿": "🍫",
    "고구마": "🍠", "고등어": "🐟", "멸치": "🐟",
    "강황": "🫚", "녹차": "🍵", "체리": "🍒",
    "두부": "🫘", "파프리카": "🫑", "마늘": "🧄",
}

# 습관 키워드 → 아이콘 (키워드 부분 일치)
HABIT_ICON_KEYWORDS: list[tuple[str, str]] = [
    ("걷기", "🚶"), ("달리기", "🏃"), ("운동", "🏋️"), ("스트레칭", "🤸"),
    ("수면", "😴"), ("취침", "🌙"), ("잠", "😴"),
    ("물", "💧"), ("수분", "💧"),
    ("자외선", "☀️"), ("선크림", "☀️"), ("자외선 차단", "☀️"),
    ("보습", "💆"), ("세안", "🧴"), ("스킨케어", "🧴"),
    ("명상", "🧘"), ("호흡", "🌬️"),
    ("식사", "🍽️"), ("채소", "🥗"), ("과일", "🍎"),
    ("금연", "🚭"), ("금주", "🚫"),
    ("햇빛", "🌞"), ("야외", "🌿"),
    ("스마트폰", "📵"), ("블루라이트", "📵"),
    ("규칙적", "⏰"), ("아침", "🌅"),
]

# 영양 성분 아이콘 매핑
NUTRIENT_ICONS: dict[str, str] = {
    "철분": "🩸", "비타민 B12": "⚡", "마그네슘": "💪", "코엔자임 Q10": "🔋",
    "멜라토닌": "🌙", "L-테아닌": "🍵", "비타민 C": "🍊", "비타민 D": "☀️",
    "아연": "🛡️", "루테인": "👁️", "지아잔틴": "👁️", "오메가-3": "🐟",
    "프로바이오틱스": "🌱", "프리바이오틱스": "🌱", "식이섬유": "🌾",
    "칼슘": "🦴", "콜라겐": "✨", "글루타치온": "💎",
    "단백질 보충제": "💪", "녹차 추출물": "🍵", "크롬": "🔬",
    "베르베린": "🌿", "알파리포산": "⚡", "아슈와간다": "🌿",
    "BCAA": "💪", "비오틴": "💇", "밀크씨슬": "🌱",
    "NAC": "🔬", "비타민 E": "🌻", "식이섬유 (프리바이오틱스)": "🌾",
}


def get_food_icon(name: str) -> str:
    return FOOD_ICONS.get(name, "🥗")


def get_habit_icon(title: str) -> str:
    for keyword, icon in HABIT_ICON_KEYWORDS:
        if keyword in title:
            return icon
    return "✅"


def get_nutrient_icon(name: str) -> str:
    return NUTRIENT_ICONS.get(name, "💊")

DISCLAIMER = (
    "> 이 내용은 의료적 진단이 아닙니다.\n"
    "> 복용 중인 약이나 임신·수유 중이라면 전문가 상담이 필요할 수 있어요."
)

# 영양소별 자연어 추천 이유 템플릿 (reason_seed 보완용)
REASON_TEMPLATE = {
    "fatigue_management": {
        "철분":     "철 결핍은 피로의 주요 원인 중 하나로, 특히 여성에게 흔합니다. 우선적으로 고려해 볼 수 있습니다.",
        "비타민 B12": "에너지 대사에 필수적인 비타민입니다. 식사가 불규칙하다면 결핍이 생기기 쉬워 고려해 볼 수 있습니다.",
        "마그네슘":  "근육 이완과 에너지 생성에 관여합니다. 수면이 부족한 경우 수면의 질 개선에도 도움이 될 수 있습니다.",
        "코엔자임 Q10": "세포 에너지 생성에 관여하여 만성 피로 개선에 도움이 될 수 있습니다.",
    },
    "sleep_management": {
        "마그네슘":  "신경 안정과 수면 유도에 도움이 될 수 있는 미네랄입니다.",
        "멜라토닌":  "수면 리듬 조절에 도움이 될 수 있습니다. 단기 사용을 권장합니다.",
        "L-테아닌": "카페인 없이 이완 효과를 줄 수 있어 취침 전 고려해 볼 수 있습니다.",
    },
    "immunity_management": {
        "비타민 C":  "항산화 작용과 면역 세포 활성화에 도움이 될 수 있습니다.",
        "비타민 D":  "면역 조절에 관여하며, 실내 생활이 많은 경우 특히 부족하기 쉽습니다.",
        "아연":     "면역 반응과 상처 회복에 관여하는 필수 미네랄입니다.",
    },
    "eye_health": {
        "루테인":   "황반 색소 밀도 유지에 도움이 될 수 있습니다. 블루라이트 차단 효과도 연구되고 있습니다.",
        "지아잔틴": "루테인과 함께 눈 건강 보호에 도움이 될 수 있습니다.",
        "오메가-3": "안구 건조 개선에 도움이 될 수 있으며, 눈 표면 건강 유지에 관여합니다.",
    },
    "gut_health": {
        "프로바이오틱스": "장내 유익균을 보충하여 소화 기능과 면역 균형에 도움이 될 수 있습니다.",
        "프리바이오틱스": "유익균의 먹이가 되어 장내 균형 유지에 도움이 될 수 있습니다.",
        "식이섬유":  "장 운동을 돕고 배변 규칙성 개선에 도움이 될 수 있습니다.",
    },
    "bone_health": {
        "칼슘":    "뼈와 치아의 주요 구성 성분입니다. 비타민 D와 함께 섭취하면 흡수가 향상됩니다.",
        "비타민 D": "칼슘 흡수를 도와 뼈 건강 유지에 중요합니다. 실외 활동이 적다면 보충을 고려할 수 있습니다.",
        "마그네슘": "뼈 기질 형성에 관여하며 칼슘과 함께 뼈 건강에 도움이 될 수 있습니다.",
    },
    "skin_antioxidant": {
        "비타민 C":  "콜라겐 합성에 필요하며 항산화 작용으로 피부 건강에 도움이 될 수 있습니다.",
        "콜라겐":   "피부 탄력과 수분 유지에 도움이 될 수 있습니다.",
        "글루타치온": "강력한 항산화 물질로 피부 미백과 산화 스트레스 감소에 도움이 될 수 있습니다.",
    },
    "weight_management": {
        "단백질 보충제": "충분한 단백질 섭취가 근육 유지와 포만감 유지에 도움이 될 수 있습니다.",
        "식이섬유":   "포만감을 높이고 혈당 안정화에 도움이 될 수 있습니다.",
        "녹차 추출물": "카테킨이 지방 산화 촉진에 도움이 될 수 있습니다.",
    },
    "blood_sugar_management": {
        "크롬":      "인슐린 기능을 보조하여 혈당 조절에 도움이 될 수 있습니다.",
        "베르베린":  "혈당과 지질 수치 개선에 도움이 될 수 있습니다.",
        "알파리포산": "인슐린 감수성 개선과 항산화 작용에 도움이 될 수 있습니다.",
    },
    "stress_management": {
        "마그네슘":   "신경계 안정과 코르티솔 조절에 도움이 될 수 있습니다.",
        "아슈와간다": "코르티솔 수치 감소와 스트레스 저항력 향상에 도움이 될 수 있습니다.",
        "L-테아닌":  "이완 효과와 집중력 유지에 도움이 될 수 있습니다.",
    },
    "exercise_recovery": {
        "단백질 보충제": "운동 후 근육 회복과 성장에 필요한 아미노산을 공급합니다.",
        "BCAA":      "근육 분해 방지와 회복에 도움이 될 수 있습니다.",
        "마그네슘":   "근육 경련 예방과 회복에 도움이 될 수 있습니다.",
    },
    "cardiovascular_health": {
        "오메가-3":     "중성지방 감소와 혈관 건강 유지에 도움이 될 수 있습니다.",
        "코엔자임 Q10": "심장 근육 에너지 생성에 관여하며 항산화 작용을 합니다.",
        "마그네슘":    "혈압 조절과 심장 리듬 유지에 도움이 될 수 있습니다.",
    },
    "hair_health": {
        "비오틴":  "케라틴 생성을 도와 모발 강도와 성장에 도움이 될 수 있습니다.",
        "철분":   "철 결핍성 탈모의 주요 원인이므로 보충이 도움이 될 수 있습니다.",
        "아연":   "모낭 세포 기능 유지와 탈모 완화에 도움이 될 수 있습니다.",
    },
    "liver_health": {
        "밀크씨슬":  "실리마린 성분이 간세포 보호와 재생에 도움이 될 수 있습니다.",
        "NAC":     "글루타치온 전구체로 간 해독과 항산화 작용에 도움이 될 수 있습니다.",
        "비타민 E":  "항산화 작용으로 간세포 산화 스트레스 감소에 도움이 될 수 있습니다.",
    },
}


def load_json(path: Path, required: bool = True) -> dict:
    if not path.exists():
        if required:
            print(f"[ERROR] 파일 없음: {path}", file=sys.stderr)
            sys.exit(1)
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_nutrient_reason(goal: str, name: str, reason_seed: str) -> str:
    template = REASON_TEMPLATE.get(goal, {}).get(name, "")
    if template:
        return template
    if reason_seed:
        # reason_seed를 자연어로 보완
        return f"{reason_seed}. 고려해 볼 수 있는 성분입니다."
    return f"{name} 보충을 고려해 볼 수 있습니다."


def build_header(profile: dict, plan: dict, risk_flags: dict) -> str:
    goal_key = plan.get("health_goal", "")
    goal_label = GOAL_LABEL.get(goal_key, goal_key)
    age = AGE_LABEL.get(profile.get("age_group", "unknown"), "")
    gender = GENDER_LABEL.get(profile.get("gender", "unknown"), "")
    subject = f"{age} {gender}".strip()

    lines = [f"# 나를 위한 건강 제안\n"]
    if subject:
        lines.append(f"> **대상**: {subject} | **목표**: {goal_label}")

    # 위험 플래그 상단 경고
    flags = risk_flags.get("flags", {})
    if flags.get("consult_required"):
        lines.append("> ⚠️ 일부 추천 성분은 개인 건강 상태에 따라 **전문가 상담이 필요**할 수 있습니다.")

    return "\n".join(lines)


def build_foods_section(foods: list) -> str:
    if not foods:
        return ""
    lines = ["\n---\n\n## 🥗 추천 음식\n"]
    for food in foods:
        name = food.get("name", "")
        icon = get_food_icon(name)
        lines.append(f"### {icon} {name}")
        lines.append(food.get("reason", ""))
        suggestion = food.get("serving_suggestion", "")
        if suggestion:
            lines.append(f"- **섭취 방법**: {suggestion}")
        lines.append("")
    return "\n".join(lines)


def build_habits_section(habits: list) -> str:
    if not habits:
        return ""
    lines = ["\n---\n\n## 🏃 생활습관 제안\n"]
    for habit in habits:
        title   = habit.get("title", "")
        diff    = habit.get("difficulty", "")
        freq    = habit.get("frequency", "")
        meta    = f" *({diff} / {freq})*" if diff or freq else ""
        icon    = get_habit_icon(title)
        lines.append(f"### {icon} {title}{meta}")
        lines.append(habit.get("description", ""))
        lines.append("")
    return "\n".join(lines)


def build_nutrients_section(nutrients: list, goal: str) -> str:
    if not nutrients:
        return ""
    lines = ["\n---\n\n## 💊 영양 성분 제안\n"]

    priority_groups: dict[int, list] = {}
    for n in nutrients:
        p = n.get("priority", 99)
        priority_groups.setdefault(p, []).append(n)

    rank = 1
    for p in sorted(priority_groups):
        group = priority_groups[p]
        for n in group:
            name    = n.get("name", "")
            name_en = n.get("name_en", "")
            title   = f"{name} ({name_en})" if name_en else name
            n_icon  = get_nutrient_icon(name)

            rank_label = f"{'①②③④⑤'[rank-1] if rank <= 5 else str(rank)}"
            lines.append(f"### {n_icon} {rank_label} {title}")

            reason = get_nutrient_reason(goal, name, n.get("reason_seed", ""))
            lines.append(f"**추천 이유**: {reason}")
            lines.append("")

            # 주의사항 (caution 내장 또는 caution_seed)
            caution = n.get("caution", {})
            caution_items = caution.get("short_cautions", n.get("caution_seed", []))
            interactions  = caution.get("interaction_flags", [])
            level         = caution.get("caution_level", "info")
            icon          = CAUTION_ICON.get(level, "ℹ️")

            if caution_items:
                lines.append(f"> {icon} **주의사항**")
                for item in caution_items:
                    lines.append(f"> - {item}")
                if interactions:
                    lines.append(">")
                    lines.append(f"> *상호작용*: {' / '.join(interactions)}")
                lines.append("")

            lines.append("---\n")

        rank += len(group)

    return "\n".join(lines)


def build_shopping_links_section(nutrients: list) -> str:
    if not nutrients:
        return ""
    lines = ["\n---\n\n## 🛒 영양 성분 검색\n"]
    lines.append("추천 성분을 직접 검색해보세요.\n")
    lines.append("| 성분 | 네이버 쇼핑 | 쿠팡 | iHerb |")
    lines.append("|------|------------|------|-------|")
    for n in nutrients:
        name    = n.get("name", "")
        name_en = n.get("name_en", "")
        q_ko = quote(name, safe="")
        q_en = quote(name_en or name, safe="")
        naver  = f"[검색](https://search.shopping.naver.com/search/all?query={q_ko})"
        coupang = f"[검색](https://www.coupang.com/np/search?q={q_ko})"
        iherb  = f"[검색](https://www.iherb.com/search?kw={q_en})" if name_en else "-"
        lines.append(f"| **{name}** | {naver} | {coupang} | {iherb} |")
    return "\n".join(lines)


def main():
    plan       = load_json(HEALTH_PLAN_PATH, required=True)
    risk_flags = load_json(RISK_FLAGS_PATH,  required=False)
    profile    = load_json(PROFILE_PATH,     required=False)

    goal = plan.get("health_goal", "")

    header   = build_header(profile, plan, risk_flags)
    foods    = build_foods_section(plan.get("foods", []))
    habits   = build_habits_section(plan.get("habits", []))
    nutrients_list = plan.get("nutrients", [])
    nutrients = build_nutrients_section(nutrients_list, goal)
    shopping_links = build_shopping_links_section(nutrients_list)

    md = "\n".join(filter(None, [header, foods, habits, nutrients, shopping_links]))
    md += f"\n\n{DISCLAIMER}\n"

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(md)

    food_count    = len(plan.get("foods", []))
    habit_count   = len(plan.get("habits", []))
    nutrient_count = len(plan.get("nutrients", []))
    print(f"[OK] 건강 요약 생성 완료: {OUTPUT_PATH}")
    print(f"     음식 {food_count}개 | 습관 {habit_count}개 | 영양성분 {nutrient_count}개")


if __name__ == "__main__":
    main()
