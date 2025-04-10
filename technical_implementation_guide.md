# AI Job Applicant Bot - Technical Implementation Guide

This guide provides detailed technical steps for implementing solutions to the critical issues identified in the project analysis. It focuses on actionable tasks with code examples and implementation strategies.

## 1. Database Architecture Implementation

### Current Status
The project uses a file-based approach in `utils/local_db.py` rather than a proper SQLite implementation as originally planned.

### Implementation Steps

#### 1.1 Create a Proper SQLite Database Manager

Create a new file `utils/database_manager.py` with a robust SQLite implementation:

```python
import sqlite3
import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import threading
import time

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Comprehensive SQLite database manager for the AI Job Applicant Bot.
    Implements proper connection pooling, transaction support, and schema management.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    # Singleton pattern to ensure only one database manager instance
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                cls._instance.initialized = False
            return cls._instance
    
    def __init__(self, db_path: str = "db/application_data.db", max_connections: int = 5):
        if self.initialized:
            return
            
        self.db_path = Path(db_path)
        self.max_connections = max_connections
        self.connection_pool = []
        self.initialized = True
        
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database and create tables if not exists
        self._initialize_database()
    
    def _initialize_database(self):
        """Create database schema if it doesn't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    settings TEXT
                )
            ''')
            
            # Create resumes table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS resumes (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    parsed_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # Create jobs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT,
                    job_board TEXT NOT NULL,
                    url TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'new',
                    match_score REAL DEFAULT 0,
                    applied_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # Create applications table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS applications (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    resume_id TEXT NOT NULL,
                    cover_letter_path TEXT,
                    status TEXT DEFAULT 'pending',
                    applied_at TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    response_received_at TIMESTAMP,
                    response_type TEXT,
                    notes TEXT,
                    FOREIGN KEY (job_id) REFERENCES jobs(id),
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (resume_id) REFERENCES resumes(id)
                )
            ''')
            
            # Create sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # Create tasks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    result TEXT,
                    error TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            ''')
            
            conn.commit()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a connection from the pool or create a new one if needed."""
        # Try to get an existing connection from the pool
        if self.connection_pool:
            conn = self.connection_pool.pop()
            try:
                # Test the connection
                conn.execute("SELECT 1")
                return conn
            except sqlite3.Error:
                # Connection is invalid, create a new one
                pass
        
        # Create new connection
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _release_connection(self, conn: sqlite3.Connection):
        """Return a connection to the pool."""
        if len(self.connection_pool) < self.max_connections:
            self.connection_pool.append(conn)
        else:
            conn.close()
    
    def execute_query(self, query: str, params: tuple = (), fetchone: bool = False):
        """Execute a query and return results."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
                conn.commit()
                return cursor.lastrowid
            
            if fetchone:
                return cursor.fetchone()
            return cursor.fetchall()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            self._release_connection(conn)
    
    def execute_transaction(self, queries):
        """Execute multiple queries in a transaction."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            for query, params in queries:
                cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction error: {str(e)}")
            raise
        finally:
            self._release_connection(conn)
    
    # User management methods
    def create_user(self, user_id: str, email: str, password_hash: str) -> bool:
        """Create a new user in the database."""
        try:
            self.execute_query(
                "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
                (user_id, email, password_hash)
            )
            return True
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return False
    
    def get_user(self, user_id: str = None, email: str = None) -> Optional[Dict]:
        """Get user by ID or email."""
        if user_id:
            row = self.execute_query(
                "SELECT * FROM users WHERE id = ?", 
                (user_id,), 
                fetchone=True
            )
        elif email:
            row = self.execute_query(
                "SELECT * FROM users WHERE email = ?", 
                (email,), 
                fetchone=True
            )
        else:
            return None
        
        if row:
            return dict(row)
        return None
    
    # Resume management methods
    def save_resume(self, resume_id: str, user_id: str, file_path: str, parsed_data: Dict) -> bool:
        """Save a resume to the database."""
        try:
            self.execute_query(
                """INSERT INTO resumes (id, user_id, file_path, parsed_data) 
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET 
                   file_path = ?, parsed_data = ?, last_updated = CURRENT_TIMESTAMP""",
                (resume_id, user_id, file_path, json.dumps(parsed_data), 
                 file_path, json.dumps(parsed_data))
            )
            return True
        except Exception as e:
            logger.error(f"Error saving resume: {str(e)}")
            return False
    
    def get_resume(self, resume_id: str) -> Optional[Dict]:
        """Get a resume by ID."""
        row = self.execute_query(
            "SELECT * FROM resumes WHERE id = ?", 
            (resume_id,), 
            fetchone=True
        )
        
        if row:
            result = dict(row)
            if result.get('parsed_data'):
                result['parsed_data'] = json.loads(result['parsed_data'])
            return result
        return None
    
    def get_user_resumes(self, user_id: str) -> List[Dict]:
        """Get all resumes for a user."""
        rows = self.execute_query(
            "SELECT * FROM resumes WHERE user_id = ? ORDER BY last_updated DESC", 
            (user_id,)
        )
        
        results = []
        for row in rows:
            result = dict(row)
            if result.get('parsed_data'):
                result['parsed_data'] = json.loads(result['parsed_data'])
            results.append(result)
        
        return results
    
    # Job management methods
    def save_job(self, job_data: Dict) -> bool:
        """Save a job to the database."""
        try:
            columns = ', '.join(job_data.keys())
            placeholders = ', '.join(['?'] * len(job_data))
            values = tuple(job_data.values())
            
            self.execute_query(
                f"INSERT INTO jobs ({columns}) VALUES ({placeholders})",
                values
            )
            return True
        except Exception as e:
            logger.error(f"Error saving job: {str(e)}")
            return False
    
    def update_job(self, job_id: str, update_data: Dict) -> bool:
        """Update a job in the database."""
        try:
            set_clause = ', '.join([f"{k} = ?" for k in update_data.keys()])
            values = tuple(update_data.values()) + (job_id,)
            
            self.execute_query(
                f"UPDATE jobs SET {set_clause}, last_updated = CURRENT_TIMESTAMP WHERE id = ?",
                values
            )
            return True
        except Exception as e:
            logger.error(f"Error updating job: {str(e)}")
            return False
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get a job by ID."""
        row = self.execute_query(
            "SELECT * FROM jobs WHERE id = ?", 
            (job_id,), 
            fetchone=True
        )
        
        if row:
            return dict(row)
        return None
    
    def get_user_jobs(self, user_id: str, status: str = None, limit: int = None) -> List[Dict]:
        """Get jobs for a user, optionally filtered by status."""
        query = "SELECT * FROM jobs WHERE user_id = ?"
        params = [user_id]
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        rows = self.execute_query(query, tuple(params))
        return [dict(row) for row in rows]
    
    # Application management methods
    def save_application(self, application_data: Dict) -> bool:
        """Save an application to the database."""
        try:
            columns = ', '.join(application_data.keys())
            placeholders = ', '.join(['?'] * len(application_data))
            values = tuple(application_data.values())
            
            self.execute_query(
                f"INSERT INTO applications ({columns}) VALUES ({placeholders})",
                values
            )
            return True
        except Exception as e:
            logger.error(f"Error saving application: {str(e)}")
            return False
    
    def update_application(self, application_id: str, update_data: Dict) -> bool:
        """Update an application in the database."""
        try:
            set_clause = ', '.join([f"{k} = ?" for k in update_data.keys()])
            values = tuple(update_data.values()) + (application_id,)
            
            self.execute_query(
                f"UPDATE applications SET {set_clause}, last_updated = CURRENT_TIMESTAMP WHERE id = ?",
                values
            )
            return True
        except Exception as e:
            logger.error(f"Error updating application: {str(e)}")
            return False
    
    def get_application(self, application_id: str) -> Optional[Dict]:
        """Get an application by ID."""
        row = self.execute_query(
            "SELECT * FROM applications WHERE id = ?", 
            (application_id,), 
            fetchone=True
        )
        
        if row:
            return dict(row)
        return None
    
    def get_job_applications(self, job_id: str) -> List[Dict]:
        """Get all applications for a job."""
        rows = self.execute_query(
            "SELECT * FROM applications WHERE job_id = ?", 
            (job_id,)
        )
        return [dict(row) for row in rows]
    
    def get_user_applications(self, user_id: str, status: str = None) -> List[Dict]:
        """Get applications for a user, optionally filtered by status."""
        query = "SELECT * FROM applications WHERE user_id = ?"
        params = [user_id]
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY applied_at DESC"
        
        rows = self.execute_query(query, tuple(params))
        return [dict(row) for row in rows]
    
    # Session and task management methods
    def create_session(self, session_id: str, user_id: str) -> bool:
        """Create a new session."""
        try:
            self.execute_query(
                "INSERT INTO sessions (id, user_id) VALUES (?, ?)",
                (session_id, user_id)
            )
            return True
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            return False
    
    def end_session(self, session_id: str) -> bool:
        """End a session."""
        try:
            self.execute_query(
                "UPDATE sessions SET end_time = CURRENT_TIMESTAMP, status = 'completed' WHERE id = ?",
                (session_id,)
            )
            return True
        except Exception as e:
            logger.error(f"Error ending session: {str(e)}")
            return False
    
    def create_task(self, task_id: str, session_id: str, task_type: str) -> bool:
        """Create a new task."""
        try:
            self.execute_query(
                "INSERT INTO tasks (id, session_id, task_type) VALUES (?, ?, ?)",
                (task_id, session_id, task_type)
            )
            return True
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            return False
    
    def update_task(self, task_id: str, status: str, result: str = None, error: str = None) -> bool:
        """Update a task's status."""
        try:
            if status == 'started':
                self.execute_query(
                    "UPDATE tasks SET status = ?, start_time = CURRENT_TIMESTAMP WHERE id = ?",
                    (status, task_id)
                )
            elif status in ('completed', 'failed'):
                self.execute_query(
                    "UPDATE tasks SET status = ?, end_time = CURRENT_TIMESTAMP, result = ?, error = ? WHERE id = ?",
                    (status, result, error, task_id)
                )
            else:
                self.execute_query(
                    "UPDATE tasks SET status = ? WHERE id = ?",
                    (status, task_id)
                )
            return True
        except Exception as e:
            logger.error(f"Error updating task: {str(e)}")
            return False
    
    # Database maintenance methods
    def backup_database(self, backup_path: str = None) -> str:
        """Create a backup of the database."""
        if backup_path is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_path = f"db/backups/backup_{timestamp}.db"
        
        backup_dir = os.path.dirname(backup_path)
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        conn = self._get_connection()
        try:
            # Create a backup connection
            backup_conn = sqlite3.connect(backup_path)
            conn.backup(backup_conn)
            backup_conn.close()
            return backup_path
        except Exception as e:
            logger.error(f"Backup error: {str(e)}")
            raise
        finally:
            self._release_connection(conn)
    
    def restore_database(self, backup_path: str) -> bool:
        """Restore the database from a backup."""
        if not os.path.exists(backup_path):
            logger.error(f"Backup file not found: {backup_path}")
            return False
        
        # Close all connections in the pool
        for conn in self.connection_pool:
            conn.close()
        self.connection_pool = []
        
        try:
            # Create a new connection to the backup
            backup_conn = sqlite3.connect(backup_path)
            
            # Create a new connection to the target
            target_conn = sqlite3.connect(self.db_path)
            
            # Perform the restore
            backup_conn.backup(target_conn)
            
            # Close connections
            backup_conn.close()
            target_conn.close()
            
            return True
        except Exception as e:
            logger.error(f"Restore error: {str(e)}")
            return False
    
    def vacuum_database(self) -> bool:
        """Optimize the database by rebuilding it."""
        conn = self._get_connection()
        try:
            conn.execute("VACUUM")
            return True
        except Exception as e:
            logger.error(f"Vacuum error: {str(e)}")
            return False
        finally:
            self._release_connection(conn)
```

