#!/usr/bin/env python3
"""
Complete AWS Deployment Script for TraceTrack
This script handles the entire deployment process to AWS
"""

import boto3
import subprocess
import json
import time
import os
import sys
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AWSDeployer:
    def __init__(self):
        self.region = os.environ.get('AWS_DEFAULT_REGION', 'ap-south-1')
        self.stack_name = 'tracetrack-production'
        self.ecr_repo_name = 'tracetrack'
        self.cluster_name = 'tracetrack-cluster'
        self.service_name = 'tracetrack-service'
        
        # Check AWS credentials
        self.check_credentials()
        
        # Initialize AWS clients
        self.cloudformation = boto3.client('cloudformation', region_name=self.region)
        self.ecr = boto3.client('ecr', region_name=self.region)
        self.ecs = boto3.client('ecs', region_name=self.region)
        self.dynamodb = boto3.client('dynamodb', region_name=self.region)
        self.iam = boto3.client('iam', region_name=self.region)
        self.logs = boto3.client('logs', region_name=self.region)
        
    def check_credentials(self):
        """Check if AWS credentials are configured"""
        if not os.environ.get('AWS_ACCESS_KEY_ID'):
            logger.error("❌ AWS_ACCESS_KEY_ID not found in environment")
            logger.info("Please set your AWS credentials:")
            logger.info("export AWS_ACCESS_KEY_ID=your_access_key")
            logger.info("export AWS_SECRET_ACCESS_KEY=your_secret_key")
            logger.info("export AWS_DEFAULT_REGION=ap-south-1")
            sys.exit(1)
            
        # Test credentials
        try:
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            logger.info(f"✅ AWS credentials verified - Account: {identity['Account']}")
        except Exception as e:
            logger.error(f"❌ AWS credentials invalid: {e}")
            sys.exit(1)
    
    def create_ecr_repository(self):
        """Create ECR repository for Docker images"""
        try:
            self.ecr.create_repository(
                repositoryName=self.ecr_repo_name,
                imageScanningConfiguration={'scanOnPush': True},
                encryptionConfiguration={'encryptionType': 'AES256'}
            )
            logger.info(f"✅ Created ECR repository: {self.ecr_repo_name}")
        except self.ecr.exceptions.RepositoryAlreadyExistsException:
            logger.info(f"ECR repository {self.ecr_repo_name} already exists")
    
    def build_and_push_docker_image(self):
        """Build and push Docker image to ECR"""
        # Get ECR login token
        response = self.ecr.get_authorization_token()
        token = response['authorizationData'][0]['authorizationToken']
        registry_url = response['authorizationData'][0]['proxyEndpoint']
        
        # Login to ECR
        logger.info("🔐 Logging into ECR...")
        subprocess.run([
            'docker', 'login', '--username', 'AWS', '--password-stdin', registry_url
        ], input=token.encode(), check=True)
        
        # Build Docker image
        image_tag = f"{registry_url.replace('https://', '')}/{self.ecr_repo_name}:latest"
        logger.info(f"🏗️ Building Docker image: {image_tag}")
        
        subprocess.run([
            'docker', 'build', '-t', image_tag, '.'
        ], check=True)
        
        # Push to ECR
        logger.info("📤 Pushing image to ECR...")
        subprocess.run(['docker', 'push', image_tag], check=True)
        
        return image_tag
    
    def create_cloudformation_stack(self):
        """Create CloudFormation stack with all infrastructure"""
        logger.info("🏗️ Creating CloudFormation stack...")
        
        # Read CloudFormation template
        with open('aws_cloudformation_template.yaml', 'r') as f:
            template_body = f.read()
        
        try:
            response = self.cloudformation.create_stack(
                StackName=self.stack_name,
                TemplateBody=template_body,
                Parameters=[
                    {
                        'ParameterKey': 'Environment',
                        'ParameterValue': 'production'
                    }
                ],
                Capabilities=['CAPABILITY_NAMED_IAM'],
                OnFailure='ROLLBACK'
            )
            
            logger.info(f"✅ CloudFormation stack creation initiated: {response['StackId']}")
            return response['StackId']
            
        except self.cloudformation.exceptions.AlreadyExistsException:
            logger.info(f"CloudFormation stack {self.stack_name} already exists")
            return None
    
    def wait_for_stack_completion(self, stack_id=None):
        """Wait for CloudFormation stack to complete"""
        if not stack_id:
            stack_id = self.stack_name
            
        logger.info("⏳ Waiting for CloudFormation stack to complete...")
        
        while True:
            try:
                response = self.cloudformation.describe_stacks(StackName=stack_id)
                status = response['Stacks'][0]['StackStatus']
                
                if status.endswith('COMPLETE'):
                    logger.info(f"✅ CloudFormation stack completed: {status}")
                    return response['Stacks'][0]
                elif status.endswith('FAILED') or status.endswith('ROLLBACK'):
                    logger.error(f"❌ CloudFormation stack failed: {status}")
                    return None
                else:
                    logger.info(f"⏳ Stack status: {status}")
                    time.sleep(30)
                    
            except Exception as e:
                logger.error(f"Error checking stack status: {e}")
                time.sleep(30)
    
    def create_ecs_cluster(self):
        """Create ECS cluster"""
        try:
            self.ecs.create_cluster(
                clusterName=self.cluster_name,
                capacityProviders=['FARGATE'],
                defaultCapacityProviderStrategy=[
                    {
                        'capacityProvider': 'FARGATE',
                        'weight': 1
                    }
                ]
            )
            logger.info(f"✅ Created ECS cluster: {self.cluster_name}")
        except self.ecs.exceptions.ClusterAlreadyExistsException:
            logger.info(f"ECS cluster {self.cluster_name} already exists")
    
    def create_task_definition(self, image_uri):
        """Create ECS task definition"""
        task_def = {
            'family': 'tracetrack-task',
            'networkMode': 'awsvpc',
            'requiresCompatibilities': ['FARGATE'],
            'cpu': '1024',
            'memory': '2048',
            'executionRoleArn': 'ecsTaskExecutionRole',
            'containerDefinitions': [
                {
                    'name': 'tracetrack-app',
                    'image': image_uri,
                    'portMappings': [
                        {
                            'containerPort': 8000,
                            'protocol': 'tcp'
                        }
                    ],
                    'environment': [
                        {
                            'name': 'FLASK_ENV',
                            'value': 'production'
                        },
                        {
                            'name': 'AWS_DEFAULT_REGION',
                            'value': self.region
                        }
                    ],
                    'logConfiguration': {
                        'logDriver': 'awslogs',
                        'options': {
                            'awslogs-group': '/ecs/tracetrack',
                            'awslogs-region': self.region,
                            'awslogs-stream-prefix': 'ecs'
                        }
                    },
                    'healthCheck': {
                        'command': ['CMD-SHELL', 'curl -f http://localhost:8000/health || exit 1'],
                        'interval': 30,
                        'timeout': 5,
                        'retries': 3,
                        'startPeriod': 60
                    }
                }
            ]
        }
        
        try:
            response = self.ecs.register_task_definition(**task_def)
            logger.info(f"✅ Created task definition: {response['taskDefinition']['taskDefinitionArn']}")
            return response['taskDefinition']['taskDefinitionArn']
        except Exception as e:
            logger.error(f"Error creating task definition: {e}")
            return None
    
    def create_log_group(self):
        """Create CloudWatch log group"""
        try:
            self.logs.create_log_group(logGroupName='/ecs/tracetrack')
            logger.info("✅ Created CloudWatch log group")
        except self.logs.exceptions.ResourceAlreadyExistsException:
            logger.info("CloudWatch log group already exists")
    
    def create_ecs_service(self, task_def_arn):
        """Create ECS service"""
        try:
            # Get VPC and subnets from CloudFormation stack
            stack_outputs = self.cloudformation.describe_stacks(
                StackName=self.stack_name
            )['Stacks'][0]['Outputs']
            
            vpc_id = None
            subnet_ids = []
            security_group_id = None
            
            for output in stack_outputs:
                if output['OutputKey'] == 'VPCId':
                    vpc_id = output['OutputValue']
                elif output['OutputKey'] == 'PublicSubnetIds':
                    subnet_ids = output['OutputValue'].split(',')
                elif output['OutputKey'] == 'ContainerSecurityGroupId':
                    security_group_id = output['OutputValue']
            
            if not vpc_id or not subnet_ids or not security_group_id:
                logger.error("❌ Could not get VPC information from CloudFormation stack")
                return None
            
            service_def = {
                'cluster': self.cluster_name,
                'serviceName': self.service_name,
                'taskDefinition': task_def_arn,
                'desiredCount': 2,
                'launchType': 'FARGATE',
                'networkConfiguration': {
                    'awsvpcConfiguration': {
                        'subnets': subnet_ids,
                        'securityGroups': [security_group_id],
                        'assignPublicIp': 'ENABLED'
                    }
                },
                'deploymentConfiguration': {
                    'maximumPercent': 200,
                    'minimumHealthyPercent': 50
                }
            }
            
            response = self.ecs.create_service(**service_def)
            logger.info(f"✅ Created ECS service: {response['service']['serviceArn']}")
            return response['service']['serviceArn']
            
        except Exception as e:
            logger.error(f"Error creating ECS service: {e}")
            return None
    
    def get_service_url(self):
        """Get the public URL of the deployed service"""
        try:
            # Get ALB URL from CloudFormation stack
            stack_outputs = self.cloudformation.describe_stacks(
                StackName=self.stack_name
            )['Stacks'][0]['Outputs']
            
            for output in stack_outputs:
                if output['OutputKey'] == 'ApplicationURL':
                    return output['OutputValue']
            
            return None
        except Exception as e:
            logger.error(f"Error getting service URL: {e}")
            return None
    
    def deploy(self):
        """Main deployment method"""
        logger.info("🚀 Starting AWS deployment...")
        
        try:
            # Step 1: Create ECR repository
            self.create_ecr_repository()
            
            # Step 2: Build and push Docker image
            image_uri = self.build_and_push_docker_image()
            
            # Step 3: Create CloudFormation stack
            stack_id = self.create_cloudformation_stack()
            
            # Step 4: Wait for stack completion
            if stack_id:
                stack_result = self.wait_for_stack_completion(stack_id)
                if not stack_result:
                    logger.error("❌ CloudFormation stack failed")
                    return False
            
            # Step 5: Create ECS cluster
            self.create_ecs_cluster()
            
            # Step 6: Create log group
            self.create_log_group()
            
            # Step 7: Create task definition
            task_def_arn = self.create_task_definition(image_uri)
            if not task_def_arn:
                logger.error("❌ Failed to create task definition")
                return False
            
            # Step 8: Create ECS service
            service_arn = self.create_ecs_service(task_def_arn)
            if not service_arn:
                logger.error("❌ Failed to create ECS service")
                return False
            
            # Step 9: Get service URL
            service_url = self.get_service_url()
            if service_url:
                logger.info(f"🌐 Application deployed successfully!")
                logger.info(f"📱 Service URL: {service_url}")
                logger.info(f"📊 CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/home?region={self.region}#logsV2:log-groups/log-group/$252Fecs$252Ftracetrack")
            else:
                logger.warning("⚠️ Could not retrieve service URL")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Deployment failed: {e}")
            return False

def main():
    """Main function"""
    deployer = AWSDeployer()
    success = deployer.deploy()
    
    if success:
        logger.info("🎉 Deployment completed successfully!")
        sys.exit(0)
    else:
        logger.error("💥 Deployment failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()