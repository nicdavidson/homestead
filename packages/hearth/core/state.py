"""
Hearth Core - State Management (SQLite)
Handles concurrent access for tasks, conversations, sessions.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from contextlib import contextmanager
import threading


class StateDB:
    """
    SQLite-backed state management.
    Thread-safe, handles concurrent access from TG/CLI/Web.
    """
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    @contextmanager
    def _cursor(self):
        """Context manager for cursor with auto-commit."""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
    
    def _init_db(self):
        """Initialize database schema."""
        with self._cursor() as c:
            # Tasks table
            c.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    priority INTEGER DEFAULT 3,
                    complexity TEXT,
                    complexity_score INTEGER,
                    assigned_to TEXT,
                    source TEXT,
                    project TEXT,
                    result TEXT,
                    error TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    completed_at TEXT,
                    metadata TEXT
                )
            ''')
            
            # Conversations table
            c.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT
                )
            ''')
            
            # Sessions table
            c.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    channel TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    metadata TEXT
                )
            ''')
            
            # Key-value store for misc state
            c.execute('''
                CREATE TABLE IF NOT EXISTS state (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            ''')

            # Costs table
            c.execute('''
                CREATE TABLE IF NOT EXISTS costs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model TEXT NOT NULL,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    cost REAL DEFAULT 0.0,
                    timestamp TEXT NOT NULL,
                    metadata TEXT
                )
            ''')

            # Indices
            c.execute('CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_costs_timestamp ON costs(timestamp)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_costs_model ON costs(model)')
    
    # === Key-Value State ===
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a state value."""
        with self._cursor() as c:
            c.execute('SELECT value FROM state WHERE key = ?', (key,))
            row = c.fetchone()
            if row:
                try:
                    return json.loads(row['value'])
                except json.JSONDecodeError:
                    return row['value']
            return default
    
    def set(self, key: str, value: Any):
        """Set a state value."""
        with self._cursor() as c:
            json_value = json.dumps(value) if not isinstance(value, str) else value
            c.execute('''
                INSERT INTO state (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=?, updated_at=?
            ''', (key, json_value, datetime.now().isoformat(), 
                  json_value, datetime.now().isoformat()))
    
    def delete(self, key: str):
        """Delete a state value."""
        with self._cursor() as c:
            c.execute('DELETE FROM state WHERE key = ?', (key,))
    
    # === Tasks ===
    
    def add_task(
        self,
        title: str,
        description: str = "",
        priority: int = 3,
        source: str = "manual",
        project: str = None,
        metadata: dict = None
    ) -> str:
        """Add a new task."""
        task_id = self._generate_task_id()
        now = datetime.now().isoformat()
        
        with self._cursor() as c:
            c.execute('''
                INSERT INTO tasks 
                (id, title, description, priority, source, project, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (task_id, title, description, priority, source, project, 
                  now, now, json.dumps(metadata or {})))
        
        return task_id
    
    def _generate_task_id(self) -> str:
        """Generate next task ID."""
        with self._cursor() as c:
            c.execute('SELECT MAX(CAST(id AS INTEGER)) FROM tasks WHERE id GLOB "[0-9]*"')
            row = c.fetchone()
            max_id = row[0] if row[0] else 0
            return f"{max_id + 1:04d}"
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get a task by ID."""
        with self._cursor() as c:
            c.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
            row = c.fetchone()
            return dict(row) if row else None
    
    def update_task(self, task_id: str, **kwargs) -> bool:
        """Update task fields."""
        if not kwargs:
            return False
            
        kwargs['updated_at'] = datetime.now().isoformat()
        
        # Handle metadata specially
        if 'metadata' in kwargs and isinstance(kwargs['metadata'], dict):
            kwargs['metadata'] = json.dumps(kwargs['metadata'])
        
        set_clause = ', '.join(f'{k} = ?' for k in kwargs.keys())
        values = list(kwargs.values()) + [task_id]
        
        with self._cursor() as c:
            c.execute(f'UPDATE tasks SET {set_clause} WHERE id = ?', values)
            return c.rowcount > 0
    
    def complete_task(self, task_id: str, result: str = "") -> bool:
        """Mark task as completed."""
        return self.update_task(
            task_id,
            status='completed',
            result=result,
            completed_at=datetime.now().isoformat()
        )
    
    def fail_task(self, task_id: str, error: str) -> bool:
        """Mark task as failed."""
        return self.update_task(task_id, status='failed', error=error)
    
    def get_pending_tasks(self, limit: int = 10) -> List[Dict]:
        """Get pending tasks ordered by priority."""
        with self._cursor() as c:
            c.execute('''
                SELECT * FROM tasks 
                WHERE status = 'pending'
                ORDER BY priority, created_at
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in c.fetchall()]
    
    def get_next_task(self) -> Optional[Dict]:
        """Get the next task to process."""
        tasks = self.get_pending_tasks(limit=1)
        return tasks[0] if tasks else None
    
    def get_tasks_by_status(self, status: str) -> List[Dict]:
        """Get all tasks with a given status."""
        with self._cursor() as c:
            c.execute('SELECT * FROM tasks WHERE status = ?', (status,))
            return [dict(row) for row in c.fetchall()]
    
    def get_task_stats(self) -> Dict:
        """Get task statistics."""
        with self._cursor() as c:
            c.execute('''
                SELECT status, COUNT(*) as count 
                FROM tasks 
                GROUP BY status
            ''')
            by_status = {row['status']: row['count'] for row in c.fetchall()}
            
            c.execute('''
                SELECT COUNT(*) as count FROM tasks 
                WHERE status = 'completed' 
                AND date(completed_at) = date('now')
            ''')
            completed_today = c.fetchone()['count']
            
            return {
                'by_status': by_status,
                'completed_today': completed_today,
                'total': sum(by_status.values())
            }
    
    # === Conversations ===
    
    def add_message(
        self,
        session_id: str,
        channel: str,
        role: str,
        content: str,
        metadata: dict = None
    ):
        """Add a message to conversation history."""
        with self._cursor() as c:
            c.execute('''
                INSERT INTO conversations 
                (session_id, channel, role, content, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session_id, channel, role, content, 
                  datetime.now().isoformat(), json.dumps(metadata or {})))
            
            # Update session
            c.execute('''
                INSERT INTO sessions (id, channel, started_at, last_activity, message_count)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(id) DO UPDATE SET 
                    last_activity = ?,
                    message_count = message_count + 1
            ''', (session_id, channel, datetime.now().isoformat(),
                  datetime.now().isoformat(), datetime.now().isoformat()))
    
    def get_conversation(
        self, 
        session_id: str, 
        limit: int = 20
    ) -> List[Dict]:
        """Get recent conversation history."""
        with self._cursor() as c:
            c.execute('''
                SELECT role, content, timestamp FROM conversations
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (session_id, limit))
            rows = c.fetchall()
            # Return in chronological order
            return [dict(row) for row in reversed(rows)]
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session info."""
        with self._cursor() as c:
            c.execute('SELECT * FROM sessions WHERE id = ?', (session_id,))
            row = c.fetchone()
            return dict(row) if row else None
    
    # === Costs ===

    def log_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        metadata: dict = None
    ):
        """Log API usage and cost."""
        with self._cursor() as c:
            c.execute('''
                INSERT INTO costs
                (model, input_tokens, output_tokens, cost, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (model, input_tokens, output_tokens, cost,
                  datetime.now().isoformat(), json.dumps(metadata or {})))

    def get_daily_costs(self) -> Dict:
        """Get today's cost summary."""
        with self._cursor() as c:
            # Total for today
            c.execute('''
                SELECT
                    SUM(cost) as total,
                    SUM(input_tokens) as input_tokens,
                    SUM(output_tokens) as output_tokens
                FROM costs
                WHERE date(timestamp) = date('now')
            ''')
            row = c.fetchone()
            total = row['total'] or 0.0

            # By model
            c.execute('''
                SELECT
                    model,
                    SUM(cost) as cost,
                    SUM(input_tokens) as input_tokens,
                    SUM(output_tokens) as output_tokens,
                    COUNT(*) as calls
                FROM costs
                WHERE date(timestamp) = date('now')
                GROUP BY model
            ''')
            by_model = {
                row['model']: {
                    'cost': row['cost'] or 0.0,
                    'input_tokens': row['input_tokens'] or 0,
                    'output_tokens': row['output_tokens'] or 0,
                    'calls': row['calls']
                }
                for row in c.fetchall()
            }

            return {
                'total': total,
                'by_model': by_model
            }

    def get_weekly_costs(self) -> Dict:
        """Get last 7 days cost summary."""
        with self._cursor() as c:
            c.execute('''
                SELECT
                    date(timestamp) as date,
                    SUM(cost) as total,
                    model,
                    SUM(input_tokens) as input_tokens,
                    SUM(output_tokens) as output_tokens
                FROM costs
                WHERE date(timestamp) >= date('now', '-7 days')
                GROUP BY date(timestamp), model
                ORDER BY date(timestamp) DESC
            ''')

            # Organize by day
            days_data = {}
            for row in c.fetchall():
                date = row['date']
                if date not in days_data:
                    days_data[date] = {'total': 0.0, 'by_model': {}}

                days_data[date]['by_model'][row['model']] = {
                    'cost': row['total'] or 0.0,
                    'input_tokens': row['input_tokens'] or 0,
                    'output_tokens': row['output_tokens'] or 0
                }
                days_data[date]['total'] += row['total'] or 0.0

            days = [{'date': d, **data} for d, data in days_data.items()]
            total = sum(d['total'] for d in days)
            average = total / 7 if days else 0.0

            return {
                'days': days,
                'total': total,
                'average': average
            }

    # === Utility ===

    def close(self):
        """Close the database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# Singleton instance
_state_instance = None


def get_state(db_path: str = "/home/_/data/hearth.db") -> StateDB:
    """Get or create singleton StateDB instance."""
    global _state_instance
    if _state_instance is None:
        _state_instance = StateDB(db_path)
    return _state_instance
