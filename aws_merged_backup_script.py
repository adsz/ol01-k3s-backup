#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import boto3
from botocore.exceptions import ClientError
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Backup K3s cluster and upload to AWS S3")
    parser.add_argument("--github-repo-url", required=True, help="GitHub repository URL")
    parser.add_argument("--venv", required=True, help="Virtual environment name")
    parser.add_argument("--local-backup-path", required=True, help="Local backup path")
    parser.add_argument("--aws-profile", required=True, help="AWS profile name")
    parser.add_argument("--aws-region", required=True, help="AWS region")
    parser.add_argument("--s3-bucket", required=True, help="S3 bucket name")
    parser.add_argument("--repo-base-path", required=True, help="Base path for the repository")
    return parser.parse_args()

def clone_repo(repo_url, repo_path):
    logger.info(f"Cloning repository from {repo_url} to {repo_path}")
    if os.path.exists(repo_path):
        subprocess.run(["rm", "-rf", repo_path], check=True)
    subprocess.run(["git", "clone", repo_url, repo_path], check=True)

def setup_venv(venv_path):
    logger.info(f"Setting up virtual environment at {venv_path}")
    if not os.path.exists(venv_path):
        subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)
    
    # Use the activated Python to install packages
    pip_path = os.path.join(venv_path, "bin", "pip")
    subprocess.run([pip_path, "install", "--upgrade", "pip"], check=True)
    subprocess.run([pip_path, "install", "boto3==1.18.17", "botocore==1.21.17", "urllib3==1.26.5"], check=True)

def update_backup_script(script_path):
    logger.info(f"Updating backup script at {script_path}")
    updated_content = """#!/bin/bash
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
"""
    with open(script_path, 'w') as f:
        f.write(updated_content)
    os.chmod(script_path, 0o755)  # Make the script executable

def run_backup_script(script_path, venv_name, local_backup_path, aws_profile, aws_region, s3_bucket):
    logger.info("Running backup script")
    timestamp = subprocess.check_output(["date", "+%Y-%m-%d_%H-%M-%S"]).decode().strip()
    backup_path = os.path.join(local_backup_path, f"backup_{timestamp}")
    s3_prefix = f"backup_{timestamp}"

    cmd = [
        "/bin/bash",
        script_path,
        "--venv-name", venv_name,
        "--local-backup-path", backup_path,
        "--aws-profile", aws_profile,
        "--aws-region", aws_region,
        "--s3-bucket", s3_bucket,
        "--s3-prefix", s3_prefix
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"Backup script output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Backup script failed with exit code {e.returncode}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        raise

    return backup_path, s3_prefix

def upload_to_s3(local_path, bucket, prefix, profile_name, region):
    logger.info(f"Starting upload to S3 bucket {bucket} with prefix {prefix}")
    session = boto3.Session(profile_name=profile_name, region_name=region)
    s3 = session.client('s3')

    if not os.path.exists(local_path):
        logger.error(f"Local backup path does not exist: {local_path}")
        return

    files_to_upload = []
    for root, _, files in os.walk(local_path):
        for file in files:
            local_file = os.path.join(root, file)
            relative_path = os.path.relpath(local_file, local_path)
            s3_key = os.path.join(prefix, relative_path)
            files_to_upload.append((local_file, s3_key))

    if not files_to_upload:
        logger.warning(f"No files found to upload in {local_path}")
        return

    logger.info(f"Found {len(files_to_upload)} files to upload")

    for local_file, s3_key in files_to_upload:
        try:
            logger.info(f"Uploading {local_file} to s3://{bucket}/{s3_key}")
            s3.upload_file(local_file, bucket, s3_key)
            logger.info(f"Successfully uploaded {local_file} to s3://{bucket}/{s3_key}")
        except ClientError as e:
            logger.error(f"Error uploading {local_file}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error uploading {local_file}: {e}")

    logger.info("S3 upload process completed")

    # Verify uploads
    try:
        logger.info(f"Verifying uploads in s3://{bucket}/{prefix}")
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        uploaded_files = [obj['Key'] for obj in response.get('Contents', [])]
        logger.info(f"Found {len(uploaded_files)} files in S3 bucket")
        for uploaded_file in uploaded_files:
            logger.info(f"Verified file in S3: s3://{bucket}/{uploaded_file}")
    except ClientError as e:
        logger.error(f"Error verifying uploads: {e}")
    except Exception as e:
        logger.error(f"Unexpected error verifying uploads: {e}")

def main():
    args = parse_arguments()
    
    repo_path = os.path.join(args.repo_base_path, args.venv)
    venv_path = os.path.join(repo_path, args.venv)
    backup_script_path = os.path.join(repo_path, "backup_k3s.sh")

    try:
        clone_repo(args.github_repo_url, repo_path)
        setup_venv(venv_path)
        
        update_backup_script(backup_script_path)  # Force update the backup script

        backup_path, s3_prefix = run_backup_script(
            backup_script_path,
            args.venv, 
            args.local_backup_path, 
            args.aws_profile, 
            args.aws_region, 
            args.s3_bucket
        )

        logger.info(f"Backup completed. Local backup path: {backup_path}")
        logger.info(f"S3 prefix for upload: {s3_prefix}")

        upload_to_s3(
            backup_path, 
            args.s3_bucket, 
            s3_prefix, 
            args.aws_profile, 
            args.aws_region
        )

        logger.info("Backup process completed successfully.")

    except subprocess.CalledProcessError as e:
        logger.error(f"Error in subprocess: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        sys.exit(1)
    except ClientError as e:
        logger.error(f"AWS client error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
