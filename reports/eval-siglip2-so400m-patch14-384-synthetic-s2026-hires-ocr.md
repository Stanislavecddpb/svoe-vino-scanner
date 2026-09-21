# Eval: google/siglip2-so400m-patch14-384 (synthetic x2 hires, OCR rerank top-10 a=0.1 b=0.05), views: full, label_mid, label_low, label weight 0.5

Index: 1964 wines; near-duplicates (cos≥0.9): 962; twins (cos≥0.99, excluded from the main rows): 67. Embed: 98.8 ms/img (batched).

| subset | n | Top-1 | Top-5 | Top-10 | mean margin (correct) | confident share | Top-1 when confident |
|---|---|---|---|---|---|---|---|
| all_without_twins | 968 | 72.2% | 89.1% | 91.4% | 0.0626 | 48.1% | 0.9614 |
| near_duplicates | 450 | 64.9% | 88.0% | 90.0% | 0.0354 | 31.3% | 0.9291 |
| distinct | 518 | 78.6% | 90.1% | 92.7% | 0.082 | 62.7% | 0.9754 |
| twins | 32 | 53.1% | 93.8% | 93.8% | 0.0063 | 9.4% | 0.3333 |
