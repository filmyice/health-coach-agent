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
    "크롬":          ("chromium",    "크롬",        ["크로미움 피콜리네이트 영양제", "Chromium picolinate supplement"]),
    "홍삼":          ("red_ginseng", "홍삼",        ["홍삼 농축액 정관장", "Korean red ginseng extract"]),
    "홍삼 농축액":   ("red_ginseng", "홍삼 농축액", ["홍삼 농축액 정관장", "Korean red ginseng extract"]),
    "흑염소 진액":   ("black_goat",  "흑염소 진액", ["흑염소 진액 농축액", "Black goat extract"]),
    "녹용":          ("deer_antler", "녹용",        ["녹용 엑기스 건강식품", "Deer antler velvet extract"]),
    "프로폴리스":    ("propolis",    "프로폴리스",  ["프로폴리스 추출물 영양제", "Propolis extract supplement"]),
    "아로니아":      ("aronia",      "아로니아",    ["아로니아 원액 착즙", "Aronia berry juice"]),
    "클로렐라":      ("chlorella",   "클로렐라",    ["클로렐라 정제 영양제", "Chlorella supplement"]),
    "스피루리나":    ("spirulina",   "스피루리나",  ["스피루리나 분말 정제", "Spirulina supplement"]),
    "알로에 베라":   ("aloe_vera",   "알로에 베라", ["알로에 베라 원액 음용", "Aloe vera juice"]),
    "알로에 베라 젤":("aloe_vera",   "알로에 베라 젤",["알로에 베라 원액 음용", "Aloe vera juice"]),
    "밀크시슬":      ("milk_thistle","밀크시슬",    ["밀크시슬 실리마린 영양제", "Milk thistle silymarin"]),
    "여주 추출물":   ("bitter_melon","여주 추출물", ["여주 추출물 혈당 영양제", "Bitter melon extract"]),
    "아슈와간다":    ("ashwagandha", "아슈와간다",  ["아슈와간다 추출물 영양제", "Ashwagandha KSM-66"]),
    "빌베리 추출물": ("bilberry",    "빌베리 추출물",["빌베리 추출물 눈 영양제", "Bilberry extract supplement"]),
    "발레리안 추출물":("valerian",   "발레리안 추출물",["발레리안 수면 영양제", "Valerian root supplement"]),
    "산조인 한방차": ("sanjoin",     "산조인 한방차",["산조인차 수면 한방", "Sanjoin herbal tea"]),
    "비오틴":        ("biotin",      "비오틴",      ["비오틴 영양제",     "Biotin supplement"]),
    "비타민 B군":    ("vitamin_b",   "비타민 B군",  ["비타민B 복합 영양제", "Vitamin B complex"]),
    "비타민 A":      ("vitamin_a",   "비타민 A",    ["비타민A 영양제",    "Vitamin A supplement"]),
    "비타민 E":      ("vitamin_e",   "비타민 E",    ["비타민E 영양제",    "Vitamin E supplement"]),
    "비타민 K":      ("vitamin_k",   "비타민 K",    ["비타민K 영양제",    "Vitamin K2 supplement"]),
    "NAC":           ("nac",         "NAC",         ["NAC 아세틸시스테인", "NAC N-acetylcysteine"]),
    "밀크시슬":      ("milk_thistle","밀크시슬",    ["밀크시슬 영양제",   "Milk thistle silymarin"]),
    "알파리포산":    ("ala",         "알파리포산",  ["알파리포산 영양제", "Alpha lipoic acid supplement"]),
    "BCAA":          ("bcaa",        "BCAA",        ["BCAA 아미노산",     "BCAA branched chain amino acid"]),
    "단백질":        ("protein",     "단백질",      ["단백질 보충제 헬스", "Protein supplement whey"]),
    "L-카르니틴":    ("l_carnitine", "L-카르니틴",  ["엘카르니틴 영양제", "L-Carnitine supplement"]),
    "포스파티딜세린": ("ps",         "포스파티딜세린",["포스파티딜세린 영양제","Phosphatidylserine supplement"]),
    "GABA":          ("gaba",        "GABA",        ["가바 수면 영양제",  "GABA sleep supplement"]),
    "5-HTP":         ("5htp",        "5-HTP",       ["5HTP 영양제",       "5-HTP tryptophan supplement"]),
}