#### 1.2 Migration Script for Existing Data

Create a migration script to transfer data from the current file-based system:

```python
# migrate_to_sql.py
import json
import os
import uuid
from pathlib import Path
from utils.local_db import LocalDB
from utils.database_manager import DatabaseManager

def migrate_data():
    """Migrate data from file-based storage to SQLite database."""
    # Initialize both database systems
    local_db = LocalDB()
    db_manager = DatabaseManager()
    
    # Get all users from local DB
    users_path = "db/users"
    if not os.path.exists(users_path):
        print("No users directory found. Nothing to migrate.")
        return
    
    user_ids = [f.stem for f in Path(users_path).glob("*.json")]
    
    for user_id in user_ids:
        # Get user data
        user_data = local_db.get_data(f"users/{user_id}")
        if not user_data:
            continue
        
        # Create user in new database
        db_manager.create_user(
            user_id=user_id,
            email=user_data.get('email', f"{user_id}@example.com"),
            password_hash=user_data.get('password_hash', '')
        )
        
        # Migrate resumes
        user_resumes = local_db.get_data(f"resumes/{user_id}")
        if user_resumes:
            for resume_id, resume_data in user_resumes.items():
                db_manager.save_resume(
                    resume_id=resume_id,
                    user_id=user_id,
                    file_path=resume_data.get('file_path', ''),
                    parsed_data=resume_data.get('parsed_data', {})
                )
        
        # Migrate jobs
        user_jobs = local_db.get_data(f"jobs/{user_id}")
        if user_jobs:
            for job_id, job_data in user_jobs.items():
                job_record = {
                    'id': job_id,
                    'user_id': user_id,
                    'title': job_data.get('title', ''),
                    'company': job_data.get('company', ''),
                    'location': job_data.get('location', ''),
                    'job_board': job_data.get('job_board', ''),
                    'url': job_data.get('url', ''),
                    'description': job_data.get('description', ''),
                    'status': job_data.get('status', 'new'),
                    'match_score': job_data.get('match_score', 0),
                    'notes': json.dumps(job_data.get('notes', {}))
                }
                db_manager.save_job(job_record)
        
        # Migrate applications
        user_applications = local_db.get_data(f"applications/{user_id}")
        if user_applications:
            for app_id, app_data in user_applications.items():
                app_record = {
                    'id': app_id,
                    'job_id': app_data.get('job_id', ''),
                    'user_id': user_id,
                    'resume_id': app_data.get('resume_id', ''),
                    'cover_letter_path': app_data.get('cover_letter_path', ''),
                    'status': app_data.get('status', 'pending'),
                    'notes': json.dumps(app_data.get('notes', {}))
                }
                db_manager.save_application(app_record)
    
    print("Migration completed successfully.")

if __name__ == "__main__":
    migrate_data()
```

