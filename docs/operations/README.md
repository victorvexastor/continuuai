# Operations

**Production-oriented**: Running and maintaining ContinuuAI

This section contains everything you need to deploy, monitor, and maintain ContinuuAI in production environments.

---

## Quick Reference

### System Status
- **[Current Status](STATUS.md)** - Real-time system health and capabilities
- **[Health Checks](health-checks.md)** - Continuous validation commands
- **[Final Checklist](FINAL_CHECKLIST.md)** - Pre-deployment verification

### Day-to-Day Operations
- **[Operations Manual](OPERATIONS.md)** - Daily operational procedures
- **[Monitoring & Alerting](monitoring.md)** - Observability setup
- **[Backup & Recovery](backup-recovery.md)** - DR procedures
- **[Security Hardening](security-hardening.md)** - Production security

---

## Runbooks

Emergency procedures for common incidents:

### Critical Incidents
- **[Incident Response](runbooks/incident-response.md)** - P0/P1 incident handling
- **[Service Outage](runbooks/service-outage.md)** - Complete system down
- **[Data Corruption](runbooks/data-corruption.md)** - Integrity issues

### Performance Issues
- **[Performance Degradation](runbooks/perf-degradation.md)** - Slow response times
- **[High Memory Usage](runbooks/high-memory.md)** - OOM scenarios
- **[Database Overload](runbooks/db-overload.md)** - Connection pool exhaustion

### Security Incidents
- **[Unauthorized Access](runbooks/unauthorized-access.md)** - ACL breach
- **[DDoS Attack](runbooks/ddos.md)** - Traffic spike handling
- **[Certificate Expiry](runbooks/cert-expiry.md)** - TLS renewal

---

## Operational Procedures

### Deployment
- [Rolling Deploy](procedures/rolling-deploy.md) - Zero-downtime updates
- [Rollback Procedure](procedures/rollback.md) - Emergency rollback
- [Database Migration](procedures/db-migration.md) - Schema changes

### Maintenance
- [Routine Maintenance](procedures/routine-maintenance.md) - Weekly/monthly tasks
- [Log Rotation](procedures/log-rotation.md) - Disk space management
- [Performance Tuning](procedures/perf-tuning.md) - Optimization

### Scaling
- [Horizontal Scaling](procedures/horizontal-scale.md) - Add more instances
- [Vertical Scaling](procedures/vertical-scale.md) - Increase resources
- [Database Scaling](procedures/db-scale.md) - Read replicas, sharding

---

## Monitoring & Observability

### Metrics
- **Key Performance Indicators (KPIs)**
  - P95 latency < 500ms
  - Availability > 99.9%
  - Error rate < 0.1%
- **[Metrics Reference](monitoring.md#metrics)** - All available metrics
- **[Dashboards](monitoring.md#dashboards)** - Grafana templates

### Logging
- **[Log Aggregation](monitoring.md#logging)** - Centralized logs
- **[Log Levels](monitoring.md#log-levels)** - Severity guidelines
- **[Audit Logs](monitoring.md#audit-logs)** - Security events

### Alerting
- **[Alert Configuration](monitoring.md#alerting)** - Alertmanager setup
- **[On-Call Procedures](runbooks/on-call.md)** - Response protocols
- **[Escalation Policy](runbooks/escalation.md)** - Incident escalation

---

## Pre-Deployment Checklist

Before deploying to production, complete:

- [ ] Run [Final Checklist](FINAL_CHECKLIST.md)
- [ ] Review [Security Hardening](security-hardening.md)
- [ ] Configure [Monitoring & Alerting](monitoring.md)
- [ ] Set up [Backup & Recovery](backup-recovery.md)
- [ ] Test [Incident Response](runbooks/incident-response.md)
- [ ] Document [Disaster Recovery Plan](backup-recovery.md#disaster-recovery)

---

## Support Levels

### Internal Operations Team
- **Response Time**: < 15 minutes (business hours)
- **Escalation**: ops@continuuai.com
- **Slack**: #ops-alerts

### External Commercial Support
- **Response Time**: < 4 hours (24/7)
- **Contact**: support@continuuai.com
- **Phone**: +1-555-SUPPORT

---

## Common Commands

### Health Check (30 seconds)
```bash
./scripts/smoke_test_all.sh
```

### Full Test Suite
```bash
./scripts/run_all_tests.sh
```

### Service Logs
```bash
docker compose logs -f retrieval
docker compose logs -f graph-deriver
```

### Database Status
```bash
docker exec $(docker ps -qf name=postgres) \
  psql -U continuuai -d continuuai \
  -c "SELECT COUNT(*) FROM evidence_span;"
```

### Debug Endpoints
```bash
curl http://localhost:8081/v1/health
curl http://localhost:8081/v1/debug/weights | jq .
```

---

## Operational Metrics

### Uptime Targets
- **Production**: 99.9% (< 43 minutes downtime/month)
- **Staging**: 99% (< 7 hours downtime/month)
- **Development**: Best effort

### Performance Targets
- **Query Latency**: P95 < 500ms, P99 < 1s
- **Throughput**: > 100 QPS per instance
- **Database**: Connection pool < 80% utilization

### Security Posture
- **Vulnerability Scans**: Weekly
- **Dependency Updates**: Monthly
- **Security Patches**: < 72 hours to apply

---

## Documentation Updates

Operations documentation is reviewed:
- **Monthly**: Routine procedures and runbooks
- **Quarterly**: Security hardening guidelines
- **After Incidents**: Runbook updates based on learnings

Last reviewed: 2025-12-15

---

**Operators Slack**: #continuuai-ops  
**On-Call Rotation**: [PagerDuty Schedule](https://continuuai.pagerduty.com)
