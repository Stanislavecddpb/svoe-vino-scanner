# Eval: google/siglip2-so400m-patch14-384 (synthetic x2)

Index: 1964 wines, near-duplicate refs (cos≥0.9): 962. Embed: 91.3 ms/img (batched).

| subset | n | Top-1 | Top-5 | mean margin (correct) | confident share | Top-1 when confident |
|---|---|---|---|---|---|---|
| all | 3928 | 59.5% | 80.9% | 0.0487 | 39.2% | 0.9032 |
| near_duplicates | 1924 | 53.5% | 81.6% | 0.0268 | 24.2% | 0.8516 |
| distinct | 2004 | 65.2% | 80.2% | 0.0659 | 53.6% | 0.9256 |
