"""
shopping-search: 최종 건강 플랜 영양 성분 → 쇼핑 검색 질의 생성
Step 14 처리 (스크립트 자동화)
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

HEALTH_PLAN_PATH = Path("output/recommendation/final_health_plan.json")
OUTPUT_PATH      = Path("output/shopping/search_queries.json")

# 성분명 → (내부 키, 한글 표시명, 한글 검색어, 영문 검색어) 매핑
NUTRIENT_QUERY_MAP = {
    "철분":          ("iron",        "철분",       ["철분 영양제",       "Iron supplement"]),
    "마그네슘":      ("magnesium",   "마그네슘",   ["마그네슘 영양제",   "Magnesium glycinate"]),
    "비타민 B12":    ("vitamin_b12", "비타민 B12", ["비타민B12 영양제",  "Vitamin B12 methylcobalamin"]),
    "비타민 D":      ("vitamin_d",   "비타민 D",   ["비타민D 보충제",    "Vitamin D3 supplement"]),
    "비타민 C":      ("vitamin_c",   "비타민 C",   ["비타민C 영양제",    "Vitamin C supplement"]),
    "아연":          ("zinc",        "아연",       ["아연 영양제",       "Zinc supplement"]),
    "코엔자임 Q10":  ("coq10",       "코엔자임 Q10",["코큐텐 영양제",    "CoQ10 ubiquinol"]),
    "칼슘":          ("calcium",     "칼슘",       ["칼슘 영양제",       "Calcium supplement"]),
    "루테인":        ("lutein",      "루테인",     ["루테인 영양제",     "Lutein zeaxanthin"]),
    "지아잔틴":      ("zeaxanthin",  "지아잔틴",   ["지아잔틴 영양제",   "Zeaxanthin supplement"]),
    "오메가-3":      ("omega3",      "오메가-3",   ["오메가3 영양제",    "Omega-3 fish oil"]),
    "프로바이오틱스": ("probiotics",  "프로바이오틱스",["프로바이오틱스",  "Probiotics supplement"]),
    "프리바이오틱스": ("prebiotics",  "프리바이오틱스",["프리바이오틱스",  "Prebiotics supplement"]),
    "식이섬유":      ("fiber",       "식이섬유",   ["식이섬유 보충제",   "Dietary fiber supplement"]),
    "멜라토닌":      ("melatonin",   "멜라토닌",   ["멜라토닌 수면",     "Melatonin sleep"]),
    "L-테아닌":      ("l_theanine",  "L-테아닌",   ["엘테아닌 영양제",   "L-Theanine supplement"]),
    "콜라겐":        ("collagen",    "콜라겐",     ["콜라겐 보충제",     "Collagen peptide"]),
    "글루타치온":    ("glutathione", "글루타치온",  ["글루타치온 영양제", "Glutathione supplement"]),
}

ALL_PLATFORMS = ["coupang", "naver", "iherb", "oliveyoung"]


def load_health_plan() -> dict:
    if not HEALTH_PLAN_PATH.exists():
        print(f"[ERROR] 최종 플랜 파일 없음: {HEALTH_PLAN_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(HEALTH_PLAN_PATH, encoding="utf-8") as f:
        return json.load(f)


def main():
    plan = load_health_plan()
    nutrients = plan.get("nutrients", [])

    queries = []
    for nutrient in nutrients:
        name = nutrient.get("name", "")
        mapping = NUTRIENT_QUERY_MAP.get(name)

        if mapping:
            key, display, terms = mapping
        else:
            # 매핑 없는 성분은 이름 그대로 사용
            key     = name.lower().replace(" ", "_").replace("-", "_")
            display = name
            name_en = nutrient.get("name_en", name)
            terms   = [f"{name} 영양제", f"{name_en} supplement"]

        queries.append({
            "nutrient":         key,
            "nutrient_display": display,
            "search_terms":     terms,
            "target_platforms": ALL_PLATFORMS,
        })

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "queries":       queries,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    names = [q["nutrient_display"] for q in queries]
    print(f"[OK] 쇼핑 검색 질의 생성 완료: {OUTPUT_PATH} ({len(queries)}개)")
    print(f"     성분: {', '.join(names)}")


if __name__ == "__main__":
    main()
