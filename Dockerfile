# syntax=docker/dockerfile:1

FROM python:3.10

RUN <<EOF
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pre-commit
EOF
