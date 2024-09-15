#!/usr/bin/env python3

import argparse
import os
import boto3
from datetime import datetime
import subprocess
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument('--local-backup-path', required=True, help='Local path to store the backup')
parser.add_argument('--s3-bucket', required=True, help='S3 bucket name')
parser.add_argument('--s3-prefix', required=True, help='S3 prefix for backup files')
parser.add_argument('--aws-profile', required=True, help='AWS profile to use')
parser.add_argument('--aws-region', required=True, help='AWS region to use')
parser.add_argument('--venv-name', required=True, help='Name of the virtual environment')
args = parser.parse_args()

logger.debug(f"Received arguments: {args}")

# Ensure the backup path exists
os.makedirs(args.local_backup_path, exist_ok=True)
logger.debug(f"Created backup directory: {args.local_backup_path}")

# Initialize boto3 session with the given AWS profile
session = boto3.Session(profile_name=args.aws_profile, region_name=args.aws_region)
s3_client = session.client('s3')
logger.debug(f"Initialized boto3 session with profile {args.aws_profile} and region {args.aws_region}")

def run_command(command):
    logger.debug(f"Running command: {command}")
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        logger.debug(f"Command output: {result.stdout}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        logger.error(f"Error output: {e.stderr}")
        raise

def backup_k3s():
    logger.info(f"Starting K3s backup to {args.local_backup_path}")
    
    # Create backup directories
    etcd_backup_path = os.path.join(args.local_backup_path, "etcd-backup")
    manifests_backup_path = os.path.join(args.local_backup_path, "manifests-backup")
    os.makedirs(etcd_backup_path, exist_ok=True)
    os.makedirs(manifests_backup_path, exist_ok=True)
    logger.debug(f"Created etcd backup directory: {etcd_backup_path}")
    logger.debug(f"Created manifests backup directory: {manifests_backup_path}")

    # Backup etcd
    run_command(["k3s", "etcd-snapshot", "save", "--dir", etcd_backup_path])
    logger.info("Etcd backup completed")

    # Backup Kubernetes resources
    resources = ["deployments", "services", "configmaps", "secrets", "ingresses", "pv", "pvc"]
    for resource in resources:
        output = run_command(["kubectl", "get", resource, "-A", "-o", "yaml"])
        file_path = os.path.join(args.local_backup_path, f"{resource}.yaml")
        with open(file_path, "w") as f:
            f.write(output)
        logger.debug(f"Backed up {resource} to {file_path}")

    # Backup all YAML files in the manifests directory
    manifests_dir = "/var/lib/rancher/k3s/server/manifests"
    for filename in os.listdir(manifests_dir):
        if filename.endswith(".yaml"):
            src = os.path.join(manifests_dir, filename)
            dst = os.path.join(manifests_backup_path, filename)
            run_command(["cp", src, dst])
            logger.debug(f"Copied {src} to {dst}")

    logger.info("K3s backup completed successfully")

def upload_to_s3():
    logger.info(f"Uploading backup to S3 bucket {args.s3_bucket} with prefix {args.s3_prefix}")

    for root, _, files in os.walk(args.local_backup_path):
        for file in files:
            local_file = os.path.join(root, file)
            relative_path = os.path.relpath(local_file, args.local_backup_path)
            s3_key = f"{args.s3_prefix}/{relative_path}"
            
            logger.debug(f"Uploading {local_file} to s3://{args.s3_bucket}/{s3_key}")
            s3_client.upload_file(local_file, args.s3_bucket, s3_key)
            logger.debug(f"Upload complete for {local_file}")

    logger.info("S3 upload completed successfully")

def main():
    try:
        backup_k3s()
        upload_to_s3()
        logger.info("Backup and upload process completed successfully")
    except Exception as e:
        logger.error(f"Backup process failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()