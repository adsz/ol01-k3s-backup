#!/bin/bash

# Default values
GITHUB_REPO_URL=""
VENV_NAME=""
LOCAL_BACKUP_BASE_PATH=""
AWS_PROFILE=""
REPO_BASE_PATH="/tmp"

rm -rf $REPO_BASE_PATH/$2
# Parse command-line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --github-repo-url) GITHUB_REPO_URL="$2"; shift ;;
        --venv) VENV_NAME="$2"; shift ;;
        --local-backup-path) LOCAL_BACKUP_BASE_PATH="$2"; shift ;;
        --aws-profile) AWS_PROFILE="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

# Ensure required arguments are provided
if [ -z "$GITHUB_REPO_URL" ] || [ -z "$VENV_NAME" ] || [ -z "$LOCAL_BACKUP_BASE_PATH" ] || [ -z "$AWS_PROFILE" ]; then
    echo "Error: --github-repo-url, --venv, --local-backup-path, and --aws-profile arguments are required."
    exit 1
fi

REPO_PATH="${REPO_BASE_PATH}/${VENV_NAME}"

# Clone the repository to /tmp if it doesn't exist
if [ ! -d "$REPO_PATH" ]; then
    git clone "$GITHUB_REPO_URL" "$REPO_PATH"
else
    echo "Repository already exists at $REPO_PATH. Pulling the latest changes."
    cd "$REPO_PATH" && git pull
fi

cd "$REPO_PATH"

# Create a virtual environment if it doesn't exist
if [ ! -d "$REPO_PATH/$VENV_NAME" ]; then
    python3 -m venv "$REPO_PATH/$VENV_NAME"
fi

# Activate the virtual environment
source "$REPO_PATH/$VENV_NAME/bin/activate"

# Upgrade pip and install necessary packages
pip install --upgrade pip
pip install boto3==1.18.17 botocore==1.21.17 urllib3==1.26.5

# Call the backup script with provided arguments
"$REPO_PATH/backup_k3s.sh" --venv-name "$VENV_NAME" --local-backup-path "$LOCAL_BACKUP_BASE_PATH" --aws-profile "$AWS_PROFILE"

# Deactivate the virtual environment
deactivate

