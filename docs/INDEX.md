# ContinuuAI Documentation

**Version**: 1.0.0  
**Last Updated**: 2025-12-15  
**Status**: Production Ready

---

## 📚 Documentation Structure

This documentation follows the [Diátaxis framework](https://diataxis.fr/) for systematic documentation architecture.

### Quick Navigation

| Section | Purpose | When to use |
|---------|---------|-------------|
| [Tutorials](#tutorials) | Learning-oriented | First time users, getting started |
| [How-To Guides](#how-to-guides) | Task-oriented | Solving specific problems |
| [Reference](#reference) | Information-oriented | Looking up technical details |
| [Explanation](#explanation) | Understanding-oriented | Deep dives and context |
| [Operations](#operations) | Running in production | Deployment and maintenance |
| [Development](#development) | Contributing | Building and testing |
| [Changelog](#changelog) | Version history | What changed and when |

---

## 🎓 Tutorials

**Learning-oriented**: Step-by-step lessons for beginners

- [Getting Started](tutorials/GETTING_STARTED.md) - First-time setup and basic usage
- [Your First Query](tutorials/first-query.md) - Query ContinuuAI for decisions
- [Ingesting Decisions](tutorials/ingest-decisions.md) - Add organizational knowledge
- [Understanding the Graph](tutorials/graph-basics.md) - How ContinuuAI builds continuity

**Start here** if you're new to ContinuuAI.

---

## 🛠️ How-To Guides

**Task-oriented**: Recipes for specific tasks

### Deployment
- [Deploy to Production](how-to/deploy-production.md) - Production deployment guide
- [Configure ACL Policies](how-to/configure-acl.md) - Access control setup
- [Scale for Load](how-to/scale.md) - Horizontal and vertical scaling

### Integration
- [Integrate with Slack](how-to/slack-integration.md) - Slack bot setup
- [CI/CD Pipeline](how-to/cicd.md) - Automated deployment
- [Custom Embeddings](how-to/custom-embeddings.md) - Use your own embedding models

### Troubleshooting
- [Debug Retrieval Issues](how-to/debug-retrieval.md) - Query performance tuning
- [Fix Migration Errors](how-to/fix-migrations.md) - Schema migration recovery
- [Investigate Slow Queries](how-to/slow-queries.md) - Performance troubleshooting

**Use these** when you know what you want to do.

---

## 📖 Reference

**Information-oriented**: Technical specifications and API docs

### API Documentation
- [API Reference](reference/API_REFERENCE.md) - Complete API specification
- [Response Contract Schema](../schemas/response-contract.v1.json) - JSON Schema validation
- [SQL Schema Reference](reference/sql-schema.md) - Database structure

### Technical Specifications
- [Technical Design](reference/TECHNICAL_DESIGN.md) - System architecture
- [Test Suite Reference](reference/TEST_SUITE.md) - Complete test documentation
- [Configuration Reference](reference/config.md) - All environment variables
- [Security Model](reference/security.md) - ACL and authentication

### Code Reference
- [Retrieval Service API](reference/retrieval-service.md) - Internal service docs
- [Graph Deriver Logic](reference/graph-deriver.md) - Graph extraction rules

**Look here** for facts and technical details.

---

## 💡 Explanation

**Understanding-oriented**: Concepts, design decisions, and context

- [ContinuuAI Vision](explanation/CONTINUUAI_VISION.md) - Why we built this, our promise
- [Continuity vs RAG](explanation/continuity-vs-rag.md) - How ContinuuAI differs
- [Evidence-First Design](explanation/evidence-first.md) - Design philosophy
- [Graph Architecture](explanation/graph-architecture.md) - Why graphs for continuity
- [Hybrid Retrieval](explanation/hybrid-retrieval.md) - Vector + lexical + graph scoring

**Read these** to understand the "why" behind ContinuuAI.

---

## 🚀 Operations

**Production-oriented**: Running and maintaining ContinuuAI

### Operational Guides
- [Operations Manual](operations/OPERATIONS.md) - Day-to-day operations
- [Current Status](operations/STATUS.md) - System status and health
- [Monitoring & Alerting](operations/monitoring.md) - Observability setup
- [Backup & Recovery](operations/backup-recovery.md) - DR procedures
- [Security Hardening](operations/security-hardening.md) - Production security

### Runbooks
- [Incident Response](operations/runbooks/incident-response.md) - Emergency procedures
- [Performance Degradation](operations/runbooks/perf-degradation.md) - Slow response fixes
- [Data Corruption](operations/runbooks/data-corruption.md) - Integrity issues

### Verification
- [Final Checklist](operations/FINAL_CHECKLIST.md) - Pre-deployment validation
- [Health Checks](operations/health-checks.md) - Continuous validation

**Operators** live here.

---

## 🔧 Development

**Contributor-oriented**: Building and testing ContinuuAI

### Setup
- [Local Development](development/LOCAL.md) - Dev environment setup
- [Testing Guide](development/testing.md) - Running and writing tests
- [Contributing Guidelines](development/CONTRIBUTING.md) - How to contribute
- [Code Standards](development/code-standards.md) - Style and patterns

### Architecture
- [Service Architecture](development/services.md) - Microservices breakdown
- [Database Design](development/database-design.md) - Schema patterns
- [CI/CD Pipeline](development/cicd-pipeline.md) - Build and deploy automation

### Archive
- [Development Archive](development/archive/) - Historical planning docs

**Developers** start here.

---

## 📋 Changelog

**Historical**: What changed and when

### Major Releases
- [v1.0.0 - Test Suite Complete](changelog/IMPLEMENTATION_COMPLETE.md) - 2025-12-15
- [Observability Enhancements](changelog/OBSERVABILITY_COMPLETE.md) - 2025-12-15
- [Accountability Layer](changelog/ACCOUNTABILITY_COMPLETE.md) - Previous

### Version History
- [CHANGELOG.md](changelog/CHANGELOG.md) - Semantic versioning log

**Track changes** over time.

---

## 🎯 Common Workflows

### For New Users
1. Read [Getting Started](tutorials/GETTING_STARTED.md)
2. Try [Your First Query](tutorials/first-query.md)
3. Understand [The Vision](explanation/CONTINUUAI_VISION.md)

### For Developers
1. Set up [Local Environment](development/LOCAL.md)
2. Read [Technical Design](reference/TECHNICAL_DESIGN.md)
3. Review [Test Suite](reference/TEST_SUITE.md)

### For Operators
1. Review [Operations Manual](operations/OPERATIONS.md)
2. Check [Current Status](operations/STATUS.md)
3. Run [Final Checklist](operations/FINAL_CHECKLIST.md)

### For Decision Makers
1. Read [ContinuuAI Vision](explanation/CONTINUUAI_VISION.md)
2. Review [Sales Materials](../docs/sales-marketing/)
3. Check [Changelog](changelog/IMPLEMENTATION_COMPLETE.md)

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourorg/continuuai/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourorg/continuuai/discussions)
- **Security**: security@continuuai.com
- **Commercial**: sales@continuuai.com

---

## 🔗 External Links

- [Project Repository](https://github.com/yourorg/continuuai)
- [Community Slack](https://continuuai.slack.com)
- [Docker Hub](https://hub.docker.com/r/continuuai)
- [Status Page](https://status.continuuai.com)

---

**License**: MIT (see [LICENSE](../LICENSE))  
**Documentation License**: CC BY 4.0
