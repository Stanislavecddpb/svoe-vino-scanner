# Eval: google/siglip2-so400m-patch14-384 (synthetic x2 hires), views: full, label_mid, label_low, label weight 0.5

Index: 1964 wines; near-duplicates (cos≥0.9): 962; twins (cos≥0.99, excluded from the main rows): 67. Embed: 98.8 ms/img (batched).

| subset | n | Top-1 | Top-5 | Top-10 | mean margin (correct) | confident share | Top-1 when confident |
|---|---|---|---|---|---|---|---|
| all_without_twins | 968 | 71.9% | 88.7% | 91.4% | 0.0524 | 43.4% | 0.9667 |
| near_duplicates | 450 | 65.6% | 87.6% | 90.0% | 0.0271 | 24.7% | 0.9279 |
| distinct | 518 | 77.4% | 89.8% | 92.7% | 0.071 | 59.7% | 0.9806 |
| twins | 32 | 46.9% | 93.8% | 93.8% | 0.0035 | 0.0% | None |
