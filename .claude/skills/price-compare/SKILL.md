# 스킬: price-compare

## 역할
크롤링된 상품 정보를 정규화하고 가격을 비교하여 최저가·가성비·추천 판매처를 선정한다.

## 트리거 조건
상품 검색 결과 준비 완료 후 (Step 17)

## 처리 방식
스크립트 중심 (Python)

## 입력
- `output/shopping/normalized_products.json`

## 출력
- `output/shopping/price_comparison.json`

출력 포맷:
```json
{
  "comparisons": [
    {
      "nutrient": "철분",
      "lowest_price": {
        "product_name": "상품명",
        "platform": "coupang",
        "total_price": 12000,
        "url": "https://..."
      },
      "best_value": {
        "product_name": "상품명",
        "platform": "naver",
        "price_per_month": 9000,
        "price_per_unit": 30,
        "url": "https://..."
      },
      "recommended": {
        "product_name": "상품명",
        "platform": "coupang",
        "reason": "로켓배송, 공식 판매처, 가성비 우수",
        "url": "https://..."
      }
    }
  ],
  "disclaimer": "가격은 조회 시점 기준이며 실제 구매 시 다를 수 있습니다.",
  "compared_at": "ISO8601 timestamp"
}
```

## 스크립트
- `scripts/compare_prices.py`: 가격 정규화 + 비교 + 판매처 선정

## 비교 기준

| 항목 | 설명 |
|------|------|
| 총 판매가 | 상품 기본가 |
| 배송비 포함 실구매가 | 총 판매가 + 배송비 |
| 1개월분 기준 가격 | 용량 기준 월 비용 환산 |
| 1정·1캡슐당 가격 | 단위 비용 비교 |
| 공식몰 여부 | 신뢰도 가중치 |

## 성공 기준
- 성분별 1개 이상의 우선 판매처 결정

## 실패 처리
- 가격 비교 실패 시 상품 후보만 제공
