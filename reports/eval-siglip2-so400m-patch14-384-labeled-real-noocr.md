# Eval: google/siglip2-so400m-patch14-384 (labeled), views: full, label_mid, label_low, label weight 0.5

Index: 2076 wines; near-duplicates (cos≥0.9): 1053; twins (cos≥0.99, excluded from the main rows): 93. Embed: 2251.8 ms/img (batched).

| subset | n | Top-1 | Top-5 | Top-10 | mean margin (correct) | confident share | Top-1 when confident |
|---|---|---|---|---|---|---|---|
| all_in_catalog | 64 | 71.9% | 96.9% | 98.4% | 0.039 | 46.9% | 0.9667 |
| all_without_twins | 64 | 71.9% | 96.9% | 98.4% | 0.039 | 46.9% | 0.9667 |
| near_duplicates | 36 | 72.2% | 97.2% | 100.0% | 0.0262 | 38.9% | 0.9286 |
| distinct | 28 | 71.4% | 96.4% | 96.4% | 0.0557 | 57.1% | 1.0 |

Service answer (not_found when best visual score < 0.72):

- wines in the catalog (64): right card 70.3%, wrongly "not in catalog" 3.1%
- wines not in the catalog (33): correctly "not in catalog" 39.4%