#### 1.3 Update References to Use the New Database Manager

Modify other modules to use the new DatabaseManager instead of LocalDB:

```python
# Example: Update job_search.py to use the new database manager
from utils.database_manager import DatabaseManager

class JobSearchManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_manager = JobAPIManager(config)
        self.db_manager = DatabaseManager()  # Use the new database manager
        
    def _load_jobs_database(self) -> Dict[str, JobPost]:
        # Get jobs from the database using the new manager
        user_id = self.config.get('user_id')
        jobs_data = self.db_manager.get_user_jobs(user_id)
        
        jobs = {}
        for job_data in jobs_data:
            job = JobPost.from_dict(job_data)
            jobs[job.id] = job
        
        return jobs
```

## 2. Browser Automation Compatibility Resolution

### Current Status
The project has dual browser automation systems: a standard approach in `ai_browser.py` and a Puppeteer-based approach in `puppeteer_browser.py`.

### Implementation Steps

#### 2.1 Create a Common Browser Interface

Create an abstract base class that defines the interface for browser automation:

```python
# automation/browser_interface.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

class BrowserInterface(ABC):
    """
    Abstract base class defining the interface for browser automation implementations.
    All browser automation classes should implement this interface.
    """
    
    @abstractmethod
    def initialize(self, headless: bool = False) -> bool:
        """Initialize the browser."""
        pass
    
    @abstractmethod
    def close(self) -> bool:
        """Close the browser and release resources."""
        pass
    
    @abstractmethod
    def navigate(self, url: str, wait_for_load: bool = True) -> bool:
        """Navigate to a URL."""
        pass
    
    @abstractmethod
    def is_element_present(self, selector: str, timeout: int = 10) -> bool:
        """Check if an element is present on the page."""
        pass
    
    @abstractmethod
    def wait_for_element(self, selector: str, timeout: int = 10) -> Any:
        """Wait for an element to appear on the page."""
        pass
    
    @abstractmethod
    def click(self, selector: str, wait_after: int = 1) -> bool:
        """Click on an element."""
        pass
    
    @abstractmethod
    def fill_text(self, selector: str, text: str) -> bool:
        """Fill text into an input field."""
        pass
    
    @abstractmethod
    def select_option(self, selector: str, value: str) -> bool:
        """Select an option from a dropdown."""
        pass
    
    @abstractmethod
    def upload_file(self, selector: str, file_path: Union[str, Path]) -> bool:
        """Upload a file using a file input."""
        pass
    
    @abstractmethod
    def get_text(self, selector: str) -> Optional[str]:
        """Get text content of an element."""
        pass
    
    @abstractmethod
    def get_attribute(self, selector: str, attribute: str) -> Optional[str]:
        """Get attribute value of an element."""
        pass
    
    @abstractmethod
    def get_current_url(self) -> str:
        """Get the current page URL."""
        pass
    
    @abstractmethod
    def execute_script(self, script: str, *args) -> Any:
        """Execute JavaScript in the browser context."""
        pass
    
    @abstractmethod
    def take_screenshot(self, file_path: Union[str, Path]) -> bool:
        """Take a screenshot of the current page."""
        pass
    
    @abstractmethod
    def find_elements(self, selector: str) -> List[Any]:
        """Find all elements matching a selector."""
        pass
    
    @abstractmethod
    def get_page_source(self) -> str:
        """Get the HTML source of the current page."""
        pass
    
    @abstractmethod
    def fill_form(self, form_data: Dict[str, str]) -> bool:
        """Fill a form with the provided data."""
        pass
    
    @abstractmethod
    def has_captcha(self) -> bool:
        """Detect if the page has a CAPTCHA."""
        pass
    
    @abstractmethod
    def solve_captcha(self) -> bool:
        """Attempt to solve a CAPTCHA if present."""
        pass
```

#### 2.2 Update Existing Browser Implementations to Use the Interface

Update `ai_browser.py` to implement the interface:

```python
# automation/ai_browser.py
from automation.browser_interface import BrowserInterface
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class AIBrowser(BrowserInterface):
    """
    Selenium-based browser automation implementation.
    Implements the BrowserInterface for standard compatibility.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.driver = None
        self.initialized = False
    
    def initialize(self, headless: bool = False) -> bool:
        """Initialize the Selenium WebDriver."""
        try:
            options = webdriver.ChromeOptions()
            
            if headless:
                options.add_argument('--headless')
            
            # Add anti-detection measures
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Add user agent if specified
            if 'user_agent' in self.config:
                options.add_argument(f'user-agent={self.config["user_agent"]}')
            
            # Initialize the WebDriver
            self.driver = webdriver.Chrome(options=options)
            
            # Set window size
            window_width = self.config.get('window_width', 1920)
            window_height = self.config.get('window_height', 1080)
            self.driver.set_window_size(window_width, window_height)
            
            # Hide WebDriver usage
            self.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            
            self.initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize browser: {str(e)}")
            return False
    
    def close(self) -> bool:
        """Close the browser and release resources."""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self.initialized = False
                return True
            except Exception as e:
                logger.error(f"Error closing browser: {str(e)}")
                return False
        return True
    
    def navigate(self, url: str, wait_for_load: bool = True) -> bool:
        """Navigate to a URL."""
        if not self.initialized:
            logger.error("Browser not initialized")
            return False
        
        try:
            self.driver.get(url)
            
            if wait_for_load:
                # Wait for page to load completely
                self.execute_script(
                    "return document.readyState === 'complete' || document.readyState === 'interactive'"
                )
                time.sleep(2)  # Additional wait for dynamic content
            
            return True
        except Exception as e:
            logger.error(f"Navigation error: {str(e)}")
            return False
    
    def is_element_present(self, selector: str, timeout: int = 10) -> bool:
        """Check if an element is present on the page."""
        if not self.initialized:
            return False
        
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return True
        except TimeoutException:
            return False
    
    def wait_for_element(self, selector: str, timeout: int = 10) -> Any:
        """Wait for an element to appear on the page."""
        if not self.initialized:
            return None
        
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return element
        except TimeoutException:
            logger.warning(f"Element not found: {selector}")
            return None
    
    def click(self, selector: str, wait_after: int = 1) -> bool:
        """Click on an element."""
        if not self.initialized:
            return False
        
        element = self.wait_for_element(selector)
        if not element:
            return False
        
        try:
            # Scroll element into view
            self.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(0.5)
            
            # Perform the click
            element.click()
            
            # Wait after click if specified
            if wait_after > 0:
                time.sleep(wait_after)
            
            return True
        except Exception as e:
            logger.error(f"Click error: {str(e)}")
            return False
    
    # Implementation of other methods follows the same pattern...
    # Each method ensures the browser is initialized and handles exceptions properly
```

