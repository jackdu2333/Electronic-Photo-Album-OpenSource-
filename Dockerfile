# 多阶段构建 - 生产镜像
FROM python:3.11-slim as builder

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─────────────────────────────────────────────────────────────
# 生产镜像
FROM python:3.11-slim as production

# 设置工作目录
WORKDIR /app

# 从 builder 阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 创建非 root 用户运行应用
RUN useradd --create-home --shell /bin/bash appuser

# 复制应用代码
COPY --chown=appuser:appuser . .

# 创建必要的目录并设置权限
RUN mkdir -p /app/static/photos /app/logs && \
    chown -R appuser:appuser /app/static/photos /app/logs

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 5000

# Gunicorn 配置（通过环境变量覆盖，适配不同规格部署环境）
# 2核2G 推荐：workers=3, threads=4, worker_class=gthread
ENV GUNICORN_WORKERS=3
ENV GUNICORN_THREADS=4
ENV GUNICORN_TIMEOUT=120
ENV GUNICORN_WORKER_CLASS=gthread
ENV GUNICORN_BIND=0.0.0.0:5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/')" || exit 1

# 使用 gunicorn 运行
CMD ["sh", "-c", "gunicorn --bind ${GUNICORN_BIND} --workers ${GUNICORN_WORKERS} --threads ${GUNICORN_THREADS} --worker-class ${GUNICORN_WORKER_CLASS} --timeout ${GUNICORN_TIMEOUT} app:app"]
