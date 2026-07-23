# Stage G API smoke checklist (step 3)

Run with backend up on `http://127.0.0.1:8080`.

```bat
curl http://127.0.0.1:8080/api/health
curl http://127.0.0.1:8080/api/kpi
curl "http://127.0.0.1:8080/api/top-negative-products?limit=5&min_reviews=1"
curl "http://127.0.0.1:8080/api/top-negative-products?limit=2&min_reviews=1"
curl http://127.0.0.1:8080/api/aspects
curl "http://127.0.0.1:8080/api/aspects?aspect=size"
curl "http://127.0.0.1:8080/api/negative-reasons?limit=5"

:: Step 4 placeholders (expect HTTP 501)
curl http://127.0.0.1:8080/api/trend
curl http://127.0.0.1:8080/api/alerts
curl http://127.0.0.1:8080/api/samples
```

KPI expected (current smoke export):

- review_count = 50
- positive/neutral/negative counts = 44 / 6 / 0
- rates = 0.88 / 0.12 / 0.0
- average_rating = 4.46
- data_scope = phase_d_e_smoke_contract
- production_business_metrics = false (from /api/health)
