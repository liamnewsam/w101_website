import os

bind = "0.0.0.0:" + os.environ.get("PORT", "8080")
worker_class = "gthread"
workers = 1
threads = 100
timeout = 0
