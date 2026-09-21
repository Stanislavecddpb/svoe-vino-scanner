# Eval: google/siglip2-so400m-patch14-384 (synthetic x2), views: full

Index: 1964 wines; near-duplicates (cos≥0.9): 962; twins (cos≥0.99, excluded from the main rows): 67. Embed: 91.6 ms/img (batched).

| subset | n | Top-1 | Top-5 | Top-10 | mean margin (correct) | confident share | Top-1 when confident |
|---|---|---|---|---|---|---|---|
| all_without_twins | 3794 | 60.4% | 80.7% | 85.3% | 0.0495 | 40.4% | 0.908 |
| near_duplicates | 1790 | 55.1% | 81.3% | 86.3% | 0.0279 | 25.5% | 0.8665 |
| distinct | 2004 | 65.2% | 80.2% | 84.3% | 0.0659 | 53.6% | 0.9256 |
| twins | 134 | 32.1% | 85.8% | 93.3% | 0.0019 | 6.0% | 0.0 |
