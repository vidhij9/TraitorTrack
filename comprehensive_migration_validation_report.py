#!/usr/bin/env python3
"""
Comprehensive AWS Migration Validation Report Generator
Combines all validation results and generates final migration readiness report
"""

import json
import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, List
import os
import subprocess

# Import our validation modules
from aws_performance_validation import AWSPerformanceValidator
from aws_simulation_validator import AWSInfrastructureSimulator, AWSComponentConfig
from blue_green_deployment_validator import BlueGreenValidator, DeploymentConfig

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveMigrationValidator:
    """Comprehensive migration validation orchestrator"""
    
    def __init__(self):
        self.validation_results = {
            'validation_timestamp': datetime.now().isoformat(),
            'validation_suite_version': '1.0.0',
            'current_environment': 'replit',
            'target_environment': 'aws',
            'validations': {},
            'executive_summary': {},
            'detailed_analysis': {},
            'migration_roadmap': {}
        }
        
    async def run_complete_validation_suite(self) -> Dict[str, Any]:
        """Run complete validation suite and generate comprehensive report"""
        logger.info("🚀 Starting comprehensive AWS migration validation suite...")
        
        start_time = time.time()
        
        try:
            # 1. Current Environment Performance Validation
            logger.info("📊 Phase 1: Current Environment Performance Assessment")
            performance_validator = AWSPerformanceValidator("http://localhost:5000")
            performance_results = await performance_validator.run_comprehensive_validation()
            self.validation_results['validations']['current_performance'] = performance_results
            
            # 2. AWS Infrastructure Simulation
            logger.info("☁️ Phase 2: AWS Infrastructure Component Simulation")
            aws_config = AWSComponentConfig()
            aws_simulator = AWSInfrastructureSimulator(aws_config)
            aws_simulation_results = await aws_simulator.run_full_simulation()
            self.validation_results['validations']['aws_simulation'] = aws_simulation_results
            
            # 3. Blue-Green Deployment Validation
            logger.info("🔄 Phase 3: Blue-Green Deployment Process Validation")
            deployment_config = DeploymentConfig()
            blue_green_validator = BlueGreenValidator(deployment_config)
            deployment_results = await blue_green_validator.run_comprehensive_validation()
            self.validation_results['validations']['deployment_validation'] = deployment_results
            
            # 4. Generate comprehensive analysis
            logger.info("📈 Phase 4: Generating Comprehensive Analysis")
            self._generate_executive_summary()
            self._generate_detailed_analysis()
            self._generate_migration_roadmap()
            
            total_validation_time = time.time() - start_time
            self.validation_results['total_validation_time_seconds'] = total_validation_time
            
            logger.info(f"✅ Comprehensive validation suite completed in {total_validation_time:.1f} seconds")
            
            return self.validation_results
            
        except Exception as e:
            logger.error(f"❌ Validation suite failed: {e}")
            self.validation_results['error'] = str(e)
            return self.validation_results
    
    def _generate_executive_summary(self):
        """Generate executive summary for stakeholders"""
        validations = self.validation_results['validations']
        
        # Extract key metrics from each validation
        current_perf = validations.get('current_performance', {}).get('summary', {})
        aws_sim = validations.get('aws_simulation', {}).get('simulation_summary', {})
        deployment = validations.get('deployment_validation', {}).get('summary', {})
        
        # Current environment assessment
        current_score = current_perf.get('overall_score', 0)
        current_grade = current_perf.get('grade', 'N/A')
        
        # Migration readiness assessment
        aws_readiness_score = validations.get('aws_simulation', {}).get('migration_readiness', {}).get('readiness_score', 0)
        deployment_readiness_score = deployment.get('readiness_score', 0)
        
        # Calculate overall migration readiness
        overall_readiness = (aws_readiness_score + deployment_readiness_score) / 2
        
        # Expected improvements
        performance_improvements = aws_sim.get('performance_improvements', {})
        cost_analysis = aws_sim.get('cost_analysis', {})
        
        # Risk assessment
        deployment_risk = deployment.get('risk_level', 'Unknown')
        
        # Migration timeline
        deployment_timeline = deployment.get('deployment_timeline', {}).get('total_estimated_time', '2-3 hours')
        
        self.validation_results['executive_summary'] = {
            'migration_recommendation': self._get_migration_recommendation(overall_readiness),
            'current_environment_grade': f"{current_score:.1f}/100 ({current_grade})",
            'migration_readiness_score': f"{overall_readiness:.1f}/100",
            'expected_improvements': {
                'response_time': performance_improvements.get('response_time_improvement', '40-60% faster'),
                'database_performance': performance_improvements.get('database_performance', '50-70% faster'),
                'concurrent_capacity': performance_improvements.get('concurrent_capacity', '200-300% increase'),
                'uptime': performance_improvements.get('uptime_improvement', '99.9% SLA')
            },
            'cost_impact': {
                'current_monthly_cost': f"${cost_analysis.get('current_replit_estimated_monthly', 50)}",
                'aws_monthly_cost': f"${cost_analysis.get('aws_estimated_monthly', {}).get('total', 192)}",
                'monthly_increase': f"${cost_analysis.get('cost_increase_monthly', 142)}",
                'roi_justification': 'Improved performance, reliability, and scalability'
            },
            'migration_timeline': deployment_timeline,
            'risk_assessment': deployment_risk,
            'key_benefits': [
                'Dedicated infrastructure resources',
                'Auto-scaling capabilities', 
                'Global CDN for improved international performance',
                'Enterprise-grade monitoring and alerting',
                'Automated backup and disaster recovery',
                'Zero-downtime deployments'
            ]
        }
    
    def _get_migration_recommendation(self, readiness_score: float) -> str:
        """Get migration recommendation based on readiness score"""
        if readiness_score >= 85:
            return "✅ RECOMMENDED - Proceed with migration"
        elif readiness_score >= 70:
            return "⚠️ CONDITIONAL - Address minor issues before migration"  
        elif readiness_score >= 50:
            return "🔧 NEEDS WORK - Significant preparation required"
        else:
            return "❌ NOT RECOMMENDED - Major issues must be resolved"
    
    def _generate_detailed_analysis(self):
        """Generate detailed technical analysis"""
        validations = self.validation_results['validations']
        
        # Performance analysis
        current_perf = validations.get('current_performance', {})
        perf_tests = current_perf.get('tests', {})
        
        health_checks = perf_tests.get('health_checks', {})
        load_tests = perf_tests.get('load_tests', {})
        database_perf = perf_tests.get('database', {})
        
        # AWS simulation analysis
        aws_sim = validations.get('aws_simulation', {})
        aws_components = aws_sim.get('components', {})
        
        # Deployment analysis
        deployment_val = validations.get('deployment_validation', {})
        deployment_validations = deployment_val.get('validations', {})
        
        self.validation_results['detailed_analysis'] = {
            'current_performance_analysis': {
                'health_endpoints': {
                    'available_endpoints': health_checks.get('successful_endpoints', 0),
                    'total_tested': health_checks.get('total_endpoints', 0),
                    'avg_response_time_ms': health_checks.get('avg_response_time_ms', 0),
                    'status': '✅ Healthy' if health_checks.get('all_healthy') else '⚠️ Needs attention'
                },
                'load_testing': {
                    'overall_grade': load_tests.get('overall_performance', {}).get('grade', 'N/A'),
                    'total_requests_tested': load_tests.get('overall_performance', {}).get('total_requests_tested', 0),
                    'average_success_rate': f"{load_tests.get('overall_performance', {}).get('average_success_rate', 0):.1f}%",
                    'performance_bottlenecks': self._identify_performance_bottlenecks(load_tests)
                },
                'database_performance': {
                    'connection_time_ms': database_perf.get('connection_time_ms', 0),
                    'query_performance': database_perf.get('performance_score', 0),
                    'optimization_needed': database_perf.get('performance_score', 0) < 80
                }
            },
            'aws_infrastructure_analysis': {
                'ecs_configuration': aws_components.get('ecs', {}).get('validation', {}),
                'load_balancer_setup': aws_components.get('alb', {}).get('validation', {}),
                'database_optimization': aws_components.get('rds', {}).get('validation', {}),
                'cdn_configuration': aws_components.get('cloudfront', {}).get('validation', {}),
                'cache_setup': aws_components.get('elasticache', {}).get('validation', {})
            },
            'deployment_readiness_analysis': {
                'blue_environment': deployment_validations.get('blue_environment', {}).get('overall_healthy', False),
                'application_consistency': deployment_validations.get('application_consistency', {}).get('consistency_score', 0),
                'traffic_shifting': deployment_validations.get('traffic_shift', {}).get('ready_for_production_shift', False),
                'rollback_procedures': deployment_validations.get('rollback_procedures', {}).get('rollback_ready', False)
            },
            'risk_mitigation_strategies': self._generate_risk_mitigation_strategies()
        }
    
    def _identify_performance_bottlenecks(self, load_tests: Dict) -> List[str]:
        """Identify performance bottlenecks from load test results"""
        bottlenecks = []
        
        results = load_tests.get('results', {})
        for endpoint, result in results.items():
            if isinstance(result, dict) and 'response_times' in result:
                response_times = result['response_times']
                avg_ms = response_times.get('avg_ms', 0)
                p95_ms = response_times.get('p95_ms', 0)
                
                if avg_ms > 500:
                    bottlenecks.append(f"High average response time for {endpoint}: {avg_ms:.1f}ms")
                
                if p95_ms > 1000:
                    bottlenecks.append(f"High P95 response time for {endpoint}: {p95_ms:.1f}ms")
                    
                success_rate = result.get('success_rate', 100)
                if success_rate < 95:
                    bottlenecks.append(f"Low success rate for {endpoint}: {success_rate:.1f}%")
        
        if not bottlenecks:
            bottlenecks.append("No significant performance bottlenecks identified")
        
        return bottlenecks
    
    def _generate_risk_mitigation_strategies(self) -> List[str]:
        """Generate risk mitigation strategies"""
        return [
            "🛡️ Implement comprehensive health checks across all AWS components",
            "📊 Set up real-time monitoring with CloudWatch and custom dashboards",
            "🚨 Configure automated alerts for key performance metrics",
            "🔄 Maintain blue environment as immediate rollback option",
            "💾 Implement automated database backups with point-in-time recovery",
            "🧪 Conduct final staging environment validation before go-live",
            "👥 Ensure 24/7 technical support availability during migration window",
            "📋 Prepare detailed runbooks for common operational scenarios"
        ]
    
    def _generate_migration_roadmap(self):
        """Generate detailed migration roadmap"""
        validations = self.validation_results['validations']
        
        # Determine migration phases based on validation results
        aws_readiness = validations.get('aws_simulation', {}).get('migration_readiness', {}).get('readiness_score', 0)
        deployment_readiness = validations.get('deployment_validation', {}).get('summary', {}).get('readiness_score', 0)
        
        # Pre-migration tasks
        pre_migration_tasks = self._generate_pre_migration_tasks(aws_readiness)
        
        # Migration execution phases
        migration_phases = self._generate_migration_phases()
        
        # Post-migration tasks
        post_migration_tasks = self._generate_post_migration_tasks()
        
        # Success criteria
        success_criteria = self._generate_success_criteria()
        
        self.validation_results['migration_roadmap'] = {
            'migration_readiness_assessment': {
                'aws_infrastructure_readiness': f"{aws_readiness:.1f}%",
                'deployment_process_readiness': f"{deployment_readiness:.1f}%",
                'overall_readiness': f"{(aws_readiness + deployment_readiness) / 2:.1f}%"
            },
            'pre_migration_tasks': pre_migration_tasks,
            'migration_execution_phases': migration_phases,
            'post_migration_tasks': post_migration_tasks,
            'success_criteria': success_criteria,
            'rollback_procedures': {
                'trigger_conditions': [
                    'Health check failures > 5 minutes',
                    'Error rate > 5% for 3 minutes',
                    'Response time degradation > 100% increase',
                    'Database connectivity issues'
                ],
                'rollback_steps': [
                    'Immediate traffic routing back to blue environment',
                    'Validate blue environment health',
                    'Investigate and document issues',
                    'Plan remediation for next attempt'
                ],
                'estimated_rollback_time': '3-5 minutes'
            }
        }
    
    def _generate_pre_migration_tasks(self, readiness_score: float) -> List[Dict[str, Any]]:
        """Generate pre-migration task list"""
        tasks = [
            {
                'task': 'Final infrastructure validation',
                'duration': '2 hours',
                'owner': 'DevOps Team',
                'critical': True,
                'description': 'Validate all AWS resources are properly configured and accessible'
            },
            {
                'task': 'Database backup and validation',
                'duration': '1 hour',
                'owner': 'Database Team',
                'critical': True,
                'description': 'Create full backup and validate restoration procedures'
            },
            {
                'task': 'Team briefing and role assignment',
                'duration': '30 minutes',
                'owner': 'Project Manager',
                'critical': True,
                'description': 'Brief all team members on procedures and assign responsibilities'
            },
            {
                'task': 'Monitoring and alerting setup',
                'duration': '1 hour',
                'owner': 'DevOps Team',
                'critical': True,
                'description': 'Ensure all monitoring is configured and tested'
            }
        ]
        
        # Add conditional tasks based on readiness score
        if readiness_score < 85:
            tasks.append({
                'task': 'Address identified readiness gaps',
                'duration': '2-4 hours',
                'owner': 'Development Team',
                'critical': True,
                'description': 'Resolve any issues identified in validation'
            })
        
        return tasks
    
    def _generate_migration_phases(self) -> List[Dict[str, Any]]:
        """Generate migration execution phases"""
        return [
            {
                'phase': 'Phase 1: Green Environment Deployment',
                'duration': '15 minutes',
                'activities': [
                    'Deploy application to AWS (green environment)',
                    'Run health checks on green environment',
                    'Validate database connectivity',
                    'Verify all endpoints respond correctly'
                ]
            },
            {
                'phase': 'Phase 2: Initial Traffic Routing (10%)',
                'duration': '10 minutes',
                'activities': [
                    'Route 10% of traffic to green environment',
                    'Monitor key performance metrics',
                    'Validate error rates remain acceptable',
                    'Check response time improvements'
                ]
            },
            {
                'phase': 'Phase 3: Gradual Traffic Increase (25%)',
                'duration': '15 minutes', 
                'activities': [
                    'Increase traffic to 25%',
                    'Monitor system performance under increased load',
                    'Validate database performance',
                    'Check CDN cache hit rates'
                ]
            },
            {
                'phase': 'Phase 4: Majority Traffic Routing (50%)',
                'duration': '20 minutes',
                'activities': [
                    'Route 50% of traffic to green environment',
                    'Monitor all system metrics closely',
                    'Validate auto-scaling functionality',
                    'Check application performance'
                ]
            },
            {
                'phase': 'Phase 5: Complete Migration (100%)',
                'duration': '20 minutes',
                'activities': [
                    'Route 100% of traffic to green environment',
                    'Comprehensive system validation',
                    'Performance baseline establishment',
                    'Final health check validation'
                ]
            },
            {
                'phase': 'Phase 6: Blue Environment Decommission',
                'duration': '30 minutes',
                'activities': [
                    'Monitor green environment for 30 minutes',
                    'Validate all systems stable',
                    'Document migration completion',
                    'Schedule blue environment cleanup (24h later)'
                ]
            }
        ]
    
    def _generate_post_migration_tasks(self) -> List[Dict[str, Any]]:
        """Generate post-migration tasks"""
        return [
            {
                'task': 'Performance baseline establishment',
                'duration': '1 hour',
                'timeline': 'Immediate',
                'description': 'Establish new performance baselines for monitoring'
            },
            {
                'task': 'User acceptance testing',
                'duration': '4 hours',
                'timeline': 'Day 1',
                'description': 'Conduct thorough user testing of all functionality'
            },
            {
                'task': 'Performance optimization review',
                'duration': '2 hours',
                'timeline': 'Week 1',
                'description': 'Analyze performance data and identify optimization opportunities'
            },
            {
                'task': 'Cost optimization analysis',
                'duration': '2 hours',
                'timeline': 'Week 2',
                'description': 'Review AWS usage and optimize costs'
            },
            {
                'task': 'Documentation update',
                'duration': '4 hours',
                'timeline': 'Week 2',
                'description': 'Update all technical documentation with new AWS architecture'
            },
            {
                'task': 'Team training on AWS operations',
                'duration': '8 hours',
                'timeline': 'Week 3',
                'description': 'Train team on AWS-specific operations and troubleshooting'
            }
        ]
    
    def _generate_success_criteria(self) -> Dict[str, Any]:
        """Generate success criteria for migration"""
        return {
            'performance_criteria': {
                'response_time_improvement': 'At least 30% improvement in average response times',
                'error_rate': 'Error rate < 0.1% over 24-hour period',
                'uptime': '99.9% uptime SLA maintained',
                'database_performance': 'Database query times improved by at least 40%'
            },
            'functional_criteria': {
                'all_endpoints_working': 'All API endpoints returning expected responses',
                'user_authentication': 'Login and session management working correctly',
                'data_integrity': 'All data accessible and consistent',
                'application_features': 'All application features working as expected'
            },
            'operational_criteria': {
                'monitoring_active': 'All monitoring and alerting systems operational',
                'logging_functional': 'Application logs properly collected and accessible',
                'backup_verified': 'Database backups completing successfully',
                'auto_scaling_working': 'Auto-scaling responding appropriately to load'
            },
            'business_criteria': {
                'user_satisfaction': 'No increase in support tickets or user complaints',
                'performance_improvement': 'Users report improved application performance',
                'global_accessibility': 'Improved performance for international users',
                'cost_within_budget': 'AWS costs within approved budget parameters'
            }
        }
    
    def print_comprehensive_report(self):
        """Print comprehensive migration validation report"""
        print("\n" + "="*100)
        print("🎯 COMPREHENSIVE AWS MIGRATION VALIDATION REPORT")
        print("="*100)
        
        exec_summary = self.validation_results.get('executive_summary', {})
        
        # Executive Summary
        print(f"\n📊 EXECUTIVE SUMMARY")
        print("-" * 50)
        print(f"Migration Recommendation: {exec_summary.get('migration_recommendation', 'N/A')}")
        print(f"Current Environment Grade: {exec_summary.get('current_environment_grade', 'N/A')}")
        print(f"Migration Readiness Score: {exec_summary.get('migration_readiness_score', 'N/A')}")
        print(f"Estimated Migration Time: {exec_summary.get('migration_timeline', 'N/A')}")
        print(f"Risk Assessment: {exec_summary.get('risk_assessment', 'N/A')}")
        
        # Expected Improvements
        print(f"\n🚀 EXPECTED IMPROVEMENTS")
        print("-" * 50)
        improvements = exec_summary.get('expected_improvements', {})
        for metric, improvement in improvements.items():
            print(f"  {metric.replace('_', ' ').title()}: {improvement}")
        
        # Cost Impact
        print(f"\n💰 COST ANALYSIS")
        print("-" * 50)
        cost = exec_summary.get('cost_impact', {})
        for cost_item, amount in cost.items():
            print(f"  {cost_item.replace('_', ' ').title()}: {amount}")
        
        # Key Benefits
        print(f"\n✨ KEY BENEFITS")
        print("-" * 50)
        benefits = exec_summary.get('key_benefits', [])
        for benefit in benefits:
            print(f"  • {benefit}")
        
        # Migration Roadmap Summary
        roadmap = self.validation_results.get('migration_roadmap', {})
        readiness = roadmap.get('migration_readiness_assessment', {})
        
        print(f"\n📋 MIGRATION READINESS")
        print("-" * 50)
        print(f"AWS Infrastructure Readiness: {readiness.get('aws_infrastructure_readiness', 'N/A')}")
        print(f"Deployment Process Readiness: {readiness.get('deployment_process_readiness', 'N/A')}")
        print(f"Overall Readiness: {readiness.get('overall_readiness', 'N/A')}")
        
        # Critical Pre-Migration Tasks
        print(f"\n⚠️ CRITICAL PRE-MIGRATION TASKS")
        print("-" * 50)
        pre_tasks = roadmap.get('pre_migration_tasks', [])
        for task in pre_tasks:
            if task.get('critical', False):
                print(f"  • {task.get('task', 'N/A')} ({task.get('duration', 'N/A')})")
        
        # Success Criteria Summary
        print(f"\n🎯 KEY SUCCESS CRITERIA")
        print("-" * 50)
        success = roadmap.get('success_criteria', {})
        perf_criteria = success.get('performance_criteria', {})
        for criterion, requirement in perf_criteria.items():
            print(f"  • {criterion.replace('_', ' ').title()}: {requirement}")
        
        print("\n" + "="*100)
        print(f"Report generated on: {self.validation_results.get('validation_timestamp', 'N/A')}")
        print(f"Total validation time: {self.validation_results.get('total_validation_time_seconds', 0):.1f} seconds")
        print("="*100)
    
    def save_comprehensive_report(self, filename: str = None):
        """Save comprehensive report to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"comprehensive_migration_validation_report_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.validation_results, f, indent=2, default=str)
            
            logger.info(f"📄 Comprehensive report saved to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Failed to save comprehensive report: {e}")
            return None
    
    def generate_executive_powerpoint_summary(self, filename: str = None):
        """Generate executive summary in text format suitable for presentations"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"executive_migration_summary_{timestamp}.txt"
        
        exec_summary = self.validation_results.get('executive_summary', {})
        roadmap = self.validation_results.get('migration_roadmap', {})
        
        try:
            with open(filename, 'w') as f:
                f.write("AWS MIGRATION - EXECUTIVE SUMMARY\n")
                f.write("=" * 50 + "\n\n")
                
                f.write("RECOMMENDATION\n")
                f.write("-" * 20 + "\n")
                f.write(f"{exec_summary.get('migration_recommendation', 'N/A')}\n\n")
                
                f.write("CURRENT STATE\n")
                f.write("-" * 20 + "\n")
                f.write(f"Performance Grade: {exec_summary.get('current_environment_grade', 'N/A')}\n")
                f.write(f"Migration Readiness: {exec_summary.get('migration_readiness_score', 'N/A')}\n\n")
                
                f.write("EXPECTED BENEFITS\n")
                f.write("-" * 20 + "\n")
                improvements = exec_summary.get('expected_improvements', {})
                for metric, improvement in improvements.items():
                    f.write(f"• {metric.replace('_', ' ').title()}: {improvement}\n")
                f.write("\n")
                
                f.write("COST IMPACT\n")
                f.write("-" * 20 + "\n")
                cost = exec_summary.get('cost_impact', {})
                f.write(f"Current: {cost.get('current_monthly_cost', 'N/A')}\n")
                f.write(f"AWS: {cost.get('aws_monthly_cost', 'N/A')}\n")
                f.write(f"Increase: {cost.get('monthly_increase', 'N/A')}\n")
                f.write(f"ROI: {cost.get('roi_justification', 'N/A')}\n\n")
                
                f.write("TIMELINE & RISK\n")
                f.write("-" * 20 + "\n")
                f.write(f"Migration Time: {exec_summary.get('migration_timeline', 'N/A')}\n")
                f.write(f"Risk Level: {exec_summary.get('risk_assessment', 'N/A')}\n\n")
                
                f.write("KEY NEXT STEPS\n")
                f.write("-" * 20 + "\n")
                pre_tasks = roadmap.get('pre_migration_tasks', [])[:3]  # Top 3 tasks
                for i, task in enumerate(pre_tasks, 1):
                    f.write(f"{i}. {task.get('task', 'N/A')} ({task.get('duration', 'N/A')})\n")
            
            logger.info(f"📄 Executive summary saved to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Failed to save executive summary: {e}")
            return None


async def main():
    """Main comprehensive validation execution"""
    print("🎯 Starting Comprehensive AWS Migration Validation Suite")
    print("This will run all validation components and generate a complete migration report\n")
    
    # Create comprehensive validator
    validator = ComprehensiveMigrationValidator()
    
    # Run complete validation suite
    results = await validator.run_complete_validation_suite()
    
    # Print comprehensive report
    validator.print_comprehensive_report()
    
    # Save reports
    comprehensive_report_file = validator.save_comprehensive_report()
    executive_summary_file = validator.generate_executive_powerpoint_summary()
    
    print(f"\n✅ Comprehensive validation complete!")
    print(f"📄 Full Report: {comprehensive_report_file}")
    print(f"📊 Executive Summary: {executive_summary_file}")
    
    return results


if __name__ == "__main__":
    # Run the comprehensive validation
    results = asyncio.run(main())