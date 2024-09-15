#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import boto3
from botocore.exceptions import ClientError
import logging
from datetime import datetime

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

def run_backup_script(script_path, venv_path, venv_name, local_backup_path, aws_profile, aws_region, s3_bucket):
    logger.info("Running backup script")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = os.path.join(local_backup_path, f"backup_{timestamp}")
    s3_prefix = f"backup_{timestamp}"

    python_path = os.path.join(venv_path, "bin", "python")
    cmd = [
        python_path,
        script_path,
        "--local-backup-path", backup_path,
        "--s3-bucket", s3_bucket,
        "--s3-prefix", s3_prefix,
        "--aws-profile", aws_profile,
        "--aws-region", aws_region,
        "--venv-name", venv_name
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"Backup script output:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Backup script failed with exit code {e.returncode}")
        logger.error(f"STDOUT:\n{e.stdout}")
        logger.error(f"STDERR:\n{e.stderr}")
        raise

    return backup_path, s3_prefix

def main():
    args = parse_arguments()
    
    repo_path = os.path.join(args.repo_base_path, args.venv)
    venv_path = os.path.join(repo_path, args.venv)
    backup_script_path = os.path.join(repo_path, "backup_k3s.py")

    try:
        clone_repo(args.github_repo_url, repo_path)
        setup_venv(venv_path)
        
        logger.info("Arguments being passed to backup_k3s.py:")
        logger.info(f"--local-backup-path: {args.local_backup_path}")
        logger.info(f"--s3-bucket: {args.s3_bucket}")
        logger.info(f"--aws-profile: {args.aws_profile}")
        logger.info(f"--aws-region: {args.aws_region}")
        logger.info(f"--venv-name: {args.venv}")

        backup_path, s3_prefix = run_backup_script(
            backup_script_path,
            venv_path,
            args.venv, 
            args.local_backup_path, 
            args.aws_profile, 
            args.aws_region, 
            args.s3_bucket
        )

        logger.info(f"Backup completed. Local backup path: {backup_path}")
        logger.info(f"S3 prefix for upload: {s3_prefix}")
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