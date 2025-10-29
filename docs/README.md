# Project Documentation

## Overview

This directory contains all technical and project documentation following a spec-driven development approach. Each document serves a specific purpose in guiding development and maintaining context for both human developers and AI coding agents.

## Documentation Index

### Planning & Requirements
- **[REQUIREMENTS.md](REQUIREMENTS.md)** - User stories, functional requirements, and acceptance criteria
- **[DESIGN.md](DESIGN.md)** - System architecture, technology decisions, design patterns, and key architectural choices

### Technical Specifications
- **[DATA_MODELS.md](DATA_MODELS.md)** - Database schemas, message formats, and data structures
- **[API_REFERENCE.md](API_REFERENCE.md)** - API endpoints, contracts, and integration points
- **[OBSERVABILITY.md](OBSERVABILITY.md)** - Monitoring, logging, and observability strategy

### Quality & Operations
- **[TESTING.md](TESTING.md)** - Testing strategy, test scenarios, and coverage requirements
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment procedures, environments, and infrastructure setup

### Implementation Tracking
- **[IMPLEMENTATION.md](IMPLEMENTATION.md)** - High-level implementation plan and detailed task checklist
- **[IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md)** - Development journal with progress notes and decisions (maintained by agents)
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common errors, issues faced, and solutions (updated after confirmation)

## Document Usage Guidelines

### For Developers
1. Start with **REQUIREMENTS.md** to understand what we're building
2. Review **DESIGN.md** for architectural context
3. Consult specific technical docs (DATA_MODELS, API_REFERENCE) as needed
4. Check **TROUBLESHOOTING.md** when encountering issues
5. Track progress in **IMPLEMENTATION.md** and log decisions in **IMPLEMENTATION_LOG.md**

### For AI Agents
See root-level `AGENTS.md` for detailed instructions on when and how to update each document.

## Document Maintenance

- **User-controlled**: REQUIREMENTS, DESIGN, DATA_MODELS, API_REFERENCE, OBSERVABILITY, TESTING, DEPLOYMENT, IMPLEMENTATION
- **Agent-maintained**: IMPLEMENTATION_LOG (freely updated with progress)
- **Collaborative**: TROUBLESHOOTING (agents suggest, user confirms before adding)

## Navigation

All documents are in Markdown format with consistent structure:
- Use `##` for main sections
- Use tables for structured data
- Use code blocks with language tags for examples
- Cross-reference related documents using relative links
