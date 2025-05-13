#!/bin/bash

# Start the server using Gunicorn with gevent workers for high concurrency
exec gunicorn --worker-class gevent --workers=3 --bind 0.0.0.0:5000 --log-level=info --reuse-port --reload main:app