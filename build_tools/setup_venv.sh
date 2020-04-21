#!/bin/bash

set -e

### Set venv directory
SCRIPT_DIR="$(dirname "$(realpath "$0")")"
VENV_DIR="${SCRIPT_DIR}/../venv"

### Install dependencies
sudo apt-get install -y python3-venv

### Set up venv
python3 -m venv "${VENV_DIR}"

### Install python dependencies and package
source "${VENV_DIR}/bin/activate"
pip install -r "${SCRIPT_DIR}/requirements_build.txt"
pip install -r "${SCRIPT_DIR}/requirements_run.txt"
pip install -e "${SCRIPT_DIR}/.."

### Success!
echo "Setup successful!"
