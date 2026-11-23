#!/bin/sh
# Start the attendance server (Linux / Mac).  Many CPU cores:  gunicorn -c gunicorn.conf.py app:app
cd "$(dirname "$0")"
python3 serve.py
