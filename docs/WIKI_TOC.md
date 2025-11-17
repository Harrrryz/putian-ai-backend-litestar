# Project Wiki Table of Contents

## Core Documentation

### Project Overview & Architecture
### Getting Started Guide
### Development Setup & Environment

## Architecture & Design
### Domain-Driven Design Implementation
### Clean Architecture Principles
### Application Structure & Organization
### Advanced Alchemy Integration
### Dependency Injection System
### Async Architecture & Performance Patterns

## Configuration & Infrastructure

### Configuration Management System
    *   Environment-based Configuration
    *   AppSettings, DatabaseSettings, AISettings
    *   SMTP & Email Configuration
    *   S3 & File Storage Configuration
### Database Setup & Migrations
    *   PostgreSQL & SQLite Support
    *   Alembic Migration Management
    *   Connection Pooling Configuration
### Development Infrastructure
    *   Docker Development Setup
    *   Make Commands & Scripts

## Domain Modules
### Accounts Domain
    *   User Management System
    *   Authentication & Authorization
    *   Role-Based Access Control (RBAC)
    *   Email Verification & Password Reset
    *   OAuth Integration (GitHub)
    *   User Signals & Event Handling
### Todo Domain
    *   Todo CRUD Operations
    *   Tag Management System
    *   Importance Levels & Scheduling
    *   Todo Validation & Business Rules
### Todo Agents Domain
    *   AI Agent Architecture (OpenAI Agents)
    *   Agent Factory & Configuration
    *   Streaming Chat Implementation (SSE)
    *   Tool System & Universal Tools
    *   Context Management & History
    *   System Instructions & Prompts
### Agent Sessions Domain
    *   Chat Session Management
    *   Message History Persistence
    *   Session Lifecycle Events
### Quota Domain
    *   User Usage Quota Model
    *   Rate Limiting Service
    *   Usage Statistics & Tracking
### System Domain
    *   Health Checks & Monitoring
    *   System Utilities & Helpers

## AI Integration
### OpenAI Agents Framework
    *   Agent Implementation Guide
    *   Tool Definition System
    *   Tool Implementation Patterns
    *   Argument Processing & Validation
### AI Service Providers
    *   VolcEngine Doubao Integration
    *   GLM Model Support
    *   Model Configuration & Switching
### Streaming & Real-time Features
    *   Server-Sent Events (SSE)
    *   Real-time Chat Implementation
    *   Event-Driven Agent Responses
### Agent Testing & Development
    *   SimpleEnvironment for Testing
    *   Agent Tool Validation
    *   Debug & Logging Strategies

## API Documentation
### REST API Reference
    *   Accounts & User Management API
    *   Todo Management API
    *   Todo Agents & Chat API
    *   Agent Sessions API
    *   System Health & Monitoring API
### OpenAPI Documentation
    *   Schema Generation
    *   API Testing & Validation
### Authentication & Security
    *   JWT Authentication Implementation
    *   OAuth2 Flow Integration
    *   Authorization Guards & Middleware
    *   CSRF Protection

## Database & Models
### Data Models & ORM Mapping
    *   User Model & Relationships
    *   Todo Model & Tagging System
    *   AgentSession & SessionMessage Models
    *   Role & UserRole Models
    *   EmailToken & PasswordToken Models
    *   Quota & Usage Models
### Repository Pattern
    *   Advanced Alchemy Repository Usage
    *   Custom Repository Implementations
    *   Query Optimization Strategies
### Database Migration Guide
    *   Creating & Applying Migrations
    *   Schema Evolution Best Practices

## Business Logic & Services
### Service Layer Architecture
    *   Todo Service Implementation
    *   AI Agent Service & Tool Management
    *   User Management Service
    *   Agent Session Service
    *   Quota Management Service
### Business Rules & Validation
    *   Pydantic Schema Validation
    *   Custom Validators & Constraints
    *   Error Handling & Exceptions

## Security & Compliance
### Authentication Systems
    *   Password Hashing (Argon2)
    *   Token-based Authentication
    *   Session Management
### Security Best Practices
    *   Input Validation & Sanitization
    *   SQL Injection Prevention
    *   XSS Protection
    *   CORS Configuration
### Email Security
    *   Email Verification Workflows
    *   Password Reset Security
    *   SMTP Configuration & TLS

## Development & Testing
### Development Workflow
    *   Code Style & Quality (Ruff, Mypy, Pyright)
    *   Pre-commit Hooks Configuration
    *   Git Workflow & Branching
### Testing Strategy
    *   Unit Testing Guide
    *   Integration Testing Patterns
    *   Database Testing (pytest-databases)
    *   Test Fixtures & Factories
    *   Test Coverage & Reporting
### CLI Tools & Commands
    *   User Management CLI
    *   Database Migration Commands
    *   Development Utilities

## Deployment & Operations
### Production Deployment
    *   Docker Containerization
    *   Environment Configuration
    *   Database Setup for Production
### Monitoring & Logging
    *   Structured Logging (structlog)
    *   Health Checks & Metrics
    *   Error Tracking & Alerting
### Performance Optimization
    *   Async Performance Patterns
    *   Database Query Optimization
    *   Caching Strategies
    *   Connection Pool Management

## Advanced Topics
### Event-Driven Architecture
    *   Signal System Implementation
    *   Event Handling Patterns
    *   Async Event Processing
### Advanced Patterns
    *   Middleware Development
    *   Plugin Architecture
    *   Custom Dependency Injection
    *   Advanced Repository Patterns
### Performance & Scalability
    *   Async/Await Best Practices
    *   Memory Management
    *   Database Connection Strategies
    *   Load Balancing Considerations