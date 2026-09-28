# Eval: google/siglip2-so400m-patch14-384 (labeled), views: full, label weight 0.5

Index: 2082 wines; near-duplicates (cos≥0.9): 1058; twins (cos≥0.99, excluded from the main rows): 96. Embed: 2251.8 ms/img (batched).

| subset | n | Top-1 | Top-5 | Top-10 | mean margin (correct) | confident share | Top-1 when confident |
|---|---|---|---|---|---|---|---|
| all_in_catalog | 64 | 70.3% | 95.3% | 98.4% | 0.0347 | 37.5% | 0.9583 |
| all_without_twins | 61 | 70.5% | 95.1% | 98.4% | 0.0351 | 37.7% | 0.9565 |
| near_duplicates | 34 | 73.5% | 97.1% | 100.0% | 0.0246 | 20.6% | 1.0 |
| distinct | 27 | 66.7% | 92.6% | 96.3% | 0.0498 | 59.3% | 0.9375 |
| twins | 3 | 66.7% | 100.0% | 100.0% | 0.0253 | 33.3% | 1.0 |

Service answer (not_found when best visual score < 0.75):

- wines in the catalog (64): right card 67.2%, wrongly "not in catalog" 4.7%
- wines not in the catalog (33): correctly "not in catalog" 54.5%
