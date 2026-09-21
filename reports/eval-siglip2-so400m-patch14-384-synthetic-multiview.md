# Eval: google/siglip2-so400m-patch14-384 (synthetic x2), views: full, label_mid, label_low, label weight 0.5

Index: 1964 wines; near-duplicates (cos≥0.9): 962; twins (cos≥0.99, excluded from the main rows): 67. Embed: 91.6 ms/img (batched).

| subset | n | Top-1 | Top-5 | Top-10 | mean margin (correct) | confident share | Top-1 when confident |
|---|---|---|---|---|---|---|---|
| all_without_twins | 3794 | 65.2% | 85.8% | 90.2% | 0.0483 | 40.5% | 0.9597 |
| near_duplicates | 1790 | 58.5% | 86.2% | 90.7% | 0.0278 | 24.2% | 0.9353 |
| distinct | 2004 | 71.3% | 85.4% | 89.9% | 0.0634 | 55.1% | 0.9692 |
| twins | 134 | 38.1% | 92.5% | 96.3% | 0.0022 | 0.8% | 0.0 |
