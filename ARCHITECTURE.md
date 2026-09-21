# Архитектура

## Поток запроса

```
фото (multipart "image")
   │
   ▼
web — Nuxt 3 / Nitro, :8080 ─────────────────────────────────────────────┐
   │ 1. приём и валидация (readImage: multipart, magic bytes, ≤15 МБ)     │
   │ 2. RecognitionEngine.recognize(image, k=5)   ← ENGINE=vector|stub     │
   │ 3. ответ: /v1/eval/predict → {"slug"} ; /v1/search → top1/top5/margin │
   └──────────┬───────────────────────────────────────────────┬──────────┘
              │ POST /embed (VectorEngine)                     │ SQL
              ▼                                                ▼
ml — FastAPI, :8001                                  Postgres 16 + pgvector
   нормализация фото → SigLIP 2 → L2-вектор          wines, wine_embeddings
```

## Слои

| Слой | Где | Что делает |
|---|---|---|
| Нормализация фото | `ml/wine_ml/preprocess.py` | EXIF-поворот → RGB, прозрачность → белый → обрезка белых полей → уменьшение до 1024 → паддинг до квадрата. Одна функция для эталонов, запросов и оценки, чтобы векторы были сопоставимы. |
| Извлечение признаков | `ml/wine_ml/embedder.py` | SigLIP 2 (`google/siglip2-so400m-patch14-384`, 1152-d), fp16 на GPU, L2-нормировка. |
| Поиск по каталогу | `web/server/utils/engine/vector.ts` | косинусное расстояние `<=>` в pgvector, точный перебор (≈2k векторов, <5 мс), Top-5. |
| Выдача карточки | `web/server/routes/v1/wines/[slug].get.ts`, `/v1/images/:file` | карточка вина из таблицы `wines` + фото каталога. |
| Уверенность | `web/server/utils/search.ts` | `score` = косинусное сходство; `margin` = score₁ − score₂; `confident` = margin ≥ `CONFIDENCE_MARGIN`. |
| Доп. функционал | — | следующий этап (сомелье, аналоги) — строится поверх `/v1/search` и `/v1/wines`. |

## Recognition Engine — точка подключения CV

```ts
interface RecognitionEngine {
  name: string; model: string | null
  recognize(image: UploadedImage, k: number): Promise<Candidate[]>  // sorted by score desc
}
```

- `StubEngine` — детерминированная заглушка (хеш картинки → реальные slug каталога). Не требует ml и БД; для фронтенда и тестов.
- `VectorEngine` — ml `/embed` + pgvector.
- Новый движок (например, с OCR-переранжированием) = новый класс + строка в `getEngine()`. API и фронтенд не меняются.

Контракт ml-сервиса: `POST /embed` (multipart `image`) → `{model, dim, embedding[], embed_ms}`; `GET /health`.
Web проверяет, что `model` ответа совпадает с `MODEL_NAME` индекса, — иначе 503 (защита от смешения векторов разных моделей).

## Данные и офлайн-конвейер

```
data/raw/strapi_output0709.csv + data/raw/strapi/.../uploads
   │ ml/scripts/build_catalog.py      однозначные позиции → data/catalog/{wines.jsonl, excluded.csv, images/}
   │ ml/scripts/load_catalog.py       → таблица wines
   │ ml/scripts/build_index.py        → таблица wine_embeddings (slug, model, vector)
   └ ml/scripts/evaluate.py           → reports/eval-*.md|json
```

**Однозначная позиция**: фото в CSV принадлежит ровно одному slug И имя фото сопоставляется ровно с одним файлом в uploads (или несколькими побайтно одинаковыми). Сопоставление: у файла Strapi отрезается `_<hash10>`, обе стороны приводятся к ключу (lowercase, транслитерация кириллицы, только `[a-z0-9]`). Исключённые позиции с причиной — в `data/catalog/excluded.csv` (`shared_photo`, `file_not_found`, `ambiguous_file`, `unreadable_image`).

`wine_embeddings` хранит модель в ключе — можно держать индексы нескольких моделей и переключаться `MODEL_NAME` без миграции.

## Оценка

- **Синтетическая** (`evaluate.py`): из каждого эталона генерируются «полевые» фото (`augment.py`: крупный план этикетки или бутылка целиком, перспектива, наклон, фон, свет, блик, размытие, JPEG). Метрики Top-1/Top-5, margin, доля «уверенных» ответов и их точность — отдельно для near-duplicates (эталоны, у которых ближайший другой эталон с косинусом ≥ 0.9). Это ориентир, не реальная точность.
- **Реальная**: `evaluate.py --labels file.tsv --images-dir DIR`, как только появятся размеченные фото.
- **Контракт кейсодержателя**: `eval/participant_test.sh` против запущенного сервиса.

## Куда расти

1. OCR-переранжирование внутри Top-5 (год, «брют/сухое», название) — главный инструмент против near-duplicates.
2. Несколько векторов на вино (бутылка целиком + зона этикетки) — снижает разрыв «крупный план vs студийное фото».
3. Дообучение SigLIP 2 (контрастивно, на синтетике/полевых фото) на 4060.
