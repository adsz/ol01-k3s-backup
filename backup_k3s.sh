#!/bin/bash
# Default values
VENV_NAME=""
LOCAL_BACKUP_BASE_PATH=""
AWS_PROFILE=""
AWS_REGION=""
S3_BUCKET=""
S3_PREFIX=""
REPO_BASE_PATH="/tmp"

# Parse command-line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --venv-name) VENV_NAME="$2"; shift ;;
        --local-backup-path) LOCAL_BACKUP_BASE_PATH="$2"; shift ;;
        --aws-profile) AWS_PROFILE="$2"; shift ;;
        --aws-region) AWS_REGION="$2"; shift ;;
        --s3-bucket) S3_BUCKET="$2"; shift ;;
        --s3-prefix) S3_PREFIX="$2"; shift ;;
    esac
    shift
done

# Ensure required arguments are provided
if [ -z "$VENV_NAME" ] || [ -z "$LOCAL_BACKUP_BASE_PATH" ] || [ -z "$AWS_PROFILE" ] || [ -z "$AWS_REGION" ] || [ -z "$S3_BUCKET" ] || [ -z "$S3_PREFIX" ]; then
    echo "Error: --venv-name, --local-backup-path, --aws-profile, --aws-region, --s3-bucket, and --s3-prefix arguments are required."
    exit 1
fi

REPO_PATH="${REPO_BASE_PATH}/${VENV_NAME}"

# Create the backup directory
mkdir -p "$LOCAL_BACKUP_BASE_PATH"

# Activate the virtual environment
source "$REPO_PATH/$VENV_NAME/bin/activate"

# Call the Python backup script
python3 "$REPO_PATH/backup_k3s.py" --local-backup-path "$LOCAL_BACKUP_BASE_PATH" --s3-bucket "$S3_BUCKET" --s3-prefix "$S3_PREFIX" --aws-profile "$AWS_PROFILE" --aws-region "$AWS_REGION" --venv-name "$VENV_NAME"

# Deactivate the virtual environment
deactivate
