"""
상품 정보 정규화 (Step 16)
4개 플랫폼 raw 결과를 통합하고 비교 가능한 구조로 변환
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

OUTPUT_DIR = Path("output/shopping")
RAW_FILES = [
    OUTPUT_DIR / "raw_coupang_results.json",
    OUTPUT_DIR / "raw_naver_results.json",
    OUTPUT_DIR / "raw_iherb_results.json",
    OUTPUT_DIR / "raw_oliveyoung_results.json",
]
OUTPUT_PATH = OUTPUT_DIR / "normalized_products.json"

REQUIRED_FIELDS = ["product_name", "price", "total_price", "platform", "url"]


def normalize_product(raw: dict) -> dict | None:
    """필수 필드 확인 및 정규화."""
    for field in REQUIRED_FIELDS:
        if not raw.get(field):
            return None

    # 용량 정보 파싱 (상품명에서 추출 시도)
    name = raw.get("product_name", "")
    unit_count = extract_unit_count(name)

    price = raw.get("price", 0)
    shipping = raw.get("shipping_fee", 0)
    total = price + shipping

    price_per_unit = round(total / unit_count, 1) if unit_count > 0 else None
    monthly_supply = unit_count if unit_count > 0 else None
    price_per_month = total if monthly_supply else None

    return {
        "product_name": name,
        "nutrient": raw.get("nutrient", "unknown"),
        "price": price,
        "shipping_fee": shipping,
        "total_price": total,
        "price_per_unit": price_per_unit,
        "unit_type": "정",
        "monthly_supply": monthly_supply,
        "price_per_month": price_per_month,
        "platform": raw.get("platform", ""),
        "seller": raw.get("seller", ""),
        "is_official": raw.get("is_official", False),
        "url": raw.get("url", ""),
        "crawled_at": raw.get("crawled_at", ""),
    }


def extract_unit_count(name: str) -> int:
    """상품명에서 수량 추출 (예: '60정', '90캡슐')."""
    import re
    patterns = [r"(\d+)\s*정", r"(\d+)\s*캡슐", r"(\d+)\s*캡", r"(\d+)\s*개"]
    for pattern in patterns:
        match = re.search(pattern, name)
        if match:
            return int(match.group(1))
    return 0


def main():
    all_products = []
    loaded_platforms = []

    for raw_file in RAW_FILES:
        if not raw_file.exists():
            print(f"[INFO] 크롤링 결과 없음 (건너뜀): {raw_file}", file=sys.stderr)
            continue

        with open(raw_file, encoding="utf-8") as f:
            data = json.load(f)

        platform = data.get("platform", "unknown")
        raw_products = data.get("products", [])
        normalized = 0

        for raw in raw_products:
            product = normalize_product(raw)
            if product:
                all_products.append(product)
                normalized += 1

        loaded_platforms.append(platform)
        print(f"[OK] {platform}: {normalized}/{len(raw_products)}개 정규화")

    if not all_products:
        print("[WARN] 정규화된 상품 없음. 쇼핑 섹션 생략 예정.", file=sys.stderr)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result = {
        "products": all_products,
        "platforms_loaded": loaded_platforms,
        "total_count": len(all_products),
        "normalized_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[OK] 상품 정규화 완료: {OUTPUT_PATH} (총 {len(all_products)}개)")


if __name__ == "__main__":
    main()
