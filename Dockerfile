# FastAPI service for the BCI trial dataset.
# Build:  docker build -t bci-api .
# Run:    docker run -p 8000:8000 bci-api   then open http://localhost:8000/docs
FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir "fastapi>=0.115" "uvicorn[standard]>=0.32" "httpx>=0.27"

COPY api/ api/
COPY web/public/data/trials.json web/public/data/trials.json

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