#### 2.3 Create a Browser Factory

Implement a factory class to create the appropriate browser based on configuration:

```python
# automation/browser_factory.py
from typing import Dict, Any, Optional
from automation.browser_interface import BrowserInterface
from automation.ai_browser import AIBrowser
from automation.puppeteer_browser import PuppeteerBrowser
import logging

logger = logging.getLogger(__name__)

class BrowserFactory:
    """
    Factory class for creating browser automation instances.
    Provides a single point for browser selection and configuration.
    """
    
    @staticmethod
    def create_browser(browser_type: str = "standard", config: Optional[Dict[str, Any]] = None) -> Optional[BrowserInterface]:
        """
        Create a browser instance based on the specified type and configuration.
        
        Args:
            browser_type: Type of browser to create ("standard", "puppeteer", or "auto")
            config: Configuration dictionary for the browser
            
        Returns:
            A browser instance implementing BrowserInterface or None if creation fails
        """
        config = config or {}
        
        # Auto-select browser type if specified
        if browser_type == "auto":
            # Use Puppeteer for headless operation, standard otherwise
            browser_type = "puppeteer" if config.get("headless", False) else "standard"
        
        try:
            if browser_type == "standard":
                logger.info("Creating standard browser instance")
                return AIBrowser(config)
            elif browser_type == "puppeteer":
                logger.info("Creating Puppeteer browser instance")
                return PuppeteerBrowser(config)
            else:
                logger.error(f"Unknown browser type: {browser_type}")
                return None
        except Exception as e:
            logger.error(f"Failed to create browser: {str(e)}")
            return None
    
    @staticmethod
    def get_default_browser(config: Optional[Dict[str, Any]] = None) -> Optional[BrowserInterface]:
        """
        Create a browser with the default configuration.
        
        Args:
            config: Optional configuration to override defaults
            
        Returns:
            A browser instance implementing BrowserInterface
        """
        default_config = {
            "headless": False,
            "window_width": 1920,
            "window_height": 1080,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        if config:
            default_config.update(config)
        
        return BrowserFactory.create_browser("auto", default_config)
```

#### 2.4 Update Application Code to Use the Browser Factory

Modify the application engine to use the browser factory:

```python
# automation/applicator.py
from automation.browser_factory import BrowserFactory
from utils.database_manager import DatabaseManager
import logging

logger = logging.getLogger(__name__)

class ApplicationEngine:
    """
    Manages the job application process.
    Uses the browser factory to create appropriate browser instances.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db_manager = DatabaseManager()
        self.browser = None
    
    def initialize_browser(self):
        """Initialize the browser based on configuration."""
        browser_config = self.config.get("browser", {})
        browser_type = browser_config.get("type", "auto")
        
        self.browser = BrowserFactory.create_browser(browser_type, browser_config)
        
        if not self.browser:
            logger.error("Failed to initialize browser")
            return False
        
        return self.browser.initialize(browser_config.get("headless", False))
    
    def apply_to_job(self, job_id: str, resume_id: str) -> Dict[str, Any]:
        """Apply to a job using the specified resume."""
        # Get job and resume data
        job = self.db_manager.get_job(job_id)
        resume = self.db_manager.get_resume(resume_id)
        
        if not job or not resume:
            logger.error(f"Job or resume not found: job_id={job_id}, resume_id={resume_id}")
            return {"success": False, "error": "Job or resume not found"}
        
        # Initialize browser if needed
        if not self.browser or not getattr(self.browser, 'initialized', False):
            if not self.initialize_browser():
                return {"success": False, "error": "Failed to initialize browser"}
        
        # Application logic using the browser interface
        # This code remains the same regardless of browser implementation
        try:
            # Navigate to job page
            if not self.browser.navigate(job["url"]):
                return {"success": False, "error": "Failed to navigate to job page"}
            
            # Find and click apply button
            apply_button_selector = self._get_apply_button_selector(job["job_board"])
            if not self.browser.click(apply_button_selector):
                return {"success": False, "error": "Apply button not found"}
            
            # Fill application form
            form_data = self._prepare_form_data(job, resume)
            if not self.browser.fill_form(form_data):
                return {"success": False, "error": "Failed to fill application form"}
            
            # Upload resume if needed
            resume_upload_selector = self._get_resume_upload_selector(job["job_board"])
            if self.browser.is_element_present(resume_upload_selector):
                if not self.browser.upload_file(resume_upload_selector, resume["file_path"]):
                    return {"success": False, "error": "Failed to upload resume"}
            
            # Submit application
            submit_button_selector = self._get_submit_button_selector(job["job_board"])
            if not self.browser.click(submit_button_selector):
                return {"success": False, "error": "Submit button not found"}
            
            # Take screenshot for evidence
            screenshot_path = f"application_results/{job_id}_{resume_id}.png"
            self.browser.take_screenshot(screenshot_path)
            
            # Update job and application status
            self.db_manager.update_job(job_id, {"status": "applied"})
            
            # Create application record
            application_id = str(uuid.uuid4())
            self.db_manager.save_application({
                "id": application_id,
                "job_id": job_id,
                "user_id": job["user_id"],
                "resume_id": resume_id,
                "status": "submitted",
                "applied_at": "CURRENT_TIMESTAMP"
            })
            
            return {
                "success": True,
                "application_id": application_id,
                "screenshot": screenshot_path
            }
            
        except Exception as e:
            logger.error(f"Application error: {str(e)}")
            return {"success": False, "error": str(e)}
        finally:
            # Don't close the browser here - it may be reused for other applications
            pass
    
    def close_browser(self):
        """Close the browser and release resources."""
        if self.browser:
            self.browser.close()
            self.browser = None
    
    # Helper methods for different job boards
    def _get_apply_button_selector(self, job_board: str) -> str:
        """Get the CSS selector for the apply button based on job board."""
        selectors = {
            "linkedin": "button.jobs-apply-button",
            "indeed": ".indeed-apply-button",
            "glassdoor": ".gd-ui-button.applyButton",
            "ziprecruiter": ".job_apply",
            # Add more job boards as needed
        }
        
        return selectors.get(job_board.lower(), ".apply-button")
    
    def _get_resume_upload_selector(self, job_board: str) -> str:
        """Get the CSS selector for resume upload based on job board."""
        selectors = {
            "linkedin": "input[type='file'][name='resume']",
            "indeed": "#resume-upload-input",
            "glassdoor": "input[type='file'].resumeUpload",
            "ziprecruiter": "input[type='file'][name='resume']",
            # Add more job boards as needed
        }
        
        return selectors.get(job_board.lower(), "input[type='file'][name='resume']")
    
    def _get_submit_button_selector(self, job_board: str) -> str:
        """Get the CSS selector for submit button based on job board."""
        selectors = {
            "linkedin": "button[type='submit']",
            "indeed": "#form-action-submit",
            "glassdoor": "button.submit",
            "ziprecruiter": ".submit-application-button",
            # Add more job boards as needed
        }
        
        return selectors.get(job_board.lower(), "button[type='submit']")
    
    def _prepare_form_data(self, job: Dict[str, Any], resume: Dict[str, Any]) -> Dict[str, str]:
        """Prepare form data based on job and resume."""
        parsed_data = resume.get("parsed_data", {})
        
        form_data = {
            "name": parsed_data.get("contact_info", {}).get("name", ""),
            "email": parsed_data.get("contact_info", {}).get("email", ""),
            "phone": parsed_data.get("contact_info", {}).get("phone", ""),
            "location": parsed_data.get("contact_info", {}).get("location", ""),
            # Add more fields as needed
        }
        
        return form_data
```

