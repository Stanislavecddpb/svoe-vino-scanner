# Eval: google/siglip2-so400m-patch14-384 (labeled, OCR rerank top-10 a=0.1 b=0.05), views: full, label_mid, label_low, label weight 0.5

Index: 1964 wines; near-duplicates (cos≥0.9): 962; twins (cos≥0.99, excluded from the main rows): 67. Embed: 366.3 ms/img (batched).

| subset | n | Top-1 | Top-5 | Top-10 | mean margin (correct) | confident share | Top-1 when confident |
|---|---|---|---|---|---|---|---|
| all_without_twins | 1 | 100.0% | 100.0% | 100.0% | 0.0236 | 0.0% | None |
| near_duplicates | 1 | 100.0% | 100.0% | 100.0% | 0.0236 | 0.0% | None |

Service answer (not_found when best visual score < 0.72):

- wines in the catalog (1): right card 100.0%, wrongly "not in catalog" 0.0%
- wines not in the catalog (2): correctly "not in catalog" 100.0%
