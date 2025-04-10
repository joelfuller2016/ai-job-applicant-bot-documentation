# AI Job Applicant Bot - Component Architecture

This document outlines the detailed architecture of the AI Job Applicant Bot system, showing how different components interact with each other and the data flow throughout the application.

## System Architecture Overview

The AI Job Applicant Bot follows a modular architecture with clearly defined interfaces between components. This design allows for independent development, testing, and maintenance of each component while ensuring seamless integration.

```
┌───────────────────┐        ┌──────────────────┐        ┌───────────────────┐
│                   │        │                  │        │                   │
│  User Interface   │◄─────►│  Core Services   │◄─────►│   Data Storage    │
│                   │        │                  │        │                   │
└───────────────────┘        └──────────────────┘        └───────────────────┘
      │                              │                           │
      │                              │                           │
      │                              │                           │
      ▼                              ▼                           ▼
┌───────────────────┐        ┌──────────────────┐        ┌───────────────────┐
│                   │        │                  │        │                   │
│  AI/ML Services   │◄─────►│ External Services │◄─────►│   Authentication  │
│                   │        │                  │        │                   │
└───────────────────┘        └──────────────────┘        └───────────────────┘
```

## Component Details and Interactions

### 1. User Interface Layer

#### 1.1 Streamlit UI (`ui/app.py`)
- Entry point for the web-based user interface
- Renders different pages based on user navigation
- Manages session state and user context
- Interacts with backend services through API calls

#### 1.2 UI Components
- `resume_pages.py`: Resume upload, viewing, and enhancement
- `job_pages.py`: Job search and filtering interface
- `applicator_pages.py`: Application tracking and submission
- `dashboard_pages.py`: Analytics and visualization
- `settings_pages.py`: Configuration and preferences
- `auth_pages.py`: User authentication flows

#### 1.3 Console Interface (`automation/console_runner.py`)
- Command-line interface for headless operation
- Provides progress reporting and status updates
- Supports batch job processing and scheduled execution

### 2. Core Services Layer

#### 2.1 Main Orchestrator (Future Implementation)
- Coordinates all components and workflows
- Manages the overall job application process
- Handles error recovery and state management
- Implements event-based communication between components

#### 2.2 Job Search Engine (`automation/job_search.py`)
- Interfaces with job board APIs
- Implements search algorithms for different platforms
- Handles filtering, pagination, and data normalization
- Manages job database persistence

#### 2.3 Application Engine (`automation/applicator.py`)
- Manages the job application process workflow
- Handles form detection and filling
- Supports resume upload and cover letter attachment
- Collects evidence and screenshots of application steps

#### 2.4 Resume Manager (`resume/parser.py`, `resume/matcher.py`)
- Extracts structured data from various resume formats
- Implements resume-to-job matching algorithms
- Calculates match scores and relevance metrics

#### 2.5 Cover Letter Generator (`cover_letters/generator.py`)
- Creates personalized cover letters
- Uses templates and job-specific information
- Supports various output formats

### 3. Data Storage Layer

#### 3.1 Local Database (`utils/local_db.py`)
- Manages persistent storage of application data
- Implements schema for users, jobs, applications, and results
- Provides backup and restoration capabilities
- Supports data migration and version control

#### 3.2 File Storage
- Handles storage of resume files, cover letters, and other documents
- Implements secure access control
- Provides versioning and history tracking

### 4. AI/ML Services Layer

#### 4.1 Resume Enhancement (`utils/resume_enhancer.py`)
- Improves parsed resume data using AI
- Generates suggestions for improvement
- Fills missing values and normalizes content

#### 4.2 ML Pipeline (`utils/ml_pipeline.py`)
- Implements machine learning models for various features
- Handles model training, prediction, and evaluation
- Supports continuous learning and improvement

#### 4.3 Semantic Matching (`utils/semantic_matcher.py`)
- Provides semantic similarity functions for text comparison
- Used for matching job descriptions with resumes
- Implements entity recognition for skills extraction

