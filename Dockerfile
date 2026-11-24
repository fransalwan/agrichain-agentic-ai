# AgriChain stakeholder portal + FastAPI gateway in one container (Hugging Face Spaces, Docker SDK).
# The portal is served on 7860 (the Spaces port); the API stays internal on 127.0.0.1:8000.
FROM python:3.12-slim

# libgomp is required by LightGBM / XGBoost at runtime
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

# Spaces run containers as UID 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    LLM_EXECUTION_MODE=SIMULATED \
    API_BASE_URL=http://127.0.0.1:8000
WORKDIR /home/user/app

COPY --chown=user requirements-deploy.txt .
RUN pip install --no-cache-dir --user -r requirements-deploy.txt

COPY --chown=user . .

EXPOSE 7860
CMD ["bash", "deploy/start.sh"]
