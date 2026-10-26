# ============================================================================
# Student Grade Management System
#
# Design notes you should be ready to defend in the viva:
#   - slim base image, not the full python image, to keep the layer count and
#     attack surface down
#   - requirements copied and installed BEFORE the source, so Docker reuses the
#     cached dependency layer whenever only application code changes
#   - runs as a non-root user
#   - gunicorn, not the Flask development server, which is single threaded and
#     prints a warning that it is not for production use
# ============================================================================

FROM python:3.12-slim

# Stop Python writing .pyc files and buffering stdout, so container logs appear
# in `kubectl logs` immediately rather than being held in a buffer.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /usr/src/app

# Dependency layer. Changing application code below does not invalidate this.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application layer.
COPY app/ ./app/

# Run as an unprivileged user.
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /usr/src/app
USER appuser

EXPOSE 8080

# Documents intent for anyone running the image directly with Docker.
# Kubernetes uses the probes in k8s/deployment.yaml instead of this.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health').status==200 else 1)"

# 2 workers and 4 threads is sized for the small Minikube node, not for load.
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "2", \
     "--threads", "4", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app.main:app"]
