# Eval: google/siglip2-so400m-patch14-384 (labeled), views: full, label weight 0.5

Index: 2076 wines; near-duplicates (cos≥0.9): 1053; twins (cos≥0.99, excluded from the main rows): 93. Embed: 2251.8 ms/img (batched).

| subset | n | Top-1 | Top-5 | Top-10 | mean margin (correct) | confident share | Top-1 when confident |
|---|---|---|---|---|---|---|---|
| all_in_catalog | 64 | 70.3% | 93.8% | 96.9% | 0.0353 | 40.6% | 0.9231 |
| all_without_twins | 64 | 70.3% | 93.8% | 96.9% | 0.0353 | 40.6% | 0.9231 |
| near_duplicates | 36 | 75.0% | 97.2% | 100.0% | 0.0257 | 25.0% | 1.0 |
| distinct | 28 | 64.3% | 89.3% | 92.9% | 0.0498 | 60.7% | 0.8824 |

Service answer (not_found when best visual score < 0.72):

- wines in the catalog (64): right card 68.8%, wrongly "not in catalog" 3.1%
- wines not in the catalog (33): correctly "not in catalog" 27.3%
