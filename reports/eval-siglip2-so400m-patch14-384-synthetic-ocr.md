# Eval: google/siglip2-so400m-patch14-384 (synthetic x2 hires, OCR rerank top-10 a=0.1 b=0.05), views: full, label_mid, label_low, label weight 0.5

Index: 1964 wines; near-duplicates (cos≥0.9): 962; twins (cos≥0.99, excluded from the main rows): 67. Embed: 98.6 ms/img (batched).

| subset | n | Top-1 | Top-5 | Top-10 | mean margin (correct) | confident share | Top-1 when confident |
|---|---|---|---|---|---|---|---|
| all_without_twins | 588 | 70.6% | 89.8% | 92.5% | 0.0624 | 49.1% | 0.9689 |
| near_duplicates | 270 | 59.3% | 89.6% | 92.6% | 0.0381 | 29.3% | 0.9747 |
| distinct | 318 | 80.2% | 89.9% | 92.5% | 0.0776 | 66.0% | 0.9667 |
| twins | 12 | 25.0% | 83.3% | 91.7% | 0.0099 | 0.0% | None |
