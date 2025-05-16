# AI Job Applicant Bot - Project Documentation

## Overview

This repository contains comprehensive documentation for the AI Job Applicant Bot project. The AI Job Applicant Bot is an intelligent system designed to automate and optimize the job application process using machine learning, natural language processing, and browser automation.

## Documentation

The main documentation file is:

- [Project Documentation](project_documentation.md) - Comprehensive description of project structure, components, and implementation plan

## Core Components

The AI Job Applicant Bot consists of the following core components:

1. **Main Orchestrator** - Central brain of the system that coordinates all components
2. **Job Search Engine** - Engine that drives job discovery across multiple platforms
3. **Application Engine** - System that handles the actual job application process
4. **Resume Parser** - AI-powered resume parsing system
5. **Cover Letter Generator** - AI-driven personalized cover letter creation
6. **Database Manager** - Comprehensive storage solution
7. **Console Runner** - Command-line interface for headless operation
8. **Streamlit UI** - Comprehensive graphical interface
9. **Additional Utilities** - Supporting components

## Key Features

- Intelligent job search across multiple job boards
- Resume matching and scoring against job requirements
- Automated application form filling
- Cover letter generation with GPT models
- ML-powered insights and recommendations
- Application tracking and analytics

## Implementation Plan

The implementation is organized into three phases:

1. **Phase 1: Data Layer & Core Functionality**
   - Database Implementation
   - Resume Processing
   - Job Search Engine

2. **Phase 2: Intelligence & Integration**
   - Main Orchestrator
   - Application Engine
   - AI Integration

3. **Phase 3: User Experience & Deployment**
   - Streamlit UI Enhancement
   - Security & Performance
   - Testing & Documentation

For detailed information on each component and the implementation plan, please refer to the [Project Documentation](project_documentation.md).
## Running the Streamlit UI

A minimal Streamlit interface is included under `ui/app.py`. To launch the UI locally or in GitHub Codespaces:

```bash
pip install -r requirements.txt
streamlit run ui/app.py
```

Codespaces will forward the default port (8501) so you can open the app directly in your browser, including on mobile devices.