## 3. API Dependency Risk Mitigation

### Current Status
The job search system depends on multiple external job board APIs with potential rate limits and availability issues.

### Implementation Steps

#### 3.1 Create a Robust API Client with Fallback Mechanisms

```python
# utils/api_client.py
import requests
import time
import logging
import json
from typing import Dict, Any, Optional, List, Callable
from functools import wraps
import random

logger = logging.getLogger(__name__)

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorator for retrying API requests with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds between retries
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except (requests.RequestException, ConnectionError) as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Max retries reached for {func.__name__}: {str(e)}")
                        raise
                    
                    # Calculate backoff delay with jitter
                    delay = base_delay * (2 ** (retries - 1)) + random.uniform(0, 0.5)
                    logger.warning(f"Retrying {func.__name__} in {delay:.2f}s (attempt {retries}/{max_retries})")
                    time.sleep(delay)
        return wrapper
    return decorator

class APIClient:
    """
    Robust API client with caching, retry logic, and fallback mechanisms.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.cache = {}
        self.cache_ttl = self.config.get("cache_ttl", 3600)  # Default 1 hour
        self.default_headers = {
            "User-Agent": self.config.get("user_agent", "AI Job Applicant Bot/1.0")
        }
    
    @retry_with_backoff(max_retries=3)
    def get(self, url: str, params: Optional[Dict[str, Any]] = None, 
            headers: Optional[Dict[str, str]] = None, cache: bool = True) -> Dict[str, Any]:
        """
        Perform a GET request with caching and retry logic.
        
        Args:
            url: The URL to request
            params: Query parameters for the request
            headers: Additional headers for the request
            cache: Whether to use cache for this request
            
        Returns:
            JSON response as dictionary
        """
        # Check cache first if enabled
        cache_key = self._get_cache_key(url, params)
        if cache and cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if time.time() < cache_entry["expires"]:
                logger.debug(f"Cache hit for {url}")
                return cache_entry["data"]
        
        # Prepare headers
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)
        
        # Make the request
        response = requests.get(url, params=params, headers=request_headers)
        response.raise_for_status()
        
        # Parse response
        data = response.json()
        
        # Update cache if enabled
        if cache:
            self.cache[cache_key] = {
                "data": data,
                "expires": time.time() + self.cache_ttl
            }
        
        return data
    
    @retry_with_backoff(max_retries=3)
    def post(self, url: str, data: Optional[Dict[str, Any]] = None, 
             json_data: Optional[Dict[str, Any]] = None, 
             headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Perform a POST request with retry logic.
        
        Args:
            url: The URL to request
            data: Form data for the request
            json_data: JSON data for the request
            headers: Additional headers for the request
            
        Returns:
            JSON response as dictionary
        """
        # Prepare headers
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)
        
        # Make the request
        response = requests.post(url, data=data, json=json_data, headers=request_headers)
        response.raise_for_status()
        
        # Parse response
        return response.json()
    
    def _get_cache_key(self, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate a unique cache key for a request."""
        if params:
            param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            return f"{url}?{param_str}"
        return url
    
    def clear_cache(self, url: Optional[str] = None):
        """
        Clear the request cache.
        
        Args:
            url: Optional URL to clear specific cache entry, or all if None
        """
        if url:
            # Clear specific URL entries
            keys_to_remove = [k for k in self.cache.keys() if k.startswith(url)]
            for key in keys_to_remove:
                del self.cache[key]
        else:
            # Clear entire cache
            self.cache = {}

class JobAPI:
    """
    Job board API client with fallback mechanisms.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_client = APIClient(config)
        self.api_keys = self._get_api_keys()
    
    def _get_api_keys(self) -> Dict[str, str]:
        """Get API keys from configuration."""
        return self.config.get("api_keys", {})
    
    def search_jobs(self, job_board: str, query: str, location: str, 
                    fallback: bool = True, **kwargs) -> List[Dict[str, Any]]:
        """
        Search for jobs using a specific job board API.
        
        Args:
            job_board: The job board to search (linkedin, indeed, etc.)
            query: Job search query
            location: Job location
            fallback: Whether to use fallback mechanisms if primary search fails
            **kwargs: Additional search parameters
            
        Returns:
            List of job listings
        """
        # Get job search method based on job board
        primary_search_method = getattr(self, f"search_{job_board}_jobs", None)
        
        try:
            # Try primary search method
            if primary_search_method:
                return primary_search_method(query, location, **kwargs)
            else:
                logger.warning(f"No search method for job board: {job_board}")
                
            # If we reach here, primary search failed or doesn't exist
            if fallback:
                logger.info(f"Using fallback for {job_board}")
                return self._fallback_search(job_board, query, location, **kwargs)
                
            return []
        except Exception as e:
            logger.error(f"Error searching {job_board}: {str(e)}")
            
            # Use fallback if enabled
            if fallback:
                logger.info(f"Using fallback after error for {job_board}")
                return self._fallback_search(job_board, query, location, **kwargs)
            
            return []
    
    def _fallback_search(self, job_board: str, query: str, location: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Fallback search mechanism when primary API fails.
        
        Strategy:
        1. Try alternative API endpoint if available
        2. Try web scraping if configured
        3. Try cached results if available
        4. Generate sample data as last resort
        """
        # Try alternative API endpoint first
        alt_search_method = getattr(self, f"search_{job_board}_alt", None)
        if alt_search_method:
            try:
                return alt_search_method(query, location, **kwargs)
            except Exception as e:
                logger.warning(f"Alternative API also failed: {str(e)}")
        
        # Try web scraping if configured
        if self.config.get("enable_scraping", False):
            try:
                return self._scrape_jobs(job_board, query, location, **kwargs)
            except Exception as e:
                logger.warning(f"Web scraping fallback failed: {str(e)}")
        
        # Check cache for older results
        cache_key = f"{job_board}_{query}_{location}"
        if cache_key in self.api_client.cache:
            logger.info("Using cached results as fallback")
            return self.api_client.cache[cache_key]["data"]
        
        # Last resort: generate sample data
        logger.warning("All fallbacks failed, using generated sample data")
        return self._generate_sample_jobs(query, location, count=kwargs.get("limit", 5))
    
    def _scrape_jobs(self, job_board: str, query: str, location: str, **kwargs) -> List[Dict[str, Any]]:
        """Web scraping fallback implementation."""
        # This would be implemented with a web scraping library
        # such as BeautifulSoup or Scrapy
        raise NotImplementedError("Web scraping not implemented yet")
    
    def _generate_sample_jobs(self, query: str, location: str, count: int = 5) -> List[Dict[str, Any]]:
        """Generate sample job data as last-resort fallback."""
        sample_jobs = []
        companies = ["TechCorp", "DataSystems", "InnovateTech", "CodeMasters", "DevHQ"]
        job_types = ["Full-time", "Contract", "Part-time"]
        
        for i in range(count):
            job_id = f"sample_{int(time.time())}_{i}"
            company = random.choice(companies)
            
            sample_jobs.append({
                "id": job_id,
                "title": f"{query.title()} Specialist",
                "company": company,
                "location": location,
                "description": f"This is a sample job for {query} in {location}. "
                               f"No real jobs were found due to API limitations.",
                "job_board": "sample",
                "url": f"https://example.com/jobs/{job_id}",
                "date_posted": "2023-01-01",
                "job_type": random.choice(job_types),
                "is_sample": True
            })
        
        return sample_jobs
    
    # Implementation of specific job board search methods
    def search_linkedin_jobs(self, query: str, location: str, **kwargs) -> List[Dict[str, Any]]:
        """Search LinkedIn jobs."""
        api_key = self.api_keys.get("linkedin")
        if not api_key:
            logger.warning("LinkedIn API key not found")
            return []
        
        url = "https://api.linkedin.com/v2/jobSearch"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        params = {
            "keywords": query,
            "location": location,
            "start": kwargs.get("offset", 0),
            "count": kwargs.get("limit", 10)
        }
        
        # Add optional parameters
        if "experience" in kwargs:
            params["experience"] = kwargs["experience"]
        
        response = self.api_client.get(url, params=params, headers=headers)
        return self._parse_linkedin_response(response)
    
    def _parse_linkedin_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse LinkedIn API response."""
        jobs = []
        
        for item in response.get("elements", []):
            job_data = {
                "id": item.get("entityUrn", "").split(":")[-1],
                "title": item.get("title", ""),
                "company": item.get("companyDetails", {}).get("name", ""),
                "location": item.get("locationName", ""),
                "description": item.get("description", {}).get("text", ""),
                "job_board": "linkedin",
                "url": f"https://www.linkedin.com/jobs/view/{item.get('entityUrn', '').split(':')[-1]}",
                "date_posted": item.get("listedAt", ""),
                "job_type": item.get("employmentStatus", "")
            }
            jobs.append(job_data)
        
        return jobs
    
    # Similar implementations for other job boards would follow
```

