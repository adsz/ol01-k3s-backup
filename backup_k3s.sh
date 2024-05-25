#!/bin/bash

# Default values
VENV_NAME=""
LOCAL_BACKUP_BASE_PATH=""
AWS_PROFILE=""
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
S3_PREFIX="backup-${TIMESTAMP}"
REPO_BASE_PATH="/tmp"

# Parse command-line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --venv-name) VENV_NAME="$2"; shift ;;
        --local-backup-path) LOCAL_BACKUP_BASE_PATH="$2"; shift ;;
        --aws-profile) AWS_PROFILE="$2"; shift ;;
    esac
    shift
done

# Ensure required arguments are provided
if [ -z "$VENV_NAME" ] || [ -z "$LOCAL_BACKUP_BASE_PATH" ] || [ -z "$AWS_PROFILE" ]; then
    echo "Error: --venv-name, --local-backup-path, and --aws-profile arguments are required."
    exit 1
fi

LOCAL_BACKUP_PATH="${LOCAL_BACKUP_BASE_PATH}/${VENV_NAME}/backup-${TIMESTAMP}"
S3_BUCKET=$VENV_NAME
REPO_PATH="${REPO_BASE_PATH}/${VENV_NAME}"

# Activate the virtual environment
source "$REPO_PATH/$VENV_NAME/bin/activate"

# Call the Python backup script
python3 backup_k3s.py --local-backup-path "$LOCAL_BACKUP_PATH" --s3-bucket "$S3_BUCKET" --s3-prefix "$S3_PREFIX" --aws-profile "$AWS_PROFILE" --venv-name "$VENV_NAME"

# Deactivate the virtual environment
deactivate

