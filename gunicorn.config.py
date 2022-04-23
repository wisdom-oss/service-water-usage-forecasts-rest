import multiprocessing

bind = "0.0.0.0:5000"
workers = multiprocessing.cpu_count() * 2 + 1
limit_request_line = 0
limit_request_fields = 0
limit_request_field_size = 0
worker_class = "uvicorn.workers.UvicornWorker"
max_requests = 1
max_requests_jitter = 2
timeout = 0
