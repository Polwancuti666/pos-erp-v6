FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir fastapi uvicorn[standard] psycopg[binary]
ENV PYTHONPATH=/app/src
EXPOSE 8000
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "pos_erp.fastapi_app:app", "--host", "0.0.0.0", "--port", "8000"]
