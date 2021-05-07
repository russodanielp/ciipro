#!/bin/sh

# will start the conda environment
# and use gunicorn to serve CIIPro

conda run -n ciipro-bare exec gunicorn --bind :80 \
       --workers 1 --threads 8 --timeout 0 --access-logfile logs/access.log --error-logfile logs/error.log routes:app