#### 3.2 Update Job Search Manager to Use the Robust API Client

```python
# automation/job_search.py
from utils.api_client import JobAPI
from utils.database_manager import DatabaseManager
import uuid
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class JobPost:
    """
    Represents a job listing with its attributes.
    """
    
    def __init__(self, title: str, company: str, location: str, job_board: str, url: str,
                 description: str = "", status: str = "new", match_score: float = 0,
                 job_id: Optional[str] = None):
        self.id = job_id or str(uuid.uuid4())
        self.title = title
        self.company = company
        self.location = location
        self.job_board = job_board
        self.url = url
        self.description = description
        self.status = status
        self.match_score = match_score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job post to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "job_board": self.job_board,
            "url": self.url,
            "description": self.description,
            "status": self.status,
            "match_score": self.match_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobPost':
        """Create job post from dictionary."""
        return cls(
            title=data.get("title", ""),
            company=data.get("company", ""),
            location=data.get("location", ""),
            job_board=data.get("job_board", ""),
            url=data.get("url", ""),
            description=data.get("description", ""),
            status=data.get("status", "new"),
            match_score=data.get("match_score", 0),
            job_id=data.get("id")
        )

class JobSearchManager:
    """
    Coordinates job search across multiple platforms.
    Uses the robust JobAPI client for resilient API access.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.job_api = JobAPI(config)
        self.db_manager = DatabaseManager()
        self.user_id = config.get("user_id")
    
    def search_job_board(self, job_board: str, job_title: str, location: str,
                        limit: int = 20) -> List[JobPost]:
        """
        Search for jobs on a specific job board.
        
        Args:
            job_board: Job board to search (linkedin, indeed, etc.)
            job_title: Job title to search for
            location: Location to search in
            limit: Maximum number of results to return
            
        Returns:
            List of JobPost objects
        """
        logger.info(f"Searching {job_board} for {job_title} in {location}")
        
        # Use the resilient API client with fallback mechanisms
        job_results = self.job_api.search_jobs(
            job_board=job_board,
            query=job_title,
            location=location,
            limit=limit,
            fallback=True  # Enable fallback mechanisms
        )
        
        # Convert to JobPost objects
        job_posts = []
        for job_data in job_results:
            job_post = JobPost(
                title=job_data.get("title", ""),
                company=job_data.get("company", ""),
                location=job_data.get("location", ""),
                job_board=job_data.get("job_board", job_board),
                url=job_data.get("url", ""),
                description=job_data.get("description", "")
            )
            
            # Skip if this is a sample job and samples should be ignored
            if job_data.get("is_sample") and not self.config.get("include_sample_jobs", False):
                continue
                
            job_posts.append(job_post)
            
            # Save to database if user is specified
            if self.user_id:
                job_dict = job_post.to_dict()
                job_dict["user_id"] = self.user_id
                self.db_manager.save_job(job_dict)
        
        logger.info(f"Found {len(job_posts)} jobs on {job_board}")
        return job_posts
    
    def search_all_job_boards(self, job_title: str, location: str, 
                             limit_per_board: int = 10) -> List[JobPost]:
        """
        Search for jobs across all configured job boards.
        
        Args:
            job_title: Job title to search for
            location: Location to search in
            limit_per_board: Maximum results per job board
            
        Returns:
            Combined list of JobPost objects from all boards
        """
        all_jobs = []
        job_boards = self.config.get("job_boards", ["linkedin", "indeed"])
        
        for job_board in job_boards:
            board_jobs = self.search_job_board(
                job_board=job_board,
                job_title=job_title,
                location=location,
                limit=limit_per_board
            )
            all_jobs.extend(board_jobs)
        
        return all_jobs
```

