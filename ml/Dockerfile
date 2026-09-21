# ml service: image normalization + SigLIP 2 embeddings.
# Default: CUDA 12.8 wheels (works on CPU too, just larger). For a slim CPU-only image:
#   docker build --build-arg TORCH_INDEX=https://download.pytorch.org/whl/cpu ml/
FROM python:3.12-slim

ARG TORCH_INDEX=https://download.pytorch.org/whl/cu128
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HF_HOME=/hf-cache

WORKDIR /app
RUN pip install torch --index-url ${TORCH_INDEX}
COPY pyproject.toml ./
COPY wine_ml ./wine_ml
COPY scripts ./scripts
RUN pip install . pillow-heif

EXPOSE 8001
HEALTHCHECK --interval=10s --timeout=5s --start-period=600s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=4)"
CMD ["uvicorn", "wine_ml.service:app", "--host", "0.0.0.0", "--port", "8001"]
