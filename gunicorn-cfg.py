import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get("GUNICORN_WORKERS", "2"))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
graceful_timeout = timeout + 10
accesslog = "-"
loglevel = "info"
capture_output = True
enable_stdio_inheritance = True
