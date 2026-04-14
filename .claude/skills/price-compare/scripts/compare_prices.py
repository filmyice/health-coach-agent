"""
price-compare: 정규화된 상품 정보 가격 비교 및 판매처 선정
Step 17 처리
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

INPUT_PATH = Path("output/shopping/normalized_products.json")
OUTPUT_PATH = Path("output/shopping/price_comparison.json")

DISCLAIMER = "가격은 조회 시점 기준이며 실제 구매 시 다를 수 있습니다."

# 플랫폼 신뢰도 가중치 (추천 판매처 선정 시 활용)
PLATFORM_TRUST = {
    "coupang": 1.0,
    "naver": 0.9,
    "iherb": 0.85,
    "oliveyoung": 0.9,
}


def load_products() -> dict:
    if not INPUT_PATH.exists():
        print(f"[ERROR] 정규화 상품 파일 없음: {INPUT_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(INPUT_PATH, encoding="utf-8") as f:
        return json.load(f)


def is_price_anomaly(product: dict, all_prices: list[float]) -> bool:
    """이상치 가격 판단."""
    price = product.get("total_price", 0)
    if price <= 0:
        return True
    if all_prices:
        median = sorted(all_prices)[len(all_prices) // 2]
        if median > 0 and (price > median * 5 or price < median / 5):
            return True
    return False


def select_lowest(products: list[dict]) -> dict | None:
    """최저가 상품 선정 (배송비 포함 실구매가 기준)."""
    valid = [p for p in products if p.get("total_price", 0) > 0]
    if not valid:
        return None
    return min(valid, key=lambda x: x["total_price"])


def select_best_value(products: list[dict]) -> dict | None:
    """가성비 상품 선정 (1개월분 기준 가격)."""
    valid = [p for p in products if (p.get("price_per_month") or 0) > 0]
    if not valid:
        valid = [p for p in products if (p.get("price_per_unit") or 0) > 0]
        if not valid:
            return None
        return min(valid, key=lambda x: x["price_per_unit"] or 0)
    return min(valid, key=lambda x: x["price_per_month"] or 0)


def select_recommended(products: list[dict]) -> dict | None:
    """추천 판매처 선정 (가성비 + 신뢰도 종합)."""
    valid = [p for p in products if p.get("total_price", 0) > 0]
    if not valid:
        return None

    def score(p):
        price_score = 1 / max(p.get("total_price", 1), 1)
        trust = PLATFORM_TRUST.get(p.get("platform", ""), 0.8)
        official_bonus = 0.1 if p.get("is_official", False) else 0
        return price_score * trust + official_bonus

    best = max(valid, key=score)
    reasons = []
    if best.get("is_official"):
        reasons.append("공식 판매처")
    if PLATFORM_TRUST.get(best.get("platform", ""), 0) >= 0.9:
        reasons.append("신뢰도 높은 플랫폼")
    reasons.append("가성비 우수")

    return {**best, "recommendation_reason": ", ".join(reasons)}


def compare_nutrient(nutrient: str, products: list[dict]) -> dict:
    all_prices = [p.get("total_price", 0) for p in products if p.get("total_price", 0) > 0]
    valid_products = [p for p in products if not is_price_anomaly(p, all_prices)]

    if not valid_products:
        valid_products = products

    lowest = select_lowest(valid_products)
    best_value = select_best_value(valid_products)
    recommended = select_recommended(valid_products)

    return {
        "nutrient": nutrient,
        "total_products": len(products),
        "valid_products": len(valid_products),
        "lowest_price": lowest,
        "best_value": best_value,
        "recommended": recommended,
    }


def main():
    data = load_products()
    products_by_nutrient: dict[str, list] = {}

    for product in data.get("products", []):
        nutrient = product.get("nutrient", "unknown")
        products_by_nutrient.setdefault(nutrient, []).append(product)

    comparisons = []
    for nutrient, products in products_by_nutrient.items():
        try:
            comparison = compare_nutrient(nutrient, products)
            comparisons.append(comparison)
        except Exception as e:
            print(f"[WARN] '{nutrient}' 가격 비교 실패: {e}", file=sys.stderr)
            comparisons.append({
                "nutrient": nutrient,
                "error": str(e),
                "products": products,
            })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "comparisons": comparisons,
        "disclaimer": DISCLAIMER,
        "compared_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[OK] 가격 비교 완료: {OUTPUT_PATH} ({len(comparisons)}개 성분)")


if __name__ == "__main__":
    main()
