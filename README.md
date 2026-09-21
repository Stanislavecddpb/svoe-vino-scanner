# Сканер вин «Своё вино»

Фото бутылки/этикетки → поиск по каталогу «Своё вино» → slug вина, Top-5 кандидатов со скорами и карточка.
Кейс РСХБ.Цифра «Сканер российских вин с описанием на платформе „Своё вино“».

Текущий этап: **каркас backend + CV baseline** (SigLIP 2 + pgvector, без OCR и дообучения).
Устройство — в [ARCHITECTURE.md](ARCHITECTURE.md).

## Состав

| Папка | Что |
|---|---|
| `web/` | Nuxt 3 (Nitro): публичный API на :8080, демо-страница |
| `ml/` | Python: сервис эмбеддингов (FastAPI, :8001), скрипты каталога/индекса/оценки |
| `db/init.sql` | схема Postgres + pgvector |
| `eval/` | набор кейсодержателя: `participant_test.sh`, `queries.tsv`, 3 фото |
| `scripts/` | `setup.ps1`, `dev.ps1`, `prepare_data.ps1` |
| `data/` | датасет и артефакты (не в git) |
| `reports/` | отчёты оценки |

## Требования

Windows + PowerShell, Python 3.11+, Node 20+, Docker Desktop, 7-Zip (для распаковки датасета).
GPU NVIDIA желательна (SigLIP 2 so400m в fp16 занимает ~2.3 ГБ VRAM); без неё работает на CPU медленнее.
Для скрипта кейсодержателя: Git Bash + `jq` (`winget install jqlang.jq`).

## Быстрый старт

```powershell
# 1. один раз: распаковать датасет, поставить зависимости, собрать каталог и индекс
.\scripts\setup.ps1 -DatasetZip "C:\путь\Датасет.zip"     # добавьте -Cpu без NVIDIA GPU

# 2. запуск: Postgres в docker, ml и web локально
.\scripts\dev.ps1            # http://127.0.0.1:8080
.\scripts\dev.ps1 -Stub      # только API с заглушкой (без модели) — для фронтенда
```

Проверка:

```bash
curl -F image=@eval/queries/019c68d0.jpg http://127.0.0.1:8080/v1/eval/predict
curl -F image=@eval/queries/019c68d0.jpg http://127.0.0.1:8080/v1/search
curl http://127.0.0.1:8080/health
```

Весь стек в docker (индекс должен быть уже построен шагом 1):

```bash
docker compose --profile full up -d --build
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile full up -d --build   # ml на GPU
```

## API

| Метод | Путь | Ответ |
|---|---|---|
| `POST` | `/v1/eval/predict` (multipart `image`) | `{"slug": "..."}` — контракт скрипта кейсодержателя |
| `POST` | `/v1/search` (multipart `image`) | `{top1, top5: [{slug, name, winery, score}], margin, confident, engine, model, latency_ms}` |
| `GET` | `/v1/wines/:slug` | карточка: `slug, name, category, color, region, grapes, description, winery, image_url` |
| `GET` | `/v1/images/:file` | фото из каталога |
| `GET` | `/health` | `{status, engine, model, db: {wines, indexed}, ml}` |

Ошибки: `{"error": "..."}` — 400 (нет `image`, не картинка), 404, 413 (>15 МБ), 503 (ml/БД недоступны).
`score` — косинусное сходство фото с эталоном; `margin` — отрыв Top-1 от Top-2; `confident` — `margin ≥ CONFIDENCE_MARGIN`.

## Переменные окружения

| Переменная | По умолчанию | Где | Смысл |
|---|---|---|---|
| `ENGINE` | `vector` | web | `vector` — реальный поиск, `stub` — заглушка |
| `ML_URL` | `http://127.0.0.1:8001` | web | адрес ml-сервиса |
| `DATABASE_URL` | `postgresql://wine:wine@127.0.0.1:5432/wine` | web, ml | Postgres |
| `MODEL_NAME` | `google/siglip2-so400m-patch14-384` | web, ml | модель; web ищет только по векторам этой модели |
| `DEVICE` | `auto` | ml | `auto` / `cuda` / `cpu` |
| `CONFIDENCE_MARGIN` | `0.03` | web | порог отрыва для `confident` |
| `ML_TIMEOUT_MS` | `8000` | web | таймаут запроса к ml |
| `CATALOG_IMAGES_DIR` | `../data/catalog/images` | web | фото каталога |
| `HF_HUB_OFFLINE` | — | ml | `1` — не ходить в сеть за моделью (после первой загрузки) |

## Данные

`setup.ps1` → `build_catalog.py` оставляет только **однозначно сопоставленные** позиции:
из 2103 slug в CSV — 1964 в индексе; исключено 26 (одно фото на несколько slug), 67 (файл фото не найден в выгрузке Strapi),
46 (имя фото соответствует нескольким разным файлам). Список с причинами — `data/catalog/excluded.csv`.

## Оценка

```powershell
# синтетика: «полевые» копии эталонов, Top-1/Top-5, near-duplicates отдельно
ml\.venv\Scripts\python ml\scripts\evaluate.py --n-aug 2
# реальные размеченные фото (TSV: image_path<TAB>slug)
ml\.venv\Scripts\python ml\scripts\evaluate.py --labels labels.tsv --images-dir photos
# глазами: каждое фото + Top-5 эталонов (нужен запущенный сервис)
ml\.venv\Scripts\python ml\scripts\contact_sheet.py --dir eval\queries
```

Скрипт кейсодержателя (Git Bash, сервис запущен):

```bash
bash eval/participant_test.sh --images-dir eval/queries --manifest eval/queries.tsv --output reports/predictions.jsonl
```

Результаты — в `reports/`.

## Тесты

```powershell
cd ml;  .venv\Scripts\python -m pytest     # нормализация, сопоставление каталога, /embed, аугментации
cd web; npx vitest run                     # контракт API на stub-движке
```

## Ограничения

- Публичный eval-набор — 3 фото без ответов; реальная точность пока не измерима, синтетика — ориентир.
- Near-duplicates (одна этикетка, разный год/категория) визуально почти неразличимы — нужен OCR (следующий этап).
- 139 позиций каталога исключены из индекса до исправления датасета.
- Первый запуск качает модель (~4.5 ГБ) с Hugging Face.
