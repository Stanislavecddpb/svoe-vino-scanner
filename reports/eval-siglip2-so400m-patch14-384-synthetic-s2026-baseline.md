# Eval: google/siglip2-so400m-patch14-384 (synthetic x2), views: full, label weight 0.5

Index: 1964 wines; near-duplicates (cos≥0.9): 962; twins (cos≥0.99, excluded from the main rows): 67. Embed: 90.3 ms/img (batched).

| subset | n | Top-1 | Top-5 | Top-10 | mean margin (correct) | confident share | Top-1 when confident |
|---|---|---|---|---|---|---|---|
| all_without_twins | 3794 | 59.3% | 79.3% | 84.5% | 0.0494 | 39.9% | 0.9074 |
| near_duplicates | 1790 | 55.8% | 81.0% | 85.9% | 0.0288 | 25.9% | 0.8772 |
| distinct | 2004 | 62.4% | 77.8% | 83.2% | 0.0658 | 52.3% | 0.9208 |
| twins | 134 | 36.6% | 83.6% | 88.1% | 0.0017 | 6.7% | 0.0 |
