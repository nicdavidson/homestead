"""
Hearth Core - REST API

FastAPI-based REST API for external access to Hearth functionality.
Enables web apps, mobile apps, and external services to interact with entities.
"""

import os
import asyncio
import json
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import Config
from .tasks import TaskManager
from .sessions import SessionManager
from .proposals import ProposalManager
from .projects import ProjectManager
from .skills import SkillManager
from .reflections import ReflectionManager


# === Request/Response Models ===

class ChatRequest(BaseModel):
    """Request for chat endpoint."""
    message: str
    provider: Optional[str] = "grok"
    stream: bool = False


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    response: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float


class TaskCreate(BaseModel):
    """Request to create a task."""
    title: str
    description: Optional[str] = None
    priority: int = 1
    source: str = "api"


class TaskResponse(BaseModel):
    """Task response."""
    id: str  # Task IDs are strings like "0001", "0002"
    title: str
    description: Optional[str] = None
    status: str
    priority: int
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class SubagentSpawn(BaseModel):
    """Request to spawn a subagent."""
    task: str
    agent_type: str = "grok"
    label: Optional[str] = None


class SubagentResponse(BaseModel):
    """Subagent spawn response."""
    run_id: str
    status: str
    message: str


class ProposalCreate(BaseModel):
    """Request to create a proposal."""
    title: str
    description: str
    reasoning: str
    target_files: List[str]
    diffs: Dict[str, str]
    priority: str = "medium"
    test_plan: Optional[str] = None
    rollback_plan: Optional[str] = None


class ProposalResponse(BaseModel):
    """Proposal response."""
    id: str
    title: str
    status: str
    priority: str
    created_at: str


class ProjectCreate(BaseModel):
    """Request to create a project."""
    name: str
    description: str
    goals: Optional[List[str]] = None


class ProjectResponse(BaseModel):
    """Project response."""
    id: str
    name: str
    description: str
    status: str
    goals: List[str]
    created_at: str


class SkillCreate(BaseModel):
    """Request to create a skill."""
    name: str
    description: str
    content: str
    examples: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class SkillResponse(BaseModel):
    """Skill response."""
    name: str
    description: str
    tags: List[str]
    file_path: str


# === WebSocket Manager ===

