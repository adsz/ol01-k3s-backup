#!/bin/bash

# Default values
GITHUB_REPO_URL=""
VENV_NAME=""
LOCAL_BACKUP_BASE_PATH=""
AWS_PROFILE=""
WASABI_PROFILE="wasabi"
WASABI_REGION="us-east-1"
WASABI_ENDPOINT="https://s3.eu-central-2.wasabisys.com"
REPO_BASE_PATH="/tmp"

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

# Remove the repository if it exists
if [ -d "$REPO_PATH" ]; then
    rm -rf "$REPO_PATH"
fi

# Clone the repository to /tmp
git clone "$GITHUB_REPO_URL" "$REPO_PATH"
if [ $? -ne 0 ]; then
    echo "Error: Failed to clone the repository."
    exit 1
fi

cd "$REPO_PATH"

# Ensure the backup_k3s.sh script exists
if [ ! -f "$REPO_PATH/backup_k3s.sh" ]; then
    echo "Error: backup_k3s.sh script not found in the repository."
    exit 1
fi

# Create a virtual environment if it doesn't exist
if [ ! -d "$REPO_PATH/$VENV_NAME" ]; then
    python3 -m venv "$REPO_PATH/$VENV_NAME"
fi

# Activate the virtual environment
source "$REPO_PATH/$VENV_NAME/bin/activate"

# Upgrade pip and install necessary packages
pip install --upgrade pip
pip install boto3==1.18.17 botocore==1.21.17 urllib3==1.26.5

# Ensure botocore is installed correctly
python -c "import botocore" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Error: botocore not installed correctly."
    deactivate
    exit 1
fi

# Call the backup script with provided arguments
timestamp=$(date +"%Y-%m-%d_%H-%M-%S")
"$REPO_PATH/backup_k3s.sh" --venv-name "$VENV_NAME" --local-backup-path "$LOCAL_BACKUP_BASE_PATH/backup_$timestamp" --aws-profile "$AWS_PROFILE" --s3-prefix "backup_$timestamp" --wasabi-profile "$WASABI_PROFILE" --wasabi-region "$WASABI_REGION" --wasabi-endpoint "$WASABI_ENDPOINT"
if [ $? -ne 0 ]; then
    echo "Error: backup_k3s.sh script failed."
    deactivate
    exit 1
fi

# Deactivate the virtual environment
deactivate

echo "Backup process completed successfully."

#!/bin/bash
# Default values
GITHUB_REPO_URL=""
VENV_NAME=""
LOCAL_BACKUP_BASE_PATH=""
AWS_PROFILE="aws4"
AWS_REGION="eu-central-1"
S3_BUCKET="aws4-ol01-k3s-backup"
REPO_BASE_PATH="/tmp"

# Parse command-line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --github-repo-url) GITHUB_REPO_URL="$2"; shift ;;
        --venv) VENV_NAME="$2"; shift ;;
        --local-backup-path) LOCAL_BACKUP_BASE_PATH="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

# Ensure required arguments are provided
if [ -z "$GITHUB_REPO_URL" ] || [ -z "$VENV_NAME" ] || [ -z "$LOCAL_BACKUP_BASE_PATH" ]; then
    echo "Error: --github-repo-url, --venv, and --local-backup-path arguments are required."
    exit 1
fi

REPO_PATH="${REPO_BASE_PATH}/${VENV_NAME}"

# Remove the repository if it exists
if [ -d "$REPO_PATH" ]; then
    rm -rf "$REPO_PATH"
fi

# Clone the repository to /tmp
git clone "$GITHUB_REPO_URL" "$REPO_PATH"
if [ $? -ne 0 ]; then
    echo "Error: Failed to clone the repository."
    exit 1
fi

cd "$REPO_PATH"

# Ensure the backup_k3s.sh script exists
if [ ! -f "$REPO_PATH/backup_k3s.sh" ]; then
    echo "Error: backup_k3s.sh script not found in the repository."
    exit 1
fi

# Create a virtual environment if it doesn't exist
if [ ! -d "$REPO_PATH/$VENV_NAME" ]; then
    python3 -m venv "$REPO_PATH/$VENV_NAME"
fi

# Activate the virtual environment
source "$REPO_PATH/$VENV_NAME/bin/activate"

# Upgrade pip and install necessary packages
pip install --upgrade pip
pip install boto3==1.18.17 botocore==1.21.17 urllib3==1.26.5

# Ensure botocore is installed correctly
python -c "import botocore" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Error: botocore not installed correctly."
    deactivate
    exit 1
fi

# Call the backup script with provided arguments
timestamp=$(date +"%Y-%m-%d_%H-%M-%S")
"$REPO_PATH/backup_k3s.sh" --venv-name "$VENV_NAME" --local-backup-path "$LOCAL_BACKUP_BASE_PATH/backup_$timestamp" --aws-profile "$AWS_PROFILE" --aws-region "$AWS_REGION" --s3-bucket "$S3_BUCKET" --s3-prefix "backup_$timestamp"

if [ $? -ne 0 ]; then
    echo "Error: backup_k3s.sh script failed."
    deactivate
    exit 1
fi

# Deactivate the virtual environment
deactivate

echo "Backup process completed successfully."
