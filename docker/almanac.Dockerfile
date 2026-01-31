FROM python:3.12-slim

WORKDIR /app

COPY packages/common /app/packages/common
COPY packages/almanac /app/packages/almanac

RUN pip install --no-cache-dir python-dotenv httpx

ENV PYTHONPATH=/app/packages/common:/app/packages/almanac

CMD ["python", "-m", "almanac.main"]
