# Eval: google/siglip2-so400m-patch14-384 (synthetic x2), views: full, label_mid, label_low, label weight 0.5

Index: 1964 wines; near-duplicates (cos≥0.9): 962; twins (cos≥0.99, excluded from the main rows): 67. Embed: 90.3 ms/img (batched).

| subset | n | Top-1 | Top-5 | Top-10 | mean margin (correct) | confident share | Top-1 when confident |
|---|---|---|---|---|---|---|---|
| all_without_twins | 3794 | 64.6% | 85.5% | 89.7% | 0.0468 | 39.0% | 0.954 |
| near_duplicates | 1790 | 59.9% | 85.5% | 89.8% | 0.0276 | 25.1% | 0.9356 |
| distinct | 2004 | 68.7% | 85.5% | 89.6% | 0.0618 | 51.3% | 0.9621 |
| twins | 134 | 38.1% | 89.5% | 94.8% | 0.0024 | 1.5% | 0.0 |
