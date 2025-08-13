# TraceTrack Monitoring and Alerting Guide

## Overview
TraceTrack includes enterprise-grade monitoring and alerting capabilities to ensure your system can handle 50+ lakh bags and 1000+ concurrent users without breaking.

## 🚨 Alert Configuration

### Setting Up Alert Recipients

Alert recipients are configured in the `alert_config.py` file. You can set up three types of alerts:

#### 1. Email Alerts
To enable email alerts, set these environment variables:
```bash
ENABLE_EMAIL_ALERTS=true
SMTP_SERVER=smtp.gmail.com  # Your SMTP server
SMTP_PORT=587
ALERT_SENDER_EMAIL=alerts@yourcompany.com
ALERT_SENDER_PASSWORD=your_app_password
```

Then modify `alert_config.py` to add recipients:
```python
'email': {
    'critical': ['admin@company.com', 'ops-team@company.com'],
    'warning': ['tech-lead@company.com'],
    'info': ['monitoring@company.com']
}
```

#### 2. SMS Alerts (Critical Only)
For SMS alerts via Twilio, set:
```bash
ENABLE_SMS_ALERTS=true
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+1234567890
```

Add phone numbers in `alert_config.py`:
```python
'sms': {
    'critical': ['+1234567890', '+0987654321']
}
```

#### 3. Webhook Alerts (Slack/Discord)
Add webhook URLs in `alert_config.py`:
```python
'webhook': {
    'critical': ['https://hooks.slack.com/services/YOUR/WEBHOOK/URL'],
    'warning': ['https://discord.com/api/webhooks/YOUR/WEBHOOK']
}
```

## 📊 Analytics Dashboard

### Accessing the Dashboard
1. Log in as an admin user
2. Navigate to: `/analytics/dashboard`
3. The dashboard shows real-time metrics and alerts

### Dashboard Sections

#### System Metrics
- CPU Usage
- Memory Usage
- Disk Usage
- Active Database Connections

#### Performance Metrics
- Average Response Time
- Requests Per Minute (RPM)
- Error Rate
- Cache Hit Rate

#### Business Metrics
- Total Bags
- Active Users
- Scans Today
- Bills Created Today

#### Recent Alerts
- Shows last 5 system alerts
- Color-coded by severity (Critical/Warning/Info)

## 🔔 Alert Thresholds

Current thresholds that trigger alerts:

| Metric | Warning | Critical |
|--------|---------|----------|
| Response Time | > 2 seconds | > 5 seconds |
| Error Rate | > 2% | > 5% |
| CPU Usage | > 75% | > 90% |
| Memory Usage | > 80% | > 90% |
| Concurrent Users | > 1500 | > 2000 |
| Database Connections | > 200 | > 240 |
| Cache Hit Rate | < 70% | < 50% |

## 🛠️ Monitoring Tools

### Real-time Monitoring API Endpoints

#### System Metrics
```
GET /analytics/api/metrics/realtime
```
Returns current system health and performance metrics.

#### Performance Metrics
```
GET /analytics/api/metrics/performance
```
Returns detailed performance analytics including response times and throughput.

#### Bag Metrics
```
GET /analytics/api/metrics/bags
```
Returns bag statistics and scanning performance.

#### User Metrics
```
GET /analytics/api/metrics/users
```
Returns user activity and session information.

#### Active Alerts
```
GET /analytics/api/alerts
```
Returns list of active system alerts.

## 🚀 Performance Optimization Features

### 1. Redis Caching
- Automatic failover to in-memory cache if Redis is unavailable
- TTL-based cache expiration
- Smart cache warming on startup

### 2. Database Connection Pooling
- Pool size: 100-250 connections
- Automatic connection recycling
- Health check on connection checkout

### 3. Query Optimization
- Automatic index creation
- Query result caching
- Bulk operations for large datasets

## 📈 Load Testing

### Running Load Tests
```bash
# Test with 1000 concurrent users
python extreme_load_test.py
```

### Expected Performance Targets
- Handle 1000+ concurrent users
- Process 5+ million bags
- Sub-second response times for searches
- 99.9% uptime

## 🔧 Troubleshooting

### Common Issues and Solutions

#### High Memory Usage
1. Check cache size: Clear if needed
2. Review database connection pool
3. Check for memory leaks in long-running processes

#### Slow Response Times
1. Check database query performance
2. Review cache hit rates
3. Check for blocking operations

#### Database Connection Errors
1. Verify connection pool settings
2. Check PostgreSQL max_connections
3. Review connection timeout settings

## 📝 Alert Response Procedures

### Critical Alerts
1. **Immediate Action Required**
2. Check system resources (CPU, Memory, Disk)
3. Review application logs for errors
4. Scale resources if needed
5. Notify technical team

### Warning Alerts
1. **Monitor closely**
2. Review trending metrics
3. Plan for scaling if trend continues
4. Schedule maintenance if needed

### Info Alerts
1. **Awareness only**
2. Log for future reference
3. Review during regular maintenance

## 🔐 Security Monitoring

### What's Monitored
- Failed login attempts
- Rate limit violations
- Suspicious scanning patterns
- Database query injection attempts

### Security Alert Responses
1. Review access logs
2. Check for patterns of abuse
3. Block suspicious IPs if needed
4. Update security rules

## 📊 Reporting

### Daily Reports Include
- System health summary
- Performance metrics
- Alert summary
- User activity
- Bag scanning statistics

### Weekly Reports Include
- Trend analysis
- Capacity planning recommendations
- Performance optimization suggestions
- Alert pattern analysis

## 🆘 Emergency Contacts

Configure in `alert_config.py`:
- **Critical Issues**: SMS + Email + Webhook
- **Warning Issues**: Email + Webhook
- **Info Issues**: Email only

## 🔄 Maintenance

### Regular Tasks
1. **Daily**: Review alerts and metrics
2. **Weekly**: Analyze trends and patterns
3. **Monthly**: Performance optimization review
4. **Quarterly**: Capacity planning

### Database Maintenance
```sql
-- Run weekly
VACUUM ANALYZE;

-- Run monthly
REINDEX DATABASE your_database_name;
```

## 📚 Additional Resources

- Performance Monitoring Code: `performance_monitoring.py`
- Alert Configuration: `alert_config.py`
- Database Scaling: `database_scaling.py`
- Cache Management: `enterprise_cache.py`
- Analytics Routes: `analytics_routes.py`

## Need Help?

If you encounter issues with monitoring or alerting:
1. Check this guide first
2. Review system logs
3. Contact your system administrator
4. For critical issues, alerts will be sent automatically to configured recipients

---

**Remember**: The monitoring system is designed to handle extreme loads. Trust the alerts - they indicate when action is needed.