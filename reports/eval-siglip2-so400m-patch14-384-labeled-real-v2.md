# Eval: google/siglip2-so400m-patch14-384 (labeled, OCR rerank top-10 a=0.2 b=0.05), views: full, label_mid, label_low, label weight 0.5

Index: 2082 wines; near-duplicates (cos≥0.9): 1058; twins (cos≥0.99, excluded from the main rows): 96. Embed: 2251.8 ms/img (batched).

| subset | n | Top-1 | Top-5 | Top-10 | mean margin (correct) | confident share | Top-1 when confident |
|---|---|---|---|---|---|---|---|
| all_in_catalog | 64 | 90.6% | 100.0% | 100.0% | 0.0788 | 67.2% | 1.0 |
| all_without_twins | 61 | 90.2% | 100.0% | 100.0% | 0.0813 | 67.2% | 1.0 |
| near_duplicates | 34 | 91.2% | 100.0% | 100.0% | 0.062 | 58.8% | 1.0 |
| distinct | 27 | 88.9% | 100.0% | 100.0% | 0.1063 | 77.8% | 1.0 |
| twins | 3 | 100.0% | 100.0% | 100.0% | 0.034 | 66.7% | 1.0 |

Service answer (not_found when best visual score < 0.75):

- wines in the catalog (64): right card 84.4%, wrongly "not in catalog" 7.8%
- wines not in the catalog (33): correctly "not in catalog" 57.6%
