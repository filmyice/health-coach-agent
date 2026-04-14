# 스킬: shopping-search

## 역할
추천 영양 성분에 대한 상품을 쿠팡·네이버 쇼핑·iHerb·올리브영에서 크롤링한다.

## 트리거 조건
최종 추천 성분 목록 확정 후 (Step 15)

## 처리 방식
Playwright 스크립트 (Python)

## 입력
- `output/shopping/search_queries.json`

입력 포맷:
```json
{
  "queries": [
    {
      "nutrient": "철분",
      "search_terms": ["철분 보충제", "iron supplement", "철분제"],
      "target_platforms": ["coupang", "naver", "iherb", "oliveyoung"]
    }
  ]
}
```

## 출력
- `output/shopping/raw_product_results.json`

## 스크립트

| 파일 | 대상 플랫폼 |
|------|-----------|
| `scripts/crawl_coupang.py` | 쿠팡 (로켓배송 우선) |
| `scripts/crawl_naver.py` | 네이버 쇼핑 |
| `scripts/crawl_iherb.py` | iHerb |
| `scripts/crawl_oliveyoung.py` | 올리브영 |
| `scripts/normalize_products.py` | 상품 정규화 (Step 16) |

## 참조 파일
- `references/selectors.json`: 플랫폼별 CSS 선택자 및 봇 대응 전략

## 크롤링 순서
1. 쿠팡 → 2. 네이버 쇼핑 → 3. iHerb → 4. 올리브영

## 크롤링 유의사항
- 쿠팡·네이버는 봇 차단 정책이 있으므로 User-Agent 설정 및 지연 처리(wait) 필수
- 각 플랫폼의 CSS 선택자와 대기 전략은 `references/selectors.json`에서 관리
- 크롤링 실패는 플랫폼 단위로 격리 처리 (전체 워크플로우 중단 금지)

## 성공 기준
- 상품명·가격·판매처·링크가 있는 상품 최소 1개 확보

## 실패 처리
| 상황 | 처리 |
|------|------|
| 플랫폼 크롤링 일시 실패 | 해당 플랫폼 재시도 1회 |
| 재시도 후 실패 | 해당 플랫폼 생략 + 로그 기록 |
| 모든 플랫폼 실패 | 쇼핑 섹션 전체 생략, 건강 추천 결과만 반환 |
