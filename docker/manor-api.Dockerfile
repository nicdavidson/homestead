FROM python:3.12-slim

WORKDIR /app

COPY manor/api /app/api
COPY manor/api/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app/api

EXPOSE 8700
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8700"]
