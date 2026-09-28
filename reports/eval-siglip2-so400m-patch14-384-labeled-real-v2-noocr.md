# Eval: google/siglip2-so400m-patch14-384 (labeled), views: full, label_mid, label_low, label weight 0.5

Index: 2082 wines; near-duplicates (cos≥0.9): 1058; twins (cos≥0.99, excluded from the main rows): 96. Embed: 2251.8 ms/img (batched).

| subset | n | Top-1 | Top-5 | Top-10 | mean margin (correct) | confident share | Top-1 when confident |
|---|---|---|---|---|---|---|---|
| all_in_catalog | 64 | 73.4% | 98.4% | 100.0% | 0.0379 | 45.3% | 0.9655 |
| all_without_twins | 61 | 72.1% | 98.4% | 100.0% | 0.0396 | 47.5% | 0.9655 |
| near_duplicates | 34 | 70.6% | 97.1% | 100.0% | 0.0261 | 38.2% | 0.9231 |
| distinct | 27 | 74.1% | 100.0% | 100.0% | 0.0557 | 59.3% | 1.0 |
| twins | 3 | 100.0% | 100.0% | 100.0% | 0.0131 | 0.0% | None |

Service answer (not_found when best visual score < 0.75):

- wines in the catalog (64): right card 68.8%, wrongly "not in catalog" 7.8%
- wines not in the catalog (33): correctly "not in catalog" 57.6%