ALL_PLATFORMS = ["coupang", "naver", "iherb", "oliveyoung"]

# 연령대별 영양소 검색어 override
# 구조: age_group → { nutrient_name → [검색어, ...] }
AGE_SEARCH_OVERRIDES = {
    "toddler": {  # 유아 3~6세
        "비타민 D":      ["어린이 비타민D 400IU 영양제", "Kids Vitamin D3 400IU drops"],
        "칼슘":          ["어린이 칼슘 영양제 액상", "Kids calcium supplement chewable"],
        "철분":          ["어린이 철분 시럽 영양제", "Kids iron supplement liquid"],
        "아연":          ["어린이 아연 영양제 구미", "Kids zinc supplement gummy"],
        "비타민 C":      ["어린이 비타민C 구미 영양제", "Kids vitamin C gummy"],
        "오메가-3":      ["어린이 오메가3 DHA 영양제", "Kids omega-3 DHA fish oil"],
        "마그네슘":      ["어린이 마그네슘 영양제", "Kids magnesium supplement"],
        "프로바이오틱스":["어린이 유산균 프로바이오틱스", "Kids probiotics supplement"],
    },
    "child": {  # 어린이 7~12세
        "비타민 D":      ["어린이 비타민D 600IU 영양제", "Kids Vitamin D3 600IU supplement"],
        "칼슘":          ["어린이 성장 칼슘 영양제", "Kids calcium magnesium supplement"],
        "철분":          ["어린이 철분 영양제 구미", "Kids iron supplement chewable"],
        "오메가-3":      ["어린이 오메가3 DHA EPA 집중력", "Kids omega-3 DHA EPA brain"],
        "아연":          ["어린이 아연 면역 영양제", "Kids zinc immune supplement"],
        "비타민 C":      ["어린이 비타민C 면역 영양제", "Kids vitamin C immune supplement"],
        "마그네슘":      ["어린이 마그네슘 수면 성장", "Kids magnesium sleep growth"],
        "프로바이오틱스":["어린이 유산균 장건강 영양제", "Kids probiotics gut health"],
    },
    "teens": {  # 10대
        "칼슘":     ["청소년 성장 칼슘 영양제", "Teen calcium bone growth supplement"],
        "비타민 D": ["청소년 비타민D 1000IU", "Teen Vitamin D3 1000IU"],
        "철분":     ["청소년 철분 영양제 여성", "Teen iron supplement"],
        "오메가-3": ["청소년 오메가3 뇌 집중력", "Teen omega-3 brain focus"],
        "아연":     ["청소년 아연 여드름 면역", "Teen zinc acne immune"],
    },
    "20s": {
        "철분":     ["철분 영양제 여성 20대", "Iron supplement women"],
        "마그네슘": ["마그네슘 피로 스트레스 영양제", "Magnesium glycinate stress"],
        "오메가-3": ["오메가3 뇌 건강 영양제", "Omega-3 fish oil brain"],
    },
    "30s": {
        "코엔자임 Q10": ["코큐텐 피로 회복 100mg", "CoQ10 100mg ubiquinol fatigue"],
        "오메가-3":     ["오메가3 심혈관 뇌 영양제", "Omega-3 cardiovascular brain"],
        "비타민 B12":   ["비타민B12 메틸코발라민 영양제", "Vitamin B12 methylcobalamin"],
    },
    "40s": {
        "코엔자임 Q10": ["코큐텐 200mg 고함량 심혈관", "CoQ10 200mg ubiquinol heart"],
        "비타민 D":     ["비타민D 2000IU 고함량 영양제", "Vitamin D3 2000IU supplement"],
        "오메가-3":     ["오메가3 고함량 EPA DHA", "Omega-3 high potency EPA DHA"],
        "마그네슘":     ["마그네슘 글리시네이트 수면", "Magnesium glycinate sleep"],
    },
    "50s": {
        "칼슘":      ["50대 칼슘 비타민D 마그네슘 복합", "Calcium vitamin D magnesium complex"],
        "비타민 D":  ["비타민D3 2000IU 고함량 갱년기", "Vitamin D3 2000IU menopause"],
        "비타민 B12":["비타민B12 설하정 메틸코발라민", "Vitamin B12 sublingual methylcobalamin"],
        "오메가-3":  ["오메가3 고함량 심혈관 50대", "Omega-3 cardiovascular senior"],
        "코엔자임 Q10":["코큐텐 고함량 300mg 심장", "CoQ10 300mg heart health"],
    },
    "60s": {
        "칼슘":      ["시니어 칼슘 1200mg 비타민D", "Senior calcium 1200mg vitamin D"],
        "비타민 D":  ["고함량 비타민D 2000IU 노인", "High dose Vitamin D3 2000IU elderly"],
        "비타민 B12":["비타민B12 고함량 설하정 흡수", "Vitamin B12 sublingual high dose absorption"],
        "마그네슘":  ["시니어 마그네슘 근육 수면 노인", "Senior magnesium muscle sleep"],
        "오메가-3":  ["시니어 오메가3 심혈관 뇌 노인", "Senior omega-3 cardiovascular brain"],
        "프로바이오틱스":["시니어 유산균 노인 장건강", "Senior probiotics elderly gut"],
    },
    "70s_plus": {
        "칼슘":      ["노인 칼슘 골다공증 1200mg", "Elderly calcium osteoporosis 1200mg"],
        "비타민 D":  ["고령자 비타민D 고함량 2000IU 낙상 예방", "Elderly Vitamin D3 2000IU fall prevention"],
        "비타민 B12":["고령자 비타민B12 주사형 설하정", "Elderly Vitamin B12 sublingual injection"],
        "마그네슘":  ["고령자 마그네슘 낙상 예방 수면", "Elderly magnesium fall prevention sleep"],
        "오메가-3":  ["고령자 오메가3 치매 예방 심혈관", "Elderly omega-3 dementia prevention"],
        "비타민 C":  ["고령자 비타민C 면역 항산화", "Elderly vitamin C immune antioxidant"],
        "프로바이오틱스":["고령자 유산균 장운동 변비", "Elderly probiotics constipation"],
    },
    "50s_plus": {
        "칼슘":      ["50대 이상 칼슘 골다공증 예방", "Calcium osteoporosis prevention 50+"],
        "비타민 D":  ["50대 이상 비타민D 고함량", "Vitamin D3 high dose 50+"],
        "비타민 B12":["비타민B12 설하정 흡수 50대 이상", "Vitamin B12 sublingual 50+"],
    },
}


