#!/usr/bin/env python3
"""
Blue-Green Deployment Script for TraceTrack AWS Migration
Provides zero-downtime migration from Replit to AWS
"""

import boto3
import time
import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BlueGreenDeployment:
    def __init__(self, region: str = 'us-east-1'):
        self.region = region
        self.elbv2 = boto3.client('elbv2', region_name=region)
        self.route53 = boto3.client('route53', region_name=region)
        self.ecs = boto3.client('ecs', region_name=region)
        self.cloudformation = boto3.client('cloudformation', region_name=region)
        
        # Deployment configuration
        self.stack_name = 'tracetrack-production'
        self.health_check_timeout = 300  # 5 minutes
        self.health_check_interval = 10  # 10 seconds
        
    def get_stack_outputs(self) -> Dict[str, str]:
        """Get CloudFormation stack outputs"""
        try:
            response = self.cloudformation.describe_stacks(StackName=self.stack_name)
            outputs = {}
            
            for output in response['Stacks'][0].get('Outputs', []):
                outputs[output['OutputKey']] = output['OutputValue']
            
            return outputs
        except Exception as e:
            logger.error(f"Failed to get stack outputs: {e}")
            return {}
    
    def health_check_endpoint(self, url: str, timeout: int = 10) -> bool:
        """Check if an endpoint is healthy"""
        try:
            health_url = f"{url.rstrip('/')}/health"
            response = requests.get(health_url, timeout=timeout)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed for {url}: {e}")
            return False
    
    def validate_aws_deployment(self) -> Dict[str, Any]:
        """Validate AWS deployment health"""
        logger.info("🔍 Validating AWS deployment health...")
        
        outputs = self.get_stack_outputs()
        alb_dns = outputs.get('ALBDNSName')
        cloudfront_url = outputs.get('CloudFrontURL')
        
        if not alb_dns:
            return {'healthy': False, 'reason': 'ALB DNS not found'}
        
        # Health check AWS endpoints
        health_results = {
            'alb_health': False,
            'cloudfront_health': False,
            'response_times': {}
        }
        
        # Test ALB health
        alb_url = f"http://{alb_dns}"
        start_time = time.time()
        health_results['alb_health'] = self.health_check_endpoint(alb_url)
        health_results['response_times']['alb'] = (time.time() - start_time) * 1000
        
        # Test CloudFront health (if available)
        if cloudfront_url:
            start_time = time.time()
            health_results['cloudfront_health'] = self.health_check_endpoint(cloudfront_url)
            health_results['response_times']['cloudfront'] = (time.time() - start_time) * 1000
        
        # Check ECS service status
        try:
            cluster_name = outputs.get('ECSClusterName')
            service_name = 'tracetrack-production-service'
            
            if cluster_name:
                response = self.ecs.describe_services(
                    cluster=cluster_name,
                    services=[service_name]
                )
                
                service = response['services'][0] if response['services'] else None
                if service:
                    health_results['ecs_running_count'] = service.get('runningCount', 0)
                    health_results['ecs_desired_count'] = service.get('desiredCount', 0)
                    health_results['ecs_healthy'] = (
                        service.get('runningCount', 0) >= service.get('desiredCount', 0)
                    )
        except Exception as e:
            logger.warning(f"Could not check ECS service status: {e}")
            health_results['ecs_healthy'] = False
        
        # Overall health assessment
        overall_healthy = (
            health_results['alb_health'] and
            health_results.get('ecs_healthy', False)
        )
        
        return {
            'healthy': overall_healthy,
            'details': health_results,
            'alb_url': alb_url,
            'cloudfront_url': cloudfront_url,
            'timestamp': datetime.now().isoformat()
        }
    
    def wait_for_deployment_health(self, max_wait_time: int = 600) -> bool:
        """Wait for AWS deployment to be healthy"""
        logger.info(f"⏳ Waiting for AWS deployment to be healthy (timeout: {max_wait_time}s)...")
        
        start_time = time.time()
        while (time.time() - start_time) < max_wait_time:
            validation = self.validate_aws_deployment()
            
            if validation['healthy']:
                logger.info(f"✅ AWS deployment is healthy!")
                logger.info(f"   ALB Response Time: {validation['details']['response_times'].get('alb', 0):.1f}ms")
                logger.info(f"   ECS Running Tasks: {validation['details'].get('ecs_running_count', 0)}")
                return True
            
            logger.info(f"⚠️ AWS deployment not yet healthy, waiting {self.health_check_interval}s...")
            if 'details' in validation:
                details = validation['details']
                logger.info(f"   ALB Health: {'✅' if details.get('alb_health') else '❌'}")
                logger.info(f"   ECS Health: {'✅' if details.get('ecs_healthy') else '❌'}")
            
            time.sleep(self.health_check_interval)
        
        logger.error(f"❌ AWS deployment failed to become healthy within {max_wait_time}s")
        return False
    
    def create_route53_weighted_routing(self, hosted_zone_id: str, domain_name: str, 
                                      replit_url: str, aws_weight: int = 10) -> bool:
        """Create Route53 weighted routing for gradual traffic shift"""
        logger.info(f"🔄 Setting up Route53 weighted routing (AWS: {aws_weight}%, Replit: {100-aws_weight}%)...")
        
        try:
            outputs = self.get_stack_outputs()
            cloudfront_url = outputs.get('CloudFrontURL', '').replace('https://', '')
            
            if not cloudfront_url:
                logger.error("CloudFront URL not found")
                return False
            
            # Create weighted record for AWS (CloudFront)
            aws_record = {
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': domain_name,
                    'Type': 'CNAME',
                    'SetIdentifier': 'AWS-TraceTrack',
                    'Weight': aws_weight,
                    'TTL': 60,
                    'ResourceRecords': [{'Value': cloudfront_url}]
                }
            }
            
            # Create weighted record for Replit
            replit_record = {
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': domain_name,
                    'Type': 'CNAME',
                    'SetIdentifier': 'Replit-TraceTrack',
                    'Weight': 100 - aws_weight,
                    'TTL': 60,
                    'ResourceRecords': [{'Value': replit_url}]
                }
            }
            
            # Apply the changes
            response = self.route53.change_resource_record_sets(
                HostedZoneId=hosted_zone_id,
                ChangeBatch={
                    'Changes': [aws_record, replit_record]
                }
            )
            
            # Wait for DNS changes to propagate
            change_id = response['ChangeInfo']['Id']
            logger.info(f"⏳ Waiting for DNS changes to propagate...")
            
            self.route53.get_waiter('resource_record_sets_changed').wait(Id=change_id)
            
            logger.info("✅ Route53 weighted routing configured successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure Route53 weighted routing: {e}")
            return False
    
    def gradual_traffic_migration(self, hosted_zone_id: str, domain_name: str, 
                                replit_url: str) -> bool:
        """Perform gradual traffic migration from Replit to AWS"""
        logger.info("🚀 Starting gradual traffic migration...")
        
        # Traffic migration stages
        migration_stages = [
            {'aws_weight': 10, 'wait_time': 300},   # 10% for 5 minutes
            {'aws_weight': 25, 'wait_time': 300},   # 25% for 5 minutes
            {'aws_weight': 50, 'wait_time': 300},   # 50% for 5 minutes
            {'aws_weight': 75, 'wait_time': 300},   # 75% for 5 minutes
            {'aws_weight': 100, 'wait_time': 0}     # 100% (final)
        ]
        
        for i, stage in enumerate(migration_stages, 1):
            aws_weight = stage['aws_weight']
            wait_time = stage['wait_time']
            
            logger.info(f"📊 Stage {i}/{len(migration_stages)}: Routing {aws_weight}% traffic to AWS...")
            
            # Update Route53 weights
            if not self.create_route53_weighted_routing(hosted_zone_id, domain_name, replit_url, aws_weight):
                logger.error(f"Failed to update traffic routing for stage {i}")
                return False
            
            # Wait and monitor
            if wait_time > 0:
                logger.info(f"⏳ Monitoring for {wait_time} seconds...")
                
                # Monitor health during the wait period
                monitor_start = time.time()
                while (time.time() - monitor_start) < wait_time:
                    validation = self.validate_aws_deployment()
                    if not validation['healthy']:
                        logger.error("❌ AWS deployment became unhealthy during migration!")
                        logger.info("🔄 Rolling back traffic routing...")
                        self.rollback_traffic(hosted_zone_id, domain_name, replit_url)
                        return False
                    
                    time.sleep(60)  # Check health every minute
                
                logger.info(f"✅ Stage {i} completed successfully")
            else:
                logger.info("🎉 Traffic migration completed - 100% on AWS!")
        
        return True
    
    def rollback_traffic(self, hosted_zone_id: str, domain_name: str, replit_url: str) -> bool:
        """Rollback traffic to Replit (100% Replit, 0% AWS)"""
        logger.info("🔄 Rolling back traffic to Replit...")
        
        try:
            # Delete AWS weighted record
            self.route53.change_resource_record_sets(
                HostedZoneId=hosted_zone_id,
                ChangeBatch={
                    'Changes': [{
                        'Action': 'DELETE',
                        'ResourceRecordSet': {
                            'Name': domain_name,
                            'Type': 'CNAME',
                            'SetIdentifier': 'AWS-TraceTrack',
                            'Weight': 100,
                            'TTL': 60,
                            'ResourceRecords': [{'Value': 'placeholder.value'}]
                        }
                    }]
                }
            )
            
            # Update Replit record to 100%
            self.route53.change_resource_record_sets(
                HostedZoneId=hosted_zone_id,
                ChangeBatch={
                    'Changes': [{
                        'Action': 'UPSERT',
                        'ResourceRecordSet': {
                            'Name': domain_name,
                            'Type': 'CNAME',
                            'TTL': 300,
                            'ResourceRecords': [{'Value': replit_url}]
                        }
                    }]
                }
            )
            
            logger.info("✅ Traffic rolled back to Replit successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback traffic: {e}")
            return False
    
    def complete_migration(self, hosted_zone_id: str, domain_name: str) -> bool:
        """Complete the migration by pointing domain to CloudFront"""
        logger.info("🏁 Completing migration - pointing domain to AWS CloudFront...")
        
        try:
            outputs = self.get_stack_outputs()
            cloudfront_url = outputs.get('CloudFrontURL', '').replace('https://', '')
            
            if not cloudfront_url:
                logger.error("CloudFront URL not found")
                return False
            
            # Remove weighted records and set final CNAME
            response = self.route53.change_resource_record_sets(
                HostedZoneId=hosted_zone_id,
                ChangeBatch={
                    'Changes': [{
                        'Action': 'UPSERT',
                        'ResourceRecordSet': {
                            'Name': domain_name,
                            'Type': 'CNAME',
                            'TTL': 300,
                            'ResourceRecords': [{'Value': cloudfront_url}]
                        }
                    }]
                }
            )
            
            change_id = response['ChangeInfo']['Id']
            logger.info("⏳ Waiting for final DNS changes...")
            
            self.route53.get_waiter('resource_record_sets_changed').wait(Id=change_id)
            
            logger.info("✅ Migration completed successfully!")
            logger.info(f"   Domain: {domain_name} → {cloudfront_url}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete migration: {e}")
            return False
    
    def run_blue_green_deployment(self, hosted_zone_id: Optional[str] = None, 
                                 domain_name: Optional[str] = None, 
                                 replit_url: Optional[str] = None) -> bool:
        """Run complete blue-green deployment process"""
        logger.info("🚀 Starting Blue-Green Deployment for TraceTrack Migration")
        logger.info("="*60)
        
        # Step 1: Validate AWS deployment
        if not self.wait_for_deployment_health():
            logger.error("❌ AWS deployment validation failed")
            return False
        
        # Step 2: DNS-based traffic migration (if DNS parameters provided)
        if hosted_zone_id and domain_name and replit_url:
            logger.info("🌐 Starting DNS-based traffic migration...")
            
            if not self.gradual_traffic_migration(hosted_zone_id, domain_name, replit_url):
                logger.error("❌ Traffic migration failed")
                return False
            
            # Step 3: Complete migration
            if not self.complete_migration(hosted_zone_id, domain_name):
                logger.error("❌ Failed to complete migration")
                return False
        else:
            logger.info("ℹ️ DNS parameters not provided - skipping traffic migration")
            logger.info("   Manual DNS update required to complete migration")
        
        # Step 4: Final validation
        final_validation = self.validate_aws_deployment()
        if not final_validation['healthy']:
            logger.error("❌ Final validation failed")
            return False
        
        logger.info("="*60)
        logger.info("🎉 BLUE-GREEN DEPLOYMENT COMPLETED SUCCESSFULLY!")
        logger.info("="*60)
        
        # Print summary
        self.print_migration_summary(final_validation)
        
        return True
    
    def print_migration_summary(self, validation: Dict[str, Any]):
        """Print migration completion summary"""
        logger.info("")
        logger.info("MIGRATION SUMMARY")
        logger.info("-" * 40)
        logger.info(f"✅ AWS Infrastructure: Healthy")
        logger.info(f"✅ ALB Response Time: {validation['details']['response_times'].get('alb', 0):.1f}ms")
        
        if 'cloudfront' in validation['details']['response_times']:
            logger.info(f"✅ CloudFront Response Time: {validation['details']['response_times']['cloudfront']:.1f}ms")
        
        logger.info(f"✅ ECS Tasks Running: {validation['details'].get('ecs_running_count', 'Unknown')}")
        logger.info(f"🌐 ALB URL: {validation.get('alb_url', 'Unknown')}")
        logger.info(f"🌐 CloudFront URL: {validation.get('cloudfront_url', 'Unknown')}")
        logger.info("")
        logger.info("NEXT STEPS:")
        logger.info("1. Monitor application performance")
        logger.info("2. Run data migration scripts if needed")
        logger.info("3. Update monitoring and alerting")
        logger.info("4. Decommission Replit environment when satisfied")
        logger.info("-" * 40)

def main():
    """Main deployment function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Blue-Green Deployment for TraceTrack')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--hosted-zone-id', help='Route53 hosted zone ID')
    parser.add_argument('--domain-name', help='Domain name for traffic migration')
    parser.add_argument('--replit-url', help='Current Replit URL')
    parser.add_argument('--validate-only', action='store_true', help='Only validate AWS deployment')
    
    args = parser.parse_args()
    
    # Create deployment manager
    deployment = BlueGreenDeployment(region=args.region)
    
    if args.validate_only:
        logger.info("🔍 Running validation only...")
        validation = deployment.validate_aws_deployment()
        
        if validation['healthy']:
            logger.info("✅ AWS deployment is healthy")
            deployment.print_migration_summary(validation)
            sys.exit(0)
        else:
            logger.error("❌ AWS deployment validation failed")
            logger.error(f"Reason: {validation.get('reason', 'Unknown')}")
            sys.exit(1)
    
    # Run full blue-green deployment
    success = deployment.run_blue_green_deployment(
        hosted_zone_id=args.hosted_zone_id,
        domain_name=args.domain_name,
        replit_url=args.replit_url
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()