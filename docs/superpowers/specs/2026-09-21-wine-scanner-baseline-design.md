# Сканер вин «Своё вино» — каркас backend + CV baseline

Дата: 2026-09-21. Покрывает две задачи команды: «backend / API / каркас проекта» и «распознавание вина / CV baseline».

## Цель

Рабочий сервис: фото бутылки/этикетки → `POST /v1/eval/predict` → `{"slug": "..."}`, плюс расширенная выдача Top-1/Top-5 со скорами. Структура репозитория, в которую фронтенд, CV-модуль и скрипт кейсодержателя подключаются через один интерфейс. Без OCR и дообучения.

## Исходные данные (проверено)

- `strapi_output0709.csv`: 4147 строк, 2103 уникальных slug, 2090 уникальных имён фото. Поля: Название вина, Категория, Цвет, Регион, Сорт винограда, Описание, Винодельня, Slug, Название фото.
- 13 фото привязаны к нескольким slug (спорные соответствия).
- CSV хранит исходное имя файла; в выгрузке Strapi (`uploads/`, ~6.2k оригиналов + производные `thumbnail_/small_/medium_/large_`) файлы называются `<нормализованное_имя>_<hash10>.<ext>`.
- `eval.zip`: `participant_test.sh`, `queries.tsv`, 3 фото без правильных ответов.
- Разработка: RTX 3050 Ti 4 ГБ; демо и контрольный прогон: машина с RTX 4060.

## Архитектура

```
web (Nuxt 3, Nitro server)  ──SQL──►  postgres + pgvector
   │ POST /embed
   ▼
ml (FastAPI, Python): нормализация фото + SigLIP 2 → вектор
ml/scripts: build_catalog → load_catalog → build_index → evaluate
```

### Компоненты

| Компонент | Ответственность | Интерфейс |
|---|---|---|
| `web/` Nuxt | публичный API, каталог, поиск в pgvector, (позже) UI карточки | HTTP API ниже |
| `web/server/utils/engine` | Recognition Engine: `stub` \| `vector` (env `ENGINE`) | `recognize(image: Buffer) → Candidate[]` |
| `ml/` сервис | нормализация изображения + эмбеддинг | `POST /embed` (multipart `image`) → `{model, dim, embedding: float[]}`; `GET /health` |
| `ml/wine_ml/preprocess.py` | EXIF-поворот, RGB, прозрачность → белый фон, паддинг до квадрата | общий для индексации, сервиса и оценки |
| `ml/wine_ml/embedder.py` | SigLIP 2 (по умолчанию `google/siglip2-so400m-patch14-384`, fp16 на GPU, fp32 на CPU), L2-нормированный вектор | `embed(images) → np.ndarray` |
| `ml/scripts/build_catalog.py` | CSV + uploads → `data/catalog/wines.jsonl` (однозначные) + `excluded.csv` (с причиной) | файлы |
| `ml/scripts/load_catalog.py` | upsert вин в таблицу `wines` | БД |
| `ml/scripts/build_index.py` | эмбеддинги эталонов → `wine_embeddings` | БД |
| `ml/scripts/evaluate.py` | синтетическая оценка Top-1/Top-5 | отчёт `reports/eval-*.md/json` |
| `db/init.sql` | схема | — |

### Схема БД

- `wines(slug PK, name, category, color, region, grapes, description, winery, image_file)`
- `wine_embeddings(slug FK, model, embedding vector, PK(slug, model))` — размерность не фиксируется, чтобы менять модель без миграции; ~2k строк → точный перебор, индекс не нужен.

### API (Nuxt)

- `POST /v1/eval/predict` (multipart `image`) → `200 {"slug":"..."}`. Контракт `participant_test.sh`.
- `POST /v1/search` (multipart `image`) → `{top1, top5:[{slug,name,winery,score}], margin, confident, engine, model, latency_ms}`. `score` — косинусное сходство; `margin = score1 − score2`; `confident = margin ≥ CONFIDENCE_MARGIN`.
- `GET /v1/wines/:slug` → карточка вина, 404 если нет.
- `GET /health` → статус web, БД, ml, число проиндексированных вин.
- Ошибки: нет поля `image` / пустой / не изображение → 400 с JSON `{error}`; ml недоступен → 503.

## Отбор «однозначных» позиций

Позиция включается, если: (1) её фото в CSV не принадлежит другому slug; (2) имя фото сопоставляется ровно с одним оригиналом в `uploads/` (или несколькими побайтно одинаковыми). Сопоставление: нормализация имени (lowercase, транслитерация кириллицы, не-alnum → `_`, отброс хеш-суффикса и расширения). Всё прочее — в `excluded.csv` с причиной (`shared_photo`, `file_not_found`, `ambiguous_file`, `unreadable_image`).

## Оценка

1. **Технический прогон**: `participant_test.sh` на 3 публичных фото — у каждого непустой `predicted_slug`, latency < 3 с; кандидаты проверяются глазами (контакт-лист top-5).
2. **Синтетический тест**: для каждого эталона — N искажённых копий (перспектива, поворот, кроп, блики, яркость/контраст, размытие, JPEG, фон) → Top-1/Top-5, средний margin, отдельно по «трудному» подмножеству (ближайший другой эталон с косинусом ≥ 0.9 — near-duplicates). Цифры ориентировочные, не реальная точность.
3. Если организаторы дадут размеченные фото — тот же `evaluate.py` принимает TSV `image_path<TAB>slug` и считает реальную точность.

## Критерии успеха

- `docker compose up` поднимает postgres + ml + web; альтернативно — локальный запуск по README за 2–3 команды.
- `participant_test.sh` проходит на 3 фото, latency < 3 с на 3050 Ti.
- Синтетический Top-5 ≥ 90%; Top-1 и margin записаны в отчёт, включая near-dup подмножество.
- Тесты: pytest для ml (preprocess, сопоставление каталога, `/embed`), vitest для web (контракт API на stub-движке, 400 на битых файлах).
- `ENGINE=stub` работает без ml-сервиса и без модели.
- README.md и ARCHITECTURE.md описывают запуск, env, слои, ограничения.

## Вне рамок

OCR (будет вторым этапом-переранжированием внутри Top-5), дообучение, UI карточки, «Цифровой сомелье», аналоги.