def load_health_plan() -> dict:
    if not HEALTH_PLAN_PATH.exists():
        print(f"[ERROR] 최종 플랜 파일 없음: {HEALTH_PLAN_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(HEALTH_PLAN_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_age_group() -> str:
    profile_path = Path("output/intake/normalized_profile.json")
    if not profile_path.exists():
        return "unknown"
    with open(profile_path, encoding="utf-8") as f:
        return json.load(f).get("age_group", "unknown")


def main():
    plan = load_health_plan()
    nutrients = plan.get("nutrients", [])
    age_group = load_age_group()
    age_overrides = AGE_SEARCH_OVERRIDES.get(age_group, {})

    if age_group != "unknown":
        print(f"[INFO] 연령대별 검색어 적용: {age_group}", file=sys.stderr)

    queries = []
    for nutrient in nutrients:
        name = nutrient.get("name", "")
        mapping = NUTRIENT_QUERY_MAP.get(name)

        if mapping:
            key, display, terms = mapping
        else:
            key     = name.lower().replace(" ", "_").replace("-", "_")
            display = name
            name_en = nutrient.get("name_en", name)
            terms   = [f"{name} 영양제", f"{name_en} supplement"]

        # 연령대별 검색어가 있으면 override
        if name in age_overrides:
            terms = age_overrides[name]

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
