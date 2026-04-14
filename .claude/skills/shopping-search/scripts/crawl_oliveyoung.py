"""
올리브영 크롤러 (Playwright 기반)
shopping-search 스킬 — Step 15
"""
import asyncio
import json
import os
import random
import sys
os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
from pathlib import Path
from datetime import datetime, timezone

from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeout

SKILL_DIR = Path(__file__).parent.parent
SELECTORS_PATH = SKILL_DIR / "references" / "selectors.json"
OUTPUT_DIR = Path("output/shopping")

PLATFORM = "oliveyoung"
BASE_URL = "https://www.oliveyoung.co.kr/store/search/getSearchMain.do?query={query}"


def load_selectors() -> dict:
    if not SELECTORS_PATH.exists():
        return {}
    with open(SELECTORS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data.get(PLATFORM, {})


async def random_delay(min_ms: int = 800, max_ms: int = 2000):
    await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000)


async def crawl_query(page: Page, query: str, selectors: dict) -> list[dict]:
    url = BASE_URL.format(query=query)
    products = []

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await random_delay(2000, 3500)

        item_selector = selectors.get("item", "li.flag-product-item")
        try:
            await page.wait_for_selector(item_selector, timeout=10000)
        except PlaywrightTimeout:
            # 대체 셀렉터 시도
            item_selector = "li[class*='product-item']"
            await page.wait_for_selector(item_selector, timeout=8000)
        items = await page.query_selector_all(item_selector)

        for item in items[:5]:
            try:
                name_el = await item.query_selector(selectors.get("name", ".prd-name"))
                price_el = await item.query_selector(selectors.get("price", ".price-2 strong"))
                link_el = await item.query_selector(selectors.get("link", "a.prd-thumb"))
                brand_el = await item.query_selector(selectors.get("brand", ".prd-brand"))

                name = await name_el.inner_text() if name_el else ""
                price_text = await price_el.inner_text() if price_el else "0"
                href = await link_el.get_attribute("href") if link_el else ""
                brand = await brand_el.inner_text() if brand_el else "올리브영"

                price = int("".join(filter(str.isdigit, price_text)) or "0")
                full_url = f"https://www.oliveyoung.co.kr{href}" if href.startswith("/") else href

                if name and price > 0:
                    products.append({
                        "product_name": name.strip(),
                        "price": price,
                        "shipping_fee": 0,
                        "total_price": price,
                        "platform": PLATFORM,
                        "seller": brand.strip(),
                        "is_official": True,
                        "url": full_url,
                        "crawled_at": datetime.now(timezone.utc).isoformat(),
                    })
            except Exception as e:
                print(f"[WARN] 상품 파싱 오류: {e}", file=sys.stderr)

    except PlaywrightTimeout:
        print(f"[WARN] 올리브영 타임아웃: {query}", file=sys.stderr)
    except Exception as e:
        print(f"[WARN] 올리브영 크롤링 오류 ({query}): {e}", file=sys.stderr)

    return products


async def crawl(queries: list[dict]) -> list[dict]:
    selectors = load_selectors()
    all_products = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1280, "height": 900},
            locale="ko-KR",
        )
        page = await context.new_page()

        for q in queries:
            nutrient = q.get("nutrient", "")
            for term in q.get("search_terms", [])[:2]:
                print(f"[올리브영] 검색 중: {term}")
                products = await crawl_query(page, term, selectors)
                for p_item in products:
                    p_item["nutrient"] = nutrient
                    p_item["search_term"] = term
                all_products.extend(products)
                await random_delay(1000, 2000)

        await browser.close()

    return all_products


def main():
    queries_path = Path("output/shopping/search_queries.json")
    if not queries_path.exists():
        print(f"[ERROR] 검색 질의 파일 없음: {queries_path}", file=sys.stderr)
        sys.exit(1)

    with open(queries_path, encoding="utf-8") as f:
        data = json.load(f)

    queries = [q for q in data.get("queries", []) if PLATFORM in q.get("target_platforms", [])]
    if not queries:
        print("[INFO] 올리브영 크롤링 대상 없음. 건너뜀.")
        sys.exit(0)

    max_retries = 2
    products = []
    for attempt in range(1, max_retries + 1):
        try:
            products = asyncio.run(crawl(queries))
            break
        except Exception as e:
            print(f"[WARN] 올리브영 크롤링 실패 (시도 {attempt}): {e}", file=sys.stderr)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "raw_oliveyoung_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"platform": PLATFORM, "products": products}, f, ensure_ascii=False, indent=2)

    print(f"[OK] 올리브영 크롤링 완료: {len(products)}개 상품")


if __name__ == "__main__":
    main()