## 4. Security Implementation

### Current Status
The system requires storage of sensitive user credentials but lacks proper security measures.

### Implementation Steps

#### 4.1 Implement Secure Credential Storage

```python
# utils/security_manager.py
import os
import base64
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class SecurityManager:
    """
    Manages encryption, secure storage, and authentication for the application.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.salt = self._get_or_create_salt()
        self.key = self._derive_key()
        self.cipher = Fernet(base64.urlsafe_b64encode(self.key))
    
    def _get_or_create_salt(self) -> bytes:
        """Get existing salt or create a new one."""
        salt_path = self.config.get("salt_path", "config/.salt")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(salt_path), exist_ok=True)
        
        try:
            # Try to read existing salt
            if os.path.exists(salt_path):
                with open(salt_path, "rb") as f:
                    return f.read()
        except Exception as e:
            logger.warning(f"Failed to read salt: {str(e)}")
        
        # Create new salt
        logger.info("Creating new salt")
        salt = os.urandom(16)
        
        try:
            # Save salt to file
            with open(salt_path, "wb") as f:
                f.write(salt)
            
            # Set secure permissions
            os.chmod(salt_path, 0o600)
        except Exception as e:
            logger.error(f"Failed to save salt: {str(e)}")
        
        return salt
    
    def _derive_key(self) -> bytes:
        """Derive encryption key from master password."""
        master_password = self._get_master_password()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000
        )
        
        return kdf.derive(master_password.encode())
    
    def _get_master_password(self) -> str:
        """Get master password from environment or config."""
        # Try to get from environment
        env_var = os.environ.get("AI_JOB_BOT_MASTER_PASSWORD")
        if env_var:
            return env_var
        
        # Try to get from config
        config_password = self.config.get("master_password")
        if config_password:
            return config_password
        
        # Use default (not secure for production!)
        logger.warning("Using default master password - NOT SECURE FOR PRODUCTION!")
        return "change_this_in_production"
    
    def encrypt_data(self, data: Dict[str, Any]) -> str:
        """
        Encrypt dictionary data to a secure string.
        
        Args:
            data: Dictionary to encrypt
            
        Returns:
            Encrypted data as string
        """
        json_data = json.dumps(data)
        encrypted = self.cipher.encrypt(json_data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt_data(self, encrypted_data: str) -> Dict[str, Any]:
        """
        Decrypt string back to dictionary data.
        
        Args:
            encrypted_data: Encrypted data string
            
        Returns:
            Decrypted dictionary
        """
        try:
            decoded = base64.urlsafe_b64decode(encrypted_data)
            decrypted = self.cipher.decrypt(decoded)
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"Decryption error: {str(e)}")
            return {}
    
    def hash_password(self, password: str) -> str:
        """
        Create a secure hash of a password.
        
        Args:
            password: Password to hash
            
        Returns:
            Secure hash as string
        """
        # In a real implementation, use a proper password hashing library
        # such as bcrypt or argon2
        # This is a simplified example
        password_bytes = password.encode()
        digest = hashes.Hash(hashes.SHA256())
        digest.update(password_bytes)
        digest.update(self.salt)
        hash_bytes = digest.finalize()
        return base64.b64encode(hash_bytes).decode()
    
    def verify_password(self, password: str, stored_hash: str) -> bool:
        """
        Verify a password against a stored hash.
        
        Args:
            password: Password to verify
            stored_hash: Previously stored hash
            
        Returns:
            True if password matches, False otherwise
        """
        calculated_hash = self.hash_password(password)
        return calculated_hash == stored_hash
    
    def store_credentials(self, service: str, username: str, password: str) -> bool:
        """
        Securely store credentials for a service.
        
        Args:
            service: Service name (e.g., "linkedin")
            username: Username or email
            password: Password
            
        Returns:
            True if stored successfully, False otherwise
        """
        creds_dir = self.config.get("credentials_dir", "config/credentials")
        os.makedirs(creds_dir, exist_ok=True)
        
        creds_path = os.path.join(creds_dir, f"{service}.enc")
        
        try:
            # Encrypt credentials
            creds_data = {
                "username": username,
                "password": password,
                "service": service
            }
            
            encrypted = self.encrypt_data(creds_data)
            
            # Write to file
            with open(creds_path, "w") as f:
                f.write(encrypted)
            
            # Set secure permissions
            os.chmod(creds_path, 0o600)
            
            return True
        except Exception as e:
            logger.error(f"Failed to store credentials: {str(e)}")
            return False
    
    def get_credentials(self, service: str) -> Dict[str, str]:
        """
        Retrieve credentials for a service.
        
        Args:
            service: Service name (e.g., "linkedin")
            
        Returns:
            Dictionary with username and password, or empty dict if not found
        """
        creds_dir = self.config.get("credentials_dir", "config/credentials")
        creds_path = os.path.join(creds_dir, f"{service}.enc")
        
        if not os.path.exists(creds_path):
            logger.warning(f"No credentials found for {service}")
            return {}
        
        try:
            # Read encrypted data
            with open(creds_path, "r") as f:
                encrypted = f.read()
            
            # Decrypt and return
            return self.decrypt_data(encrypted)
        except Exception as e:
            logger.error(f"Failed to retrieve credentials: {str(e)}")
            return {}
```

#### 4.2 Implement Secure API Key Management

