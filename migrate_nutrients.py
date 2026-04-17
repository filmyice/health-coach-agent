"""nutrient_rules.json에 recommendation_level·food_first·supplement_tip 추가"""
import json, sys
sys.stdout.reconfigure(encoding="utf-8")

# (goal, name) → (recommendation_level, food_first_list, supplement_tip)
EXTRA = {
    ("fatigue_management", "철분"): (
        "높음",
        ["시금치", "달걀", "두부", "깻잎"],
        "공복 복용 시 속쓰림 있으면 식후 복용으로 바꾸세요",
    ),
    ("fatigue_management", "비타민 B12"): (
        "중간",
        ["달걀", "연어", "우유", "치즈"],
        "채식주의자는 반드시 보충 필요; 하루 2.4μg 이하면 충분",
    ),
    ("fatigue_management", "마그네슘"): (
        "중간",
        ["아몬드", "바나나", "현미", "시금치"],
        "취침 전 복용하면 수면·회복 두 가지 효과; 설사 시 용량 줄이기",
    ),
    ("sleep_management", "마그네슘"): (
        "높음",
        ["아몬드", "바나나", "현미"],
        "취침 30분 전 복용; 처음엔 100mg부터 시작",
    ),
    ("sleep_management", "멜라토닌"): (
        "중간",
        [],
        "0.5~1mg 소량부터 시작; 장기 복용 전 전문가 상담 권장",
    ),
    ("sleep_management", "L-테아닌"): (
        "중간",
        ["녹차", "말차"],
        "100~200mg; 졸음 유발 없이 이완 효과 — 낮에도 사용 가능",
    ),
    ("immunity_management", "비타민 C"): (
        "높음",
        ["파프리카", "키위", "브로콜리", "딸기"],
        "500~1000mg; 한 번에 많이 먹으면 흡수율 낮아지므로 분할 복용",
    ),
    ("immunity_management", "비타민 D"): (
        "높음",
        [],
        "하루 15~30분 햇볕을 먼저 시도; 부족하면 1000~2000IU 보충",
    ),
    ("immunity_management", "아연"): (
        "중간",
        ["굴", "호두", "콩", "닭고기"],
        "8~11mg; 식사와 함께 복용 — 공복 복용 시 구역감 가능",
    ),
    ("eye_health", "루테인"): (
        "높음",
        ["시금치", "케일", "브로콜리", "달걀"],
        "10~20mg; 지방과 함께 먹으면 흡수율↑ — 식사 중 복용 권장",
    ),
    ("eye_health", "지아잔틴"): (
        "중간",
        ["옥수수", "달걀 노른자", "피망"],
        "2~4mg; 루테인과 함께 복용하면 시너지 효과",
    ),
    ("eye_health", "오메가-3"): (
        "중간",
        ["연어", "고등어", "참치"],
        "식사로 주 2회 생선 섭취가 우선; 부족 시 EPA+DHA 500mg",
    ),
    ("gut_health", "프로바이오틱스"): (
        "높음",
        ["요거트", "김치", "된장", "청국장"],
        "식사로 발효식품 매일 섭취가 우선; 보충제는 공복 또는 식전 복용",
    ),
    ("gut_health", "식이섬유 (프리바이오틱스)"): (
        "높음",
        ["사과", "고구마", "귀리", "바나나"],
        "소량부터 시작해 점진적으로 늘리기; 물 충분히 마시기",
    ),
    ("bone_health", "칼슘"): (
        "높음",
        ["우유", "치즈", "멸치", "두부", "브로콜리"],
        "식사로 하루 500mg 이상 섭취 먼저 시도; 보충제는 500mg씩 나눠 복용",
    ),
    ("bone_health", "비타민 D"): (
        "높음",
        [],
        "햇볕 15~30분이 가장 자연스러운 방법; 실내생활 많으면 1000IU 보충",
    ),
    ("skin_antioxidant", "비타민 C"): (
        "높음",
        ["파프리카", "키위", "딸기", "브로콜리"],
        "500mg; 공복보다 식후 복용이 위장 자극 적음",
    ),
    ("skin_antioxidant", "콜라겐"): (
        "중간",
        ["사골국", "닭발", "생선"],
        "2.5~5g; 비타민C와 함께 복용하면 흡수 및 합성 효율 증가",
    ),
    ("weight_management", "단백질 보충제"): (
        "중간",
        ["닭가슴살", "달걀", "두부", "생선"],
        "음식 단백질로 하루 목표량을 먼저 채우고, 부족분만 보충",
    ),
    ("weight_management", "식이섬유"): (
        "높음",
        ["사과", "고구마", "귀리", "채소"],
        "소량부터 시작; 식전 복용으로 포만감 극대화, 물 충분히",
    ),
    ("weight_management", "녹차 추출물"): (
        "보통",
        ["녹차"],
        "카페인 민감자는 저카페인 제품 선택; 공복 복용 주의",
    ),
    ("blood_sugar_management", "크롬"): (
        "보통",
        ["브로콜리", "통곡물", "견과류"],
        "200~400μg; 당뇨약 복용 중이라면 반드시 전문가 상담",
    ),
    ("blood_sugar_management", "베르베린"): (
        "중간",
        [],
        "식전 500mg씩 하루 3회; 약물 상호작용 가능 — 복용 전 상담 필수",
    ),
    ("blood_sugar_management", "알파리포산"): (
        "중간",
        ["시금치", "브로콜리", "토마토"],
        "100~300mg 식전 복용; 저혈당 위험 있으므로 소량부터",
    ),
    ("stress_management", "마그네슘"): (
        "높음",
        ["아몬드", "바나나", "현미", "다크초콜릿"],
        "200~400mg 취침 전; 설사 시 글리시네이트 제형으로 교체",
    ),
    ("stress_management", "아슈와간다"): (
        "중간",
        [],
        "300~600mg 식후 복용; 임신·갑상선 질환자는 사용 전 상담",
    ),
    ("stress_management", "L-테아닌"): (
        "높음",
        ["녹차", "말차"],
        "100~200mg; 카페인과 함께 복용하면 각성·집중 효과 시너지",
    ),
    ("exercise_recovery", "단백질 보충제"): (
        "높음",
        ["닭가슴살", "달걀", "그릭 요거트"],
        "운동 후 30분 이내 섭취가 근육 합성 최적; 음식 단백질 우선",
    ),
    ("exercise_recovery", "BCAA"): (
        "보통",
        ["닭가슴살", "달걀", "유제품"],
        "5~10g 운동 전후; 단백질 섭취 충분하면 추가 BCAA 불필요",
    ),
    ("exercise_recovery", "마그네슘"): (
        "중간",
        ["아몬드", "바나나", "시금치"],
        "운동 후 또는 취침 전 200mg; 근육 경련 방지에 특히 효과적",
    ),
    ("cardiovascular_health", "오메가-3"): (
        "높음",
        ["고등어", "연어", "참치", "호두"],
        "주 2회 생선 섭취가 우선; EPA+DHA 합산 1000mg 이상 권장",
    ),
    ("cardiovascular_health", "코엔자임 Q10"): (
        "중간",
        ["소고기", "생선", "브로콜리"],
        "100~200mg 식사와 함께; 스타틴 약물 복용 중이면 상담 권장",
    ),
    ("cardiovascular_health", "마그네슘"): (
        "중간",
        ["아몬드", "현미", "시금치", "바나나"],
        "300~400mg; 혈압약 복용 중이라면 전문가와 상의",
    ),
    ("hair_health", "비오틴"): (
        "중간",
        ["달걀", "견과류", "연어"],
        "2.5~5mg; 결핍이 아니라면 효과 불확실 — 3개월 복용 후 재평가",
    ),
    ("hair_health", "철분"): (
        "높음",
        ["시금치", "달걀", "두부", "소고기"],
        "탈모와 철분 결핍이 연관된 경우 많음 — 혈액 검사 후 용량 결정 권장",
    ),
    ("hair_health", "아연"): (
        "중간",
        ["굴", "호두", "콩", "닭고기"],
        "8~11mg; 과다 복용 시 구리 결핍 유발 — 권장량 준수",
    ),
    ("liver_health", "밀크씨슬"): (
        "높음",
        [],
        "실리마린 140mg 하루 3회 식전; 알코올성 간질환에 특히 근거 충분",
    ),
    ("liver_health", "NAC"): (
        "중간",
        [],
        "600mg 하루 2회; 아세트아미노펜(타이레놀) 과다 복용 시 응급 사용 성분 — 일반 보충 목적은 소량으로",
    ),
    ("liver_health", "비타민 E"): (
        "보통",
        ["아보카도", "아몬드", "해바라기씨"],
        "400IU 이하로 유지; 고용량 장기 복용은 출혈 위험 증가",
    ),
}

def migrate():
    path = "c:/test/.claude/skills/nutrient-recommender/references/nutrient_rules.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    updated, missing = 0, []
    for goal, val in data.items():
        for n in val["nutrients"]:
            key = (goal, n["name"])
            pair = EXTRA.get(key)
            if pair:
                n["recommendation_level"] = pair[0]
                n["food_first"]           = pair[1]
                n["supplement_tip"]       = pair[2]
                updated += 1
            else:
                missing.append(f"{goal}/{n['name']}")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"완료: {updated}개 업데이트")
    if missing:
        print("미등록:", missing)

if __name__ == "__main__":
    migrate()