class WebSocketManager:
    """Manages WebSocket connections and broadcasts events."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)

    async def broadcast(self, event_type: str, data: Dict[str, Any]):
        """Broadcast an event to all connected clients."""
        message = json.dumps({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })

        # Send to all connections, remove dead ones
        dead_connections = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                dead_connections.add(connection)

        # Clean up dead connections
        self.active_connections -= dead_connections

    async def send_to(self, websocket: WebSocket, event_type: str, data: Dict[str, Any]):
        """Send an event to a specific client."""
        message = json.dumps({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
        try:
            await websocket.send_text(message)
        except Exception:
            self.disconnect(websocket)


# === API Creation ===

def create_api(config: Optional[Config] = None) -> FastAPI:
    """
    Create FastAPI application with all endpoints.

    Args:
        config: Hearth configuration (uses default if not provided)

    Returns:
        Configured FastAPI app
    """
    if config is None:
        config = Config()

    app = FastAPI(
        title="Hearth API",
        description="REST API for Hearth AI entity framework",
        version="1.0.0"
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize managers
    task_manager = TaskManager(config)
    session_manager = SessionManager(config)
    proposal_manager = ProposalManager(config)
    project_manager = ProjectManager(config)
    skill_manager = SkillManager(config)
    reflection_manager = ReflectionManager(config)
    ws_manager = WebSocketManager()

    # === Endpoints ===

    @app.get("/")
    def root():
        """API root."""
        return {
            "name": "Hearth API",
            "version": "1.0.0",
            "entity": config.entity_user,
            "endpoints": {
                "health": "/health",
                "tasks": "/tasks",
                "subagents": "/subagents",
                "proposals": "/proposals",
                "projects": "/projects",
                "skills": "/skills",
                "reflections": "/reflections",
                "websocket": "/ws"
            }
        }

    @app.get("/health")
    def health():
        """Health check."""
        return {
            "status": "healthy",
            "entity": config.entity_user,
            "entity_home": str(config.entity_home),
            "timestamp": datetime.now().isoformat()
        }

    # === WebSocket ===

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """
        WebSocket endpoint for real-time updates.

        Events broadcasted:
        - task.created
        - task.started
        - task.completed
        - subagent.spawned
        - subagent.completed
        - proposal.created
        - project.created
        - skill.created
        """
        await ws_manager.connect(websocket)
        try:
            # Send welcome message
            await ws_manager.send_to(websocket, "connected", {
                "message": "Connected to Hearth API",
                "entity": config.entity_user
            })

            # Keep connection alive and handle incoming messages
            while True:
                data = await websocket.receive_text()
                # Echo back for heartbeat/ping
                await ws_manager.send_to(websocket, "pong", {"received": data})

        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)

    # === Tasks ===

    @app.post("/tasks", response_model=TaskResponse)
    async def create_task(task: TaskCreate, background_tasks: BackgroundTasks):
        """Create a new task."""
        task_id = task_manager.create_task(
            title=task.title,
            description=task.description,
            priority=task.priority,
            source=task.source
        )

        task_data = task_manager.get_task(task_id)
        if not task_data:
            raise HTTPException(status_code=500, detail="Failed to create task")

        # Broadcast event
        await ws_manager.broadcast("task.created", task_data)

        return TaskResponse(**task_data)

    @app.get("/tasks", response_model=List[TaskResponse])
    def list_tasks(
        status: Optional[str] = None,
        limit: int = 50
    ):
        """List tasks."""
        tasks = task_manager.list_tasks(status=status, limit=limit)
        return [TaskResponse(**t) for t in tasks]

    @app.get("/tasks/stats")
    def task_stats():
        """Get task statistics."""
        return task_manager.get_stats()

    @app.get("/tasks/{task_id}", response_model=TaskResponse)
    def get_task(task_id: str):
        """Get a specific task."""
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return TaskResponse(**task)

    @app.post("/tasks/{task_id}/start")
    async def start_task(task_id: str):
        """Start a task."""
        task_manager.start_task(task_id)
        task_data = task_manager.get_task(task_id)
        if task_data:
            await ws_manager.broadcast("task.started", task_data)
        return {"status": "started", "task_id": task_id}

    @app.post("/tasks/{task_id}/complete")
    async def complete_task(task_id: str, result: Optional[str] = None):
        """Complete a task."""
        task_manager.complete_task(task_id, result=result)
        task_data = task_manager.get_task(task_id)
        if task_data:
            await ws_manager.broadcast("task.completed", task_data)
        return {"status": "completed", "task_id": task_id}

    # === Subagents ===

    @app.post("/subagents", response_model=SubagentResponse)
    async def spawn_subagent(spawn: SubagentSpawn, background_tasks: BackgroundTasks):
        """Spawn a subagent (runs in background)."""
        result = session_manager.spawn_agent(
            agent_type=spawn.agent_type,
            task=spawn.task,
            spawned_by="api",
            label=spawn.label
        )

        # Broadcast event
        await ws_manager.broadcast("subagent.spawned", {
            "run_id": result["run_id"],
            "agent_type": spawn.agent_type,
            "task": spawn.task,
            "label": spawn.label
        })

        return SubagentResponse(
            run_id=result["run_id"],
            status=result["status"],
            message=f"Subagent spawned: {result['run_id']}"
        )

    @app.get("/subagents/{run_id}")
    def get_subagent(run_id: str):
        """Get subagent status and result."""
        session = session_manager.get_session(run_id)
        if not session:
            raise HTTPException(status_code=404, detail="Subagent not found")

        return {
            "run_id": session.run_id,
            "agent_type": session.agent_type,
            "status": session.status,
            "result": session.result,
            "cost": session.cost,
            "spawned_at": session.spawned_at.isoformat() if session.spawned_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        }

    @app.get("/subagents")
    def list_subagents(limit: int = 50):
        """List recent subagents."""
        all_sessions = session_manager.list_subagents()
        # Manually limit results
        sessions = all_sessions[:limit] if isinstance(all_sessions, list) else []
        return [
            {
                "run_id": s["run_id"] if isinstance(s, dict) else s.run_id,
                "agent_type": s["agent_type"] if isinstance(s, dict) else s.agent_type,
                "status": s["status"] if isinstance(s, dict) else s.status,
                "label": s.get("label") if isinstance(s, dict) else getattr(s, "label", None),
                "spawned_at": s["spawned_at"] if isinstance(s, dict) else (s.spawned_at.isoformat() if s.spawned_at else None),
            }
            for s in sessions
        ]

    # === Proposals ===

    @app.post("/proposals", response_model=ProposalResponse)
    def create_proposal(proposal: ProposalCreate):
        """Create a self-improvement proposal."""
        p = proposal_manager.create_proposal(
            title=proposal.title,
            description=proposal.description,
            reasoning=proposal.reasoning,
            target_files=proposal.target_files,
            diffs=proposal.diffs,
            priority=proposal.priority,
            test_plan=proposal.test_plan,
            rollback_plan=proposal.rollback_plan
        )

        return ProposalResponse(
            id=p.id,
            title=p.title,
            status=p.status,
            priority=p.priority,
            created_at=p.created_at
        )

    @app.get("/proposals")
    def list_proposals(status: Optional[str] = None):
        """List proposals."""
        # ProposalManager.list_proposals() requires a valid status, defaults to "pending"
        proposals = proposal_manager.list_proposals(status=status if status else "pending")
        return [
            ProposalResponse(
                id=p.id,
                title=p.title,
                status=p.status,
                priority=p.priority,
                created_at=p.created_at
            )
            for p in proposals
        ]

    @app.get("/proposals/{proposal_id}")
    def get_proposal(proposal_id: str):
        """Get a specific proposal."""
        p = proposal_manager.get_proposal(proposal_id)
        if not p:
            raise HTTPException(status_code=404, detail="Proposal not found")

        return {
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "reasoning": p.reasoning,
            "status": p.status,
            "priority": p.priority,
            "target_files": p.target_files,
            "diffs": p.diffs,
            "test_plan": p.test_plan,
            "rollback_plan": p.rollback_plan,
            "created_at": p.created_at,
        }

    # === Projects ===

    @app.post("/projects", response_model=ProjectResponse)
    def create_project(project: ProjectCreate):
        """Create a project."""
        p = project_manager.create_project(
            name=project.name,
            description=project.description,
            goals=project.goals
        )

        return ProjectResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            status=p.status,
            goals=p.goals,
            created_at=p.created_at
        )

    @app.get("/projects")
    def list_projects(status: Optional[str] = None):
        """List projects."""
        # ProjectManager.list_projects() requires a valid status, defaults to "active"
        projects = project_manager.list_projects(status=status if status else "active")
        return [
            ProjectResponse(
                id=p.id,
                name=p.name,
                description=p.description,
                status=p.status,
                goals=p.goals,
                created_at=p.created_at
            )
            for p in projects
        ]

    @app.get("/projects/{project_id}")
    def get_project(project_id: str):
        """Get a specific project."""
        p = project_manager.get_project(project_id)
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")

        return {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "status": p.status,
            "goals": p.goals,
            "notes": p.notes,
            "created_at": p.created_at,
            "updated_at": p.updated_at if p.updated_at else None,
        }

    @app.post("/projects/{project_id}/pause")
    def pause_project(project_id: str):
        """Pause a project."""
        project_manager.pause_project(project_id)
        return {"status": "paused", "project_id": project_id}

    @app.post("/projects/{project_id}/resume")
    def resume_project(project_id: str):
        """Resume a project."""
        project_manager.resume_project(project_id)
        return {"status": "active", "project_id": project_id}

    # === Skills ===

    @app.post("/skills", response_model=SkillResponse)
    def create_skill(skill: SkillCreate):
        """Create a skill."""
        s = skill_manager.create_skill(
            name=skill.name,
            description=skill.description,
            content=skill.content,
            examples=skill.examples,
            tags=skill.tags
        )

        return SkillResponse(
            name=s.name,
            description=s.description,
            tags=s.tags,
            file_path=str(skill_manager.skills_dir / (skill_manager._slugify(s.name) + ".md"))
        )

    @app.get("/skills")
    def list_skills():
        """List all skills."""
        skills = skill_manager.list_skills()
        return [
            SkillResponse(
                name=s.name,
                description=s.description,
                tags=s.tags,
                file_path=str(skill_manager.skills_dir / (skill_manager._slugify(s.name) + ".md"))
            )
            for s in skills
        ]

    @app.get("/skills/search")
    def search_skills(query: str):
        """Search skills."""
        skills = skill_manager.search_skills(query)
        return [
            SkillResponse(
                name=s.name,
                description=s.description,
                tags=s.tags,
                file_path=str(skill_manager.skills_dir / (skill_manager._slugify(s.name) + ".md"))
            )
            for s in skills
        ]

    @app.get("/skills/{skill_name}")
    def get_skill(skill_name: str):
        """Get a specific skill."""
        s = skill_manager.get_skill(skill_name)
        if not s:
            raise HTTPException(status_code=404, detail="Skill not found")

        return {
            "name": s.name,
            "description": s.description,
            "content": s.content,
            "examples": s.examples,
            "tags": s.tags,
        }

    # === Reflections ===

    @app.get("/reflections/should-reflect")
    def should_reflect():
        """Check if it's time for a reflection."""
        return {
            "should_reflect": reflection_manager.should_reflect(),
            "last_reflection": reflection_manager.get_last_reflection()
        }

    @app.get("/reflections")
    def list_reflections():
        """List all reflections."""
        return reflection_manager.list_reflections()

    @app.get("/reflections/stats")
    def reflection_stats():
        """Get reflection statistics."""
        reflections = reflection_manager.list_reflections(limit=100)
        return {
            "total_reflections": len(reflections),
            "should_reflect": reflection_manager.should_reflect(),
            "last_reflection": reflection_manager.get_last_reflection()
        }

    return app


# === Standalone Server ===

def run_api_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    config: Optional[Config] = None
):
    """
    Run the API server.

    Args:
        host: Host to bind to
        port: Port to bind to
        config: Hearth configuration
    """
    import uvicorn

    app = create_api(config)

    print(f"Starting Hearth API server on http://{host}:{port}")
    print(f"Docs available at http://{host}:{port}/docs")

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_api_server()
