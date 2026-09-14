#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="jobhunter-dashboard"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
TEMPLATE="${REPO_DIR}/deploy/${SERVICE_NAME}.service"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this installer with sudo: sudo ./deploy/install-dashboard-service.sh" >&2
  exit 1
fi

RUN_USER="${SUDO_USER:-$(id -un)}"
if [[ "${RUN_USER}" == "root" ]]; then
  echo "Run this installer as the JobHunter VM user with sudo." >&2
  exit 1
fi

if [[ ! -x "${REPO_DIR}/.venv/bin/python" ]]; then
  echo "Missing ${REPO_DIR}/.venv/bin/python. Create the project virtual environment first." >&2
  exit 1
fi

if [[ ! -x "${REPO_DIR}/.venv/bin/gunicorn" ]]; then
  echo "Gunicorn is not installed in the project virtual environment." >&2
  echo "Run: ${REPO_DIR}/.venv/bin/pip install -r ${REPO_DIR}/requirements.txt" >&2
  exit 1
fi

sed \
  -e "s|__JOBHUNTER_USER__|${RUN_USER}|g" \
  -e "s|__JOBHUNTER_DIR__|${REPO_DIR}|g" \
  "${TEMPLATE}" > "${SERVICE_FILE}"

chmod 0644 "${SERVICE_FILE}"
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"
systemctl --no-pager --full status "${SERVICE_NAME}"
