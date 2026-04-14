"""
shopping-search: 가격 비교 결과 → 쇼핑 설명 Markdown 생성
Step 18 처리 (템플릿 기반 자동화)
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

PRICE_PATH   = Path("output/shopping/price_comparison.json")
QUERIES_PATH = Path("output/shopping/search_queries.json")
OUTPUT_PATH  = Path("output/shopping/shopping_summary.md")

PLATFORM_LABEL = {
    "coupang":    "쿠팡",
    "naver":      "네이버쇼핑",
    "iherb":      "iHerb",
    "oliveyoung": "올리브영",
}

PRODUCT_TIPS = {
    "iron":        "비스글리시네이트 형태는 일반 황산철보다 위장 자극이 적어 처음 철분제를 드시는 분께 고려해 볼 수 있습니다.",
    "magnesium":   "글리시네이트 또는 말산염(malate) 형태가 흡수율과 위장 편의성이 좋은 편입니다.",
    "vitamin_b12": "메틸코발라민(methylcobalamin) 형태가 체내 활용도가 높아 선호됩니다.",
    "vitamin_d":   "D3 형태가 D2보다 체내 유지 효과가 높습니다. 식사와 함께 복용하면 흡수가 향상됩니다.",
    "vitamin_c":   "완충형(buffered) 비타민C는 위장 자극이 적습니다.",
    "calcium":     "칼슘시트레이트는 공복에도 복용 가능하며 흡수율이 안정적입니다.",
    "zinc":        "아연글루코네이트 또는 아연피콜리네이트 형태가 흡수율이 좋습니다.",
    "lutein":      "루테인은 식사(지방)와 함께 복용 시 흡수가 향상됩니다.",
    "omega3":      "EPA+DHA 합산 함량을 확인하고, 산패 여부를 레몬향으로 확인할 수 있습니다.",
    "probiotics":  "냉장 보관 여부와 균주 종류(락토바실러스, 비피도박테리움)를 확인하세요.",
    "collagen":    "저분자 콜라겐 펩타이드가 흡수율이 높습니다.",
    "coq10":       "유비퀴놀(ubiquinol) 형태가 흡수율이 더 높습니다.",
}


def load_json(path: Path, required: bool = True) -> dict:
    if not path.exists():
        if required:
            print(f"[ERROR] 파일 없음: {path}", file=sys.stderr)
            sys.exit(1)
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_comparison_block(comp: dict, display_name: str) -> list[str]:
    lines = [f"## {display_name}\n"]

    total = comp.get("total_products", 0)
    valid = comp.get("valid_products", 0)

    if total == 0:
        lines.append("이번 조회에서 가격 정보를 수집하지 못했습니다.")
        lines.append("")
        return lines

    lines.append(f"총 {total}개 상품 조회 (유효 {valid}개)\n")

    rec = comp.get("recommended") or comp.get("lowest_price")
    low = comp.get("lowest_price")

    if rec:
        platform = PLATFORM_LABEL.get(rec.get("platform", ""), rec.get("platform", ""))
        price    = rec.get("total_price", 0)
        reason   = rec.get("recommendation_reason", "")
        url      = rec.get("url", "#")
        name     = rec.get("product_name", "")
        monthly  = rec.get("price_per_month")

        lines.append("| 구분 | 내용 |")
        lines.append("|------|------|")
        lines.append(f"| 추천 상품 | {name} |")
        lines.append(f"| 판매처 | {platform} |")
        lines.append(f"| 가격 | ₩{price:,} |")
        if monthly:
            lines.append(f"| 1개월분 | ₩{int(monthly):,} |")
        if reason:
            lines.append(f"| 추천 이유 | {reason} |")
        lines.append(f"| 구매 링크 | {url} |")
        lines.append("")

    # 최저가가 추천과 다른 경우에만 표시
    if low and rec and low.get("product_name") != rec.get("product_name"):
        low_price = low.get("total_price", 0)
        low_name  = low.get("product_name", "")
        low_url   = low.get("url", "#")
        lines.append(f"**최저가**: [{low_name}]({low_url}) — ₩{low_price:,}")
        lines.append("")

    # 제품 선택 팁
    nutrient_key = comp.get("nutrient", "")
    tip = PRODUCT_TIPS.get(nutrient_key, "")
    if tip:
        lines.append(f"> 💡 **구매 팁**: {tip}")
        lines.append("")

    return lines


def build_unavailable_section(missing_names: list) -> list[str]:
    if not missing_names:
        return []
    lines = ["\n---\n\n## 직접 검색 안내\n"]
    lines.append("아래 성분은 이번 크롤링에서 가격 정보를 수집하지 못했습니다. 직접 검색을 권장합니다.\n")
    for name in missing_names:
        lines.append(f"- **{name}**: 네이버쇼핑 또는 iHerb에서 제품명으로 검색")
    lines.append("")
    return lines


def main():
    price_data   = load_json(PRICE_PATH,   required=True)
    queries_data = load_json(QUERIES_PATH, required=False)

    # nutrient → display_name 매핑
    display_map: dict[str, str] = {}
    for q in queries_data.get("queries", []):
        display_map[q["nutrient"]] = q.get("nutrient_display", q["nutrient"])

    comparisons = price_data.get("comparisons", [])
    disclaimer  = price_data.get("disclaimer", "가격은 조회 시점 기준이며 실제 구매 시 다를 수 있습니다.")
    today       = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [
        "# 영양 성분 쇼핑 가이드\n",
        f"> ⚠️ 가격은 조회 시점({today}) 기준이며, 실제 구매 시 변동될 수 있습니다.\n",
        "---\n",
    ]

    missing = []
    for comp in comparisons:
        nutrient_key  = comp.get("nutrient", "")
        display_name  = comp.get("nutrient_display") or display_map.get(nutrient_key, nutrient_key)

        if comp.get("error") or comp.get("total_products", 0) == 0:
            missing.append(display_name)
            continue

        lines.extend(build_comparison_block(comp, display_name))
        lines.append("---\n")

    lines.extend(build_unavailable_section(missing))

    lines.append(f"\n> {disclaimer}")
    lines.append("> 이 쇼핑 정보는 참고용입니다. 구매 전 성분·용량·인증 여부를 직접 확인하세요.")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    found = sum(1 for c in comparisons if c.get("total_products", 0) > 0)
    print(f"[OK] 쇼핑 요약 생성 완료: {OUTPUT_PATH}")
    print(f"     성분 {len(comparisons)}개 중 {found}개 가격 정보 포함")


if __name__ == "__main__":
    main()
