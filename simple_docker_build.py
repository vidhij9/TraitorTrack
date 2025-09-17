#!/usr/bin/env python3
"""
Simple Docker image build and push script
Creates a basic TraceTrack image and pushes to ECR
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a shell command and return result"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return None

def create_dockerfile():
    """Create a simple Dockerfile"""
    dockerfile_content = """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:5000/health || exit 1

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "main:app"]
"""
    
    with open('Dockerfile.simple', 'w') as f:
        f.write(dockerfile_content)
    print("✅ Created simple Dockerfile")

def create_requirements():
    """Create requirements.txt"""
    requirements = """flask==3.0.0
gunicorn==21.2.0
psycopg2-binary==2.9.7
SQLAlchemy==2.0.23
Flask-SQLAlchemy==3.1.1
redis==5.0.1
flask-login==0.6.3
werkzeug==3.0.1
requests==2.31.0
"""
    
    with open('requirements.txt', 'w') as f:
        f.write(requirements)
    print("✅ Created requirements.txt")

def main():
    """Main build and push process"""
    print("🚀 Starting Docker image build and push to AWS ECR")
    
    # AWS configuration
    aws_region = 'us-east-1'
    account_id = '605134465544'
    repo_name = 'tracetrack'
    image_tag = 'latest'
    
    ecr_uri = f"{account_id}.dkr.ecr.{aws_region}.amazonaws.com/{repo_name}"
    
    # Set AWS environment
    os.environ['AWS_DEFAULT_REGION'] = aws_region
    
    # Create build files
    create_dockerfile()
    create_requirements()
    
    # Login to ECR
    login_cmd = f"aws ecr get-login-password --region {aws_region} | docker login --username AWS --password-stdin {account_id}.dkr.ecr.{aws_region}.amazonaws.com"
    if not run_command(login_cmd, "ECR login"):
        sys.exit(1)
    
    # Build image
    build_cmd = f"docker build -f Dockerfile.simple -t {repo_name}:{image_tag} ."
    if not run_command(build_cmd, "Docker build"):
        sys.exit(1)
    
    # Tag image
    tag_cmd = f"docker tag {repo_name}:{image_tag} {ecr_uri}:{image_tag}"
    if not run_command(tag_cmd, "Docker tag"):
        sys.exit(1)
    
    # Push image
    push_cmd = f"docker push {ecr_uri}:{image_tag}"
    if not run_command(push_cmd, "Docker push"):
        sys.exit(1)
    
    print("🎉 Docker image successfully built and pushed!")
    print(f"📍 Image URI: {ecr_uri}:{image_tag}")
    
    return f"{ecr_uri}:{image_tag}"

if __name__ == "__main__":
    image_uri = main()