import os
import subprocess
import argparse
import boto3
from datetime import datetime

def run_command(command):
    """Run a shell command and check for errors."""
    result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
    return result.stdout

def clone_repo(github_repo_url, repo_path):
    """Clone the GitHub repository."""
    if os.path.exists(repo_path):
        run_command(f"rm -rf {repo_path}")
    run_command(f"git clone {github_repo_url} {repo_path}")

def create_venv(venv_path):
    """Create a virtual environment."""
    if not os.path.exists(venv_path):
        run_command(f"python3 -m venv {venv_path}")

def activate_venv(venv_path):
    """Activate the virtual environment."""
    activate_script = os.path.join(venv_path, 'bin', 'activate')
    return f"source {activate_script}"

def install_dependencies(venv_path):
    """Install the required dependencies."""
    pip_install_cmd = f"{activate_venv(venv_path)} && pip install --upgrade pip boto3==1.18.17 botocore==1.21.17 urllib3==1.26.5"
    run_command(pip_install_cmd)

def create_backup(local_backup_path):
    """Create a backup structure with files."""
    os.makedirs(local_backup_path, exist_ok=True)
    etcd_backup_path = os.path.join(local_backup_path, 'etcd-backup/etcd')
    manifests_backup_path = os.path.join(local_backup_path, 'manifests-backup/manifests')

    os.makedirs(etcd_backup_path, exist_ok=True)
    os.makedirs(manifests_backup_path, exist_ok=True)

    files = {
        'k8s-resources.yaml': 'sample k8s resources data',
        'etcd-backup/etcd/name': 'sample etcd name data',
        'manifests-backup/manifests/rolebindings.yaml': 'sample rolebindings data',
        'manifests-backup/manifests/ccm.yaml': 'sample ccm data',
        'manifests-backup/manifests/coredns.yaml': 'sample coredns data',
        'manifests-backup/manifests/runtimes.yaml': 'sample runtimes data',
        'manifests-backup/manifests/traefik.yaml': 'sample traefik data',
        'manifests-backup/manifests/local-storage.yaml': 'sample local storage data',
        'manifests-backup/manifests/metrics-server/aggregated-metrics-reader.yaml': 'sample metrics reader data',
        'manifests-backup/manifests/metrics-server/metrics-apiservice.yaml': 'sample metrics apiservice data',
        'manifests-backup/manifests/metrics-server/metrics-server-deployment.yaml': 'sample metrics deployment data',
        'manifests-backup/manifests/metrics-server/resource-reader.yaml': 'sample resource reader data',
        'manifests-backup/manifests/metrics-server/auth-reader.yaml': 'sample auth reader data',
        'manifests-backup/manifests/metrics-server/metrics-server-service.yaml': 'sample metrics service data',
        'manifests-backup/manifests/metrics-server/auth-delegator.yaml': 'sample auth delegator data',
    }

    for file_path, content in files.items():
        full_path = os.path.join(local_backup_path, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content)

    return local_backup_path

def upload_to_s3(backup_path, s3_bucket, s3_prefix, aws_profile):
    """Upload the backup files to AWS S3."""
    session = boto3.Session(profile_name=aws_profile)
    s3_client = session.client('s3')

    for root, dirs, files in os.walk(backup_path):
        for file in files:
            local_file_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_file_path, backup_path)
            s3_key = f"{s3_prefix}/{relative_path}"
            s3_client.upload_file(local_file_path, s3_bucket, s3_key)
            print(f"Uploaded {local_file_path} to s3://{s3_bucket}/{s3_key}")

def upload_to_wasabi(backup_path, s3_bucket, s3_prefix, wasabi_profile, wasabi_region, wasabi_endpoint):
    """Upload the backup files to Wasabi S3."""
    for root, dirs, files in os.walk(backup_path):
        for file in files:
            local_file_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_file_path, backup_path)
            s3_key = f"{s3_prefix}/{relative_path}"
            wasabi_cmd = (
                f"aws s3 cp {local_file_path} s3://{s3_bucket}/{s3_key} "
                f"--profile {wasabi_profile} --region {wasabi_region} --endpoint-url {wasabi_endpoint} --debug"
            )
            run_command(wasabi_cmd)
            print(f"Uploaded {local_file_path} to Wasabi s3://{s3_bucket}/{s3_key}")

def main():
    parser = argparse.ArgumentParser(description='Backup script for K3S cluster.')
    parser.add_argument('--github-repo-url', required=True, help='GitHub repository URL')
    parser.add_argument('--venv', required=True, help='Virtual environment name')
    parser.add_argument('--local-backup-path', required=True, help='Local backup path')
    parser.add_argument('--aws-profile', required=True, help='AWS profile name')
    parser.add_argument('--wasabi-profile', required=True, help='Wasabi profile name')
    parser.add_argument('--wasabi-region', required=True, help='Wasabi region')
    parser.add_argument('--wasabi-endpoint', required=True, help='Wasabi endpoint URL')
    args = parser.parse_args()

    repo_base_path = "/tmp"
    repo_path = os.path.join(repo_base_path, args.venv)
    venv_path = os.path.join(repo_path, args.venv)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    local_backup_path = os.path.join(args.local_backup_path, f"backup_{timestamp}")
    s3_prefix = f"backup_{timestamp}"

    # Clone the repository
    clone_repo(args.github_repo_url, repo_path)

    # Create and activate the virtual environment
    create_venv(venv_path)
    install_dependencies(venv_path)

    # Create the backup
    backup_path = create_backup(local_backup_path)

    # Upload to AWS S3
    upload_to_s3(backup_path, args.venv, s3_prefix, args.aws_profile)

    # Upload to Wasabi S3
    upload_to_wasabi(backup_path, args.venv, s3_prefix, args.wasabi_profile, args.wasabi_region, args.wasabi_endpoint)

    print("Backup process completed successfully.")

if __name__ == "__main__":
    main()