### 5. External Services Layer

#### 5.1 Browser Automation (`automation/ai_browser.py`, `automation/puppeteer_browser.py`)
- Provides browser automation for interacting with job websites
- Implements form detection and filling
- Handles navigation and document uploads
- Supports both visible and headless operation

#### 5.2 Job Board APIs
- Interfaces with external job board APIs
- Handles authentication and rate limiting
- Normalizes data from different sources

### 6. Authentication Layer

#### 6.1 User Authentication (`utils/local_auth.py`, `ui/auth_utils.py`)
- Manages user registration and login
- Implements secure credential storage
- Provides session management and token validation

## Data Flow

### Resume Upload and Enhancement Flow
1. User uploads resume via UI (`resume_pages.py`)
2. Resume is processed by `ResumeParser` to extract structured data
3. Extracted data is enhanced by `ResumeEnhancer` using AI
4. Enhanced resume data is stored in the database by `LocalDB`
5. User is presented with enhancement suggestions and visualization

### Job Search Flow
1. User enters search criteria via UI (`job_pages.py`)
2. `JobSearchManager` coordinates search across multiple job boards
3. Search results are filtered and normalized
4. Job data is stored in the database
5. User is presented with search results and match scores

### Application Flow
1. User selects jobs to apply for via UI
2. `ApplicationEngine` coordinates the application process
3. Browser automation opens job listings and fills applications
4. Cover letters are generated by `CoverLetterGenerator`
5. Application status is updated in the database
6. User is presented with application status and evidence

## Component Dependencies

```
┌───────────────────┐
│                   │
│  UI Components    │─────────►┌──────────────────┐
│                   │          │                  │
└───────────────────┘          │  Job Search      │
                               │  Engine          │
┌───────────────────┐          │                  │
│                   │          └──────────────────┘
│  Resume Parser    │────┐              │
│                   │    │              │
└───────────────────┘    │              ▼
        │                │      ┌──────────────────┐
        ▼                │      │                  │
┌───────────────────┐    │      │  Application     │
│                   │    │      │  Engine          │
│  Resume Enhancer  │    │      │                  │
│                   │    │      └──────────────────┘
└───────────────────┘    │              │
        │                │              │
        ▼                ▼              ▼
┌───────────────────┐    ┌──────────────────┐
│                   │    │                  │
│  Local Database   │◄───│  Cover Letter    │
│                   │    │  Generator       │
└───────────────────┘    │                  │
        ▲                └──────────────────┘
        │
        │
┌───────────────────┐
│                   │
│  Authentication   │
│                   │
└───────────────────┘
```

## Technologies and Frameworks

### Backend
- Python 3.10+
- Async/await for non-blocking operations
- SQLite for embedded database (via `LocalDB`)
- ML libraries (scikit-learn, TensorFlow, etc.) for intelligence
- OCR libraries for resume parsing

### Frontend
- Streamlit for web UI
- Plotly/Matplotlib for data visualization
- Bootstrap for responsive design

### Automation
- Selenium/Puppeteer for browser automation
- BeautifulSoup for HTML parsing
- Requests for API access

### AI/ML
- OpenAI GPT models for text generation
- Hugging Face Transformers for NLP tasks
- Custom ML models for job matching

## Security Considerations

- Secure storage for credentials using encryption
- Token-based authentication for API access
- Parameter sanitization to prevent injection attacks
- Rate limiting for external APIs
- IP rotation for job boards that track usage
- Audit logging for security events

## Future Architecture Enhancements

### Microservices Architecture
- Split monolithic application into microservices
- Implement message queues for communication
- Support horizontal scaling for high loads

### Cloud Deployment
- Containerize components with Docker
- Deploy on cloud platforms (AWS, GCP, Azure)
- Implement CI/CD pipeline for continuous deployment

### Enterprise Features
- Multi-user support with role-based access control
- Team collaboration features
- Integration with enterprise HR systems

This architecture document provides a high-level overview of the system design and will be updated as the project evolves.