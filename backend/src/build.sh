#!/usr/bin/env bash
python -m pip install --upgrade pip
pip install --no-cache-dir -r ./requirements.txt || {
    echo "First attempt failed, trying with --use-pep517"
    pip install --no-cache-dir --use-pep517 -r ./requirements.txt
} 