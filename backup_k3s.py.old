import os
import subprocess
import boto3
from botocore.exceptions import NoCredentialsError
import argparse

def ensure_venv(venv_name):
    if not os.getenv('VIRTUAL_ENV'):
        print(f"Please activate the virtual environment {venv_name} before running the script.")
        sys.exit(1)

def backup_etcd(local_backup_path):
    etcd_dir = "/var/lib/rancher/k3s/server/db/etcd"
    backup_dir = os.path.join(local_backup_path, "etcd-backup")
    os.makedirs(backup_dir, exist_ok=True)
    subprocess.run(["sudo", "cp", "-r", etcd_dir, backup_dir], check=True)

def backup_manifests(local_backup_path):
    manifest_dir = "/var/lib/rancher/k3s/server/manifests"
    backup_dir = os.path.join(local_backup_path, "manifests-backup")
    os.makedirs(backup_dir, exist_ok=True)
    subprocess.run(["sudo", "cp", "-r", manifest_dir, backup_dir], check=True)

def export_cluster_state(local_backup_path):
    backup_file = os.path.join(local_backup_path, "k8s-resources.yaml")
    subprocess.run(["kubectl", "get", "all", "--all-namespaces", "-o", "yaml"], stdout=open(backup_file, "w"), check=True)

def upload_to_s3(local_backup_path, s3_bucket, s3_prefix, aws_profile):
    session = boto3.Session(profile_name=aws_profile)
    s3 = session.client('s3')
    for root, dirs, files in os.walk(local_backup_path):
        for file in files:
            local_file_path = os.path.join(root, file)
            s3_file_path = os.path.join(s3_prefix, os.path.relpath(local_file_path, local_backup_path))
            try:
                s3.upload_file(local_file_path, s3_bucket, s3_file_path)
                print(f"Uploaded {local_file_path} to s3://{s3_bucket}/{s3_file_path}")
            except FileNotFoundError:
                print(f"File {local_file_path} not found")
            except NoCredentialsError:
                print("Credentials not available")

def main():
    parser = argparse.ArgumentParser(description='Backup K3s cluster')
    parser.add_argument('--local-backup-path', required=True, help='Local backup directory')
    parser.add_argument('--s3-bucket', required=True, help='S3 bucket name')
    parser.add_argument('--s3-prefix', required=True, help='S3 prefix path')
    parser.add_argument('--aws-profile', required=True, help='AWS profile name')
    parser.add_argument('--venv-name', required=True, help='Virtual environment name')

    args = parser.parse_args()

    local_backup_path = args.local_backup_path
    s3_bucket = args.s3_bucket
    s3_prefix = args.s3_prefix
    aws_profile = args.aws_profile
    venv_name = args.venv_name

    ensure_venv(venv_name)
    backup_etcd(local_backup_path)
    backup_manifests(local_backup_path)
    export_cluster_state(local_backup_path)
    upload_to_s3(local_backup_path, s3_bucket, s3_prefix, aws_profile)

if __name__ == "__main__":
    main()