```python
# utils/api_key_manager.py
from utils.security_manager import SecurityManager
import os
import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class APIKeyManager:
    """
    Manages secure storage and retrieval of API keys.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.security_manager = SecurityManager(config)
        self.api_keys_file = self.config.get("api_keys_file", "config/api_keys.enc")
    
    def store_api_key(self, service: str, key: str, secret: Optional[str] = None) -> bool:
        """
        Securely store an API key.
        
        Args:
            service: Service name (e.g., "linkedin_api")
            key: API key or token
            secret: Optional API secret or secondary token
            
        Returns:
            True if stored successfully, False otherwise
        """
        # Read existing keys
        keys = self._read_keys()
        
        # Update with new key
        keys[service] = {
            "key": key,
            "secret": secret
        }
        
        # Write back
        return self._write_keys(keys)
    
    def get_api_key(self, service: str) -> Dict[str, str]:
        """
        Get API key for a service.
        
        Args:
            service: Service name (e.g., "linkedin_api")
            
        Returns:
            Dictionary with key and optional secret
        """
        # Try to get from environment variables first
        env_key = os.environ.get(f"{service.upper()}_API_KEY")
        env_secret = os.environ.get(f"{service.upper()}_API_SECRET")
        
        if env_key:
            return {
                "key": env_key,
                "secret": env_secret
            }
        
        # Fall back to stored keys
        keys = self._read_keys()
        return keys.get(service, {})
    
    def list_services(self) -> List[str]:
        """
        List all services with stored API keys.
        
        Returns:
            List of service names
        """
        keys = self._read_keys()
        return list(keys.keys())
    
    def remove_api_key(self, service: str) -> bool:
        """
        Remove API key for a service.
        
        Args:
            service: Service name to remove
            
        Returns:
            True if removed successfully, False otherwise
        """
        keys = self._read_keys()
        
        if service in keys:
            del keys[service]
            return self._write_keys(keys)
        
        return False
    
    def _read_keys(self) -> Dict[str, Dict[str, str]]:
        """Read and decrypt API keys from file."""
        if not os.path.exists(self.api_keys_file):
            return {}
        
        try:
            with open(self.api_keys_file, "r") as f:
                encrypted = f.read()
            
            return self.security_manager.decrypt_data(encrypted) or {}
        except Exception as e:
            logger.error(f"Failed to read API keys: {str(e)}")
            return {}
    
    def _write_keys(self, keys: Dict[str, Dict[str, str]]) -> bool:
        """Encrypt and write API keys to file."""
        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(self.api_keys_file), exist_ok=True)
            
            # Encrypt keys
            encrypted = self.security_manager.encrypt_data(keys)
            
            # Write to file
            with open(self.api_keys_file, "w") as f:
                f.write(encrypted)
            
            # Set secure permissions
            os.chmod(self.api_keys_file, 0o600)
            
            return True
        except Exception as e:
            logger.error(f"Failed to write API keys: {str(e)}")
            return False
```

#### 4.3 Implement Secure User Authentication

```python
# utils/auth_manager.py
from utils.security_manager import SecurityManager
from utils.database_manager import DatabaseManager
import uuid
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AuthManager:
    """
    Manages user authentication and session handling.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.security_manager = SecurityManager(config)
        self.db_manager = DatabaseManager()
        self.session_duration = self.config.get("session_duration", 86400)  # 24 hours
    
    def register_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Register a new user.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Dictionary with user info and status
        """
        # Check if user already exists
        existing_user = self.db_manager.get_user(email=email)
        if existing_user:
            return {
                "success": False,
                "error": "User with this email already exists"
            }
        
        # Create new user
        user_id = str(uuid.uuid4())
        password_hash = self.security_manager.hash_password(password)
        
        success = self.db_manager.create_user(
            user_id=user_id,
            email=email,
            password_hash=password_hash
        )
        
        if not success:
            return {
                "success": False,
                "error": "Failed to create user"
            }
        
        return {
            "success": True,
            "user_id": user_id,
            "email": email
        }
    
    def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate a user and create a session.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Dictionary with session info and status
        """
        # Get user by email
        user = self.db_manager.get_user(email=email)
        if not user:
            return {
                "success": False,
                "error": "User not found"
            }
        
        # Verify password
        if not self.security_manager.verify_password(password, user["password_hash"]):
            return {
                "success": False,
                "error": "Invalid password"
            }
        
        # Create session
        session_id = str(uuid.uuid4())
        success = self.db_manager.create_session(
            session_id=session_id,
            user_id=user["id"]
        )
        
        if not success:
            return {
                "success": False,
                "error": "Failed to create session"
            }
        
        # Set last login time
        self.db_manager.execute_query(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
            (user["id"],)
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "user_id": user["id"],
            "email": user["email"]
        }
    
    def logout(self, session_id: str) -> bool:
        """
        End a user session.
        
        Args:
            session_id: Session ID to end
            
        Returns:
            True if logged out successfully, False otherwise
        """
        return self.db_manager.end_session(session_id)
    
    def validate_session(self, session_id: str) -> Dict[str, Any]:
        """
        Validate a session and get user info.
        
        Args:
            session_id: Session ID to validate
            
        Returns:
            Dictionary with user info and status
        """
        # Get session
        session = self.db_manager.execute_query(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,),
            fetchone=True
        )
        
        if not session:
            return {
                "valid": False,
                "error": "Session not found"
            }
        
        # Convert to dict
        session = dict(session)
        
        # Check if session is active
        if session["status"] != "active":
            return {
                "valid": False,
                "error": "Session inactive"
            }
        
        # Check if session has expired
        if session["end_time"]:
            return {
                "valid": False,
                "error": "Session expired"
            }
        
        # Get user info
        user = self.db_manager.get_user(user_id=session["user_id"])
        if not user:
            return {
                "valid": False,
                "error": "User not found"
            }
        
        return {
            "valid": True,
            "user_id": user["id"],
            "email": user["email"]
        }
    
    def change_password(self, user_id: str, current_password: str, new_password: str) -> Dict[str, Any]:
        """
        Change a user's password.
        
        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
            
        Returns:
            Dictionary with status and message
        """
        # Get user
        user = self.db_manager.get_user(user_id=user_id)
        if not user:
            return {
                "success": False,
                "error": "User not found"
            }
        
        # Verify current password
        if not self.security_manager.verify_password(current_password, user["password_hash"]):
            return {
                "success": False,
                "error": "Current password is incorrect"
            }
        
        # Update password
        new_hash = self.security_manager.hash_password(new_password)
        success = self.db_manager.execute_query(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, user_id)
        )
        
        if not success:
            return {
                "success": False,
                "error": "Failed to update password"
            }
        
        return {
            "success": True,
            "message": "Password updated successfully"
        }
```

These implementation steps address the critical issues identified in the project analysis:

1. **Database Architecture** - A proper SQLite implementation with robust schema and API
2. **Browser Automation Compatibility** - A unified interface with factory pattern for consistent use
3. **API Dependency Risks** - Resilient client with caching, retry, and fallback mechanisms
4. **Security Vulnerabilities** - Secure credential storage, API key management, and authentication

These implementations provide a solid foundation for resolving the most critical issues in the project, making it more robust and maintainable.
