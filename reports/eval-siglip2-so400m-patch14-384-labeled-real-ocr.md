# Eval: google/siglip2-so400m-patch14-384 (labeled, OCR rerank top-10 a=0.1 b=0.05), views: full, label_mid, label_low, label weight 0.5

Index: 2076 wines; near-duplicates (cos≥0.9): 1053; twins (cos≥0.99, excluded from the main rows): 93. Embed: 2251.8 ms/img (batched).

| subset | n | Top-1 | Top-5 | Top-10 | mean margin (correct) | confident share | Top-1 when confident |
|---|---|---|---|---|---|---|---|
| all_in_catalog | 64 | 84.4% | 98.4% | 98.4% | 0.0645 | 57.8% | 1.0 |
| all_without_twins | 64 | 84.4% | 98.4% | 98.4% | 0.0645 | 57.8% | 1.0 |
| near_duplicates | 36 | 86.1% | 100.0% | 100.0% | 0.0515 | 50.0% | 1.0 |
| distinct | 28 | 82.1% | 96.4% | 96.4% | 0.0821 | 67.9% | 1.0 |

Service answer (not_found when best visual score < 0.72):

- wines in the catalog (64): right card 82.8%, wrongly "not in catalog" 3.1%
- wines not in the catalog (33): correctly "not in catalog" 39.4%
