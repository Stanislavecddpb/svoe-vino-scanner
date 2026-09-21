# Реальный тестовый набор: как снять и разметить

Синтетика — только ориентир (особенно для OCR). Честная точность и настройка порогов — по реальным фото.
Цель: **100–200 фото** (~60–120 вин из чек-листа, 2–3 фото на вино) + **10–20 фото вин, которых нет в каталоге**.

## 1. Чек-лист

```powershell
ml\.venv\Scripts\python ml\scripts\photo_checklist.py
```

`data/photo_kit/checklist.html` — открыть на телефоне в магазине (самодостаточный файл, можно переслать в мессенджер):
120 вин 20 крупнейших виноделен, с фото бутылки. «Серия N» — пары почти одинаковых этикеток
(брют / полусладкое, белое / розовое, с годом / без) — **снимайте обе бутылки пары**, это самые важные фото.
Галочка «снято» запоминается в браузере. То же списком — `data/photo_kit/checklist.csv`.

## 2. Как снимать

Как обычный покупатель, телефоном, без вспышки:
1. крупный план этикетки, прямо;
2. под углом ~30° или с бликом;
3. бутылка на полке вместе с соседями.

Не кадрировать и не обрабатывать. Любой формат (JPG, HEIC, WEBP), имя файла любое.

## 3. Разметка

Фото сложить в `eval/real/photos/` (в git не попадают), таблицу — `eval/real/labels.tsv` (табуляция между колонками):

```
image_path	slug
IMG_0412.jpg	fanagoriya-brule-muscat-ottonel-brut-muskat-ottonel-beloe-polusladkoe-12
IMG_0413.jpg	fanagoriya-brule-muscat-ottonel-brut-muskat-ottonel-beloe-polusladkoe-12
IMG_0420.jpg	-
```

`slug` — из чек-листа (серый текст под названием); `-` — вина нет в каталоге.
Шаблон: `labels_template.tsv`. Пример на трёх публичных фото: `labels_public.tsv`.

## 4. Оценка

```powershell
ml\.venv\Scripts\python ml\scripts\evaluate.py --labels eval\real\labels.tsv --images-dir eval\real\photos --ocr --tag real
ml\.venv\Scripts\python ml\scripts\evaluate.py --labels eval\real\labels.tsv --images-dir eval\real\photos --tag real-noocr
```

Отчёт `reports/eval-…-labeled-real.md`: Top-1 / Top-5, отдельно серии этикеток (near-duplicates), и **ответ сервиса** —
доля верных карточек, ложных «нет в каталоге», и доля верных «нет в каталоге» для вин вне каталога.

Дальше по этому набору калибруются `OCR_ALPHA`, `LABEL_WEIGHT`, `CONFIDENCE_MARGIN`, `NOT_FOUND_SCORE`
(`evaluate.py ... --ocr --sweep` работает и для реальных фото). Чтобы не подогнать пороги под один набор,
половину фото оставить для контрольной проверки.
