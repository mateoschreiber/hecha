FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml ./
COPY backend ./backend
COPY apps ./apps
COPY alembic.ini ./
RUN pip install --no-cache-dir . alembic
RUN chown -R 10001:10001 /app
USER 10001
CMD ["uvicorn", "apps.api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
