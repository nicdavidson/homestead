"""
Hearth Web - FastAPI + HTMX Web Interface (v1.0+ Ultimate)

Complete web UI for:
- Chat
- Tasks management
- Skills library
- Projects dashboard
- Proposals review
- Status & reflections
- Configuration
- Debug/Introspection
"""

import logging
import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core import (
    Config, get_config, get_state, CostTracker, Identity,
    get_task_manager, get_session_manager, get_proposal_manager,
    get_project_manager, get_skill_manager, get_reflection_manager
)
from agents import Gateway

logger = logging.getLogger("hearth.web")


def create_app(config: Optional[Config] = None) -> FastAPI:
    """Create the FastAPI application with all v1.0+ features."""
    config = config or get_config()

    app = FastAPI(
        title="Hearth Web UI",
        description="Complete interface for Hearth AI entity"
    )

    # Setup paths
    web_dir = Path(__file__).parent
    templates = Jinja2Templates(directory=web_dir / "templates")

    # Mount static files
    static_dir = web_dir / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # Initialize all managers
    gateway = Gateway(config)
    identity = Identity(config)
    costs = CostTracker(config)
    state = get_state()
    task_manager = get_task_manager()
    session_manager = get_session_manager()
    proposal_manager = get_proposal_manager()
    project_manager = get_project_manager()
    skill_manager = get_skill_manager()
    reflection_manager = get_reflection_manager()

    # === Chat ===

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Main chat page."""
        return templates.TemplateResponse("chat.html", {
            "request": request,
            "name": identity.get_name(),
            "title": "Chat"
        })

    @app.post("/chat", response_class=HTMLResponse)
    async def chat(request: Request, message: str = Form(...)):
        """Handle chat message via HTMX."""
        response = gateway.process(message, channel="web", session_id="web-main")

        return templates.TemplateResponse("partials/message.html", {
            "request": request,
            "user_message": message,
            "assistant_message": response.content,
            "model": response.model,
            "cost": f"${response.cost:.4f}" if response.cost > 0 else "",
        })

    # === Tasks ===

    @app.get("/tasks", response_class=HTMLResponse)
    async def tasks_page(request: Request, status: Optional[str] = None):
        """Tasks management page."""
        tasks = task_manager.list_tasks(status=status, limit=100)
        stats = task_manager.get_stats()

        return templates.TemplateResponse("tasks.html", {
            "request": request,
            "name": identity.get_name(),
            "title": "Tasks",
            "tasks": tasks,
            "stats": stats,
            "current_status": status
        })

    @app.post("/tasks/create", response_class=HTMLResponse)
    async def create_task(
        request: Request,
        title: str = Form(...),
        description: Optional[str] = Form(None),
        priority: int = Form(1)
    ):
        """Create a new task via HTMX."""
        task_id = task_manager.create_task(
            title=title,
            description=description,
            priority=priority,
            source="web"
        )

        task = task_manager.get_task(task_id)

        return templates.TemplateResponse("partials/task_row.html", {
            "request": request,
            "task": task
        })

    @app.post("/tasks/{task_id}/start", response_class=HTMLResponse)
    async def start_task(request: Request, task_id: str):
        """Start a task via HTMX."""
        task_manager.start_task(task_id)
        task = task_manager.get_task(task_id)

        return templates.TemplateResponse("partials/task_row.html", {
            "request": request,
            "task": task
        })

    @app.post("/tasks/{task_id}/complete", response_class=HTMLResponse)
    async def complete_task(
        request: Request,
        task_id: str,
        result: Optional[str] = Form(None)
    ):
        """Complete a task via HTMX."""
        task_manager.complete_task(task_id, result=result)
        task = task_manager.get_task(task_id)

        return templates.TemplateResponse("partials/task_row.html", {
            "request": request,
            "task": task
        })

    # === Skills ===

    @app.get("/skills", response_class=HTMLResponse)
    async def skills_page(request: Request, query: Optional[str] = None):
        """Skills library page."""
        if query:
            skills = skill_manager.search_skills(query)
        else:
            skills = skill_manager.list_skills()

        return templates.TemplateResponse("skills.html", {
            "request": request,
            "name": identity.get_name(),
            "title": "Skills",
            "skills": skills,
            "query": query
        })

    @app.post("/skills/create", response_class=HTMLResponse)
    async def create_skill(
        request: Request,
        name: str = Form(...),
        description: str = Form(...),
        content: str = Form(...),
        tags: Optional[str] = Form(None)
    ):
        """Create a new skill via HTMX."""
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

        skill = skill_manager.create_skill(
            name=name,
            description=description,
            content=content,
            tags=tag_list
        )

        return templates.TemplateResponse("partials/skill_card.html", {
            "request": request,
            "skill": skill
        })

    @app.get("/skills/{skill_name}", response_class=HTMLResponse)
    async def view_skill(request: Request, skill_name: str):
        """View skill detail."""
        skill = skill_manager.get_skill(skill_name)
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")

        return templates.TemplateResponse("skill_detail.html", {
            "request": request,
            "name": identity.get_name(),
            "title": f"Skill: {skill.name}",
            "skill": skill
        })

    # === Projects ===

    @app.get("/projects", response_class=HTMLResponse)
    async def projects_page(request: Request, status: Optional[str] = None):
        """Projects dashboard page."""
        if status:
            projects = project_manager.list_projects(status=status)
        else:
            # Show all
            active = project_manager.list_projects(status="active")
            paused = project_manager.list_projects(status="paused")
            completed = project_manager.list_projects(status="completed")
            projects = active + paused + completed

        return templates.TemplateResponse("projects.html", {
            "request": request,
            "name": identity.get_name(),
            "title": "Projects",
            "projects": projects,
            "current_status": status
        })

    @app.post("/projects/create", response_class=HTMLResponse)
    async def create_project(
        request: Request,
        name: str = Form(...),
        description: str = Form(...),
        goals: Optional[str] = Form(None)
    ):
        """Create a new project via HTMX."""
        goal_list = [g.strip() for g in goals.split("\n") if g.strip()] if goals else []

        project = project_manager.create_project(
            name=name,
            description=description,
            goals=goal_list
        )

        return templates.TemplateResponse("partials/project_card.html", {
            "request": request,
            "project": project
        })

    @app.post("/projects/{project_id}/pause", response_class=HTMLResponse)
    async def pause_project(request: Request, project_id: str):
        """Pause a project via HTMX."""
        project_manager.pause_project(project_id)
        project = project_manager.get_project(project_id)

        return templates.TemplateResponse("partials/project_card.html", {
            "request": request,
            "project": project
        })

    @app.post("/projects/{project_id}/resume", response_class=HTMLResponse)
    async def resume_project(request: Request, project_id: str):
        """Resume a project via HTMX."""
        project_manager.resume_project(project_id)
        project = project_manager.get_project(project_id)

        return templates.TemplateResponse("partials/project_card.html", {
            "request": request,
            "project": project
        })

    @app.get("/projects/{project_id}", response_class=HTMLResponse)
    async def view_project(request: Request, project_id: str):
        """View project detail."""
        project = project_manager.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        return templates.TemplateResponse("project_detail.html", {
            "request": request,
            "name": identity.get_name(),
            "title": f"Project: {project.name}",
            "project": project
        })

    # === Proposals ===

    @app.get("/proposals", response_class=HTMLResponse)
    async def proposals_page(request: Request, status: Optional[str] = None):
        """Proposals review page."""
        proposals = proposal_manager.list_proposals(status=status or "pending")

        return templates.TemplateResponse("proposals.html", {
            "request": request,
            "name": identity.get_name(),
            "title": "Proposals",
            "proposals": proposals,
            "current_status": status or "pending"
        })

    @app.get("/proposals/{proposal_id}", response_class=HTMLResponse)
    async def view_proposal(request: Request, proposal_id: str):
        """View proposal detail."""
        proposal = proposal_manager.get_proposal(proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")

        return templates.TemplateResponse("proposal_detail.html", {
            "request": request,
            "name": identity.get_name(),
            "title": f"Proposal: {proposal.title}",
            "proposal": proposal
        })

    @app.post("/proposals/{proposal_id}/approve", response_class=HTMLResponse)
    async def approve_proposal(request: Request, proposal_id: str):
        """Approve a proposal via HTMX."""
        proposal_manager.approve_proposal(proposal_id)
        proposal = proposal_manager.get_proposal(proposal_id)

        return templates.TemplateResponse("partials/proposal_card.html", {
            "request": request,
            "proposal": proposal
        })

    @app.post("/proposals/{proposal_id}/reject", response_class=HTMLResponse)
    async def reject_proposal(request: Request, proposal_id: str):
        """Reject a proposal via HTMX."""
        proposal_manager.reject_proposal(proposal_id)
        proposal = proposal_manager.get_proposal(proposal_id)

        return templates.TemplateResponse("partials/proposal_card.html", {
            "request": request,
            "proposal": proposal
        })

    # === Status ===

    @app.get("/status", response_class=HTMLResponse)
    async def status_page(request: Request):
        """Enhanced status page with all managers."""
        task_stats = task_manager.get_stats()
        budget = costs.get_budget_status()
        subagents = session_manager.list_subagents()
        proposals = proposal_manager.list_proposals(status="pending")
        projects = project_manager.list_projects(status="active")
        skills = skill_manager.list_skills()
        reflections = reflection_manager.list_reflections(limit=5)

        return templates.TemplateResponse("status.html", {
            "request": request,
            "name": identity.get_name(),
            "title": "Status",
            "budget": budget,
            "tasks": task_stats,
            "is_named": identity.is_named(),
            "subagent_count": len(subagents),
            "proposal_count": len(proposals),
            "project_count": len(projects),
            "skill_count": len(skills),
            "reflection_count": len(reflections)
        })

    # === Reflections ===

    @app.get("/reflections", response_class=HTMLResponse)
    async def reflections_page(request: Request):
        """Reflections page."""
        reflections = reflection_manager.list_reflections(limit=20)
        should_reflect = reflection_manager.should_reflect()

        return templates.TemplateResponse("reflections.html", {
            "request": request,
            "name": identity.get_name(),
            "title": "Reflections",
            "reflections": reflections,
            "should_reflect": should_reflect
        })

    @app.get("/reflection/{name}", response_class=HTMLResponse)
    async def view_reflection(request: Request, name: str):
        """View a specific reflection."""
        reflections_dir = config.entity_home / "reflections"
        file_path = reflections_dir / f"{name}.md"

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Reflection not found")

        content = file_path.read_text()

        return templates.TemplateResponse("reflection_detail.html", {
            "request": request,
            "name": identity.get_name(),
            "title": name,
            "content": content,
        })

    @app.post("/reflect", response_class=HTMLResponse)
    async def trigger_reflect(request: Request):
        """Trigger reflection via HTMX."""
        content = gateway.trigger_reflection()
        return templates.TemplateResponse("partials/reflection_result.html", {
            "request": request,
            "content": content,
        })

    # === Debug/Introspection ===

    @app.get("/debug", response_class=HTMLResponse)
    async def debug_page(request: Request):
        """Debug and introspection page."""
        # Gather system info
        tasks = task_manager.list_tasks(limit=10)
        subagents = session_manager.list_subagents()

        # Recent activity
        recent_tasks = task_manager.list_tasks(limit=20)

        # System state
        debug_info = {
            "entity_home": str(config.entity_home),
            "entity_user": config.entity_user,
            "database": str(config.entity_home / "data" / "hearth.db"),
            "providers": list(config.agents.keys()) if hasattr(config, 'agents') else [],
            "tasks_total": len(tasks),
            "subagents_running": len([s for s in subagents if s.get('status') == 'running']),
            "config_file": str(config.config_file) if hasattr(config, 'config_file') else "default"
        }

        return templates.TemplateResponse("debug.html", {
            "request": request,
            "name": identity.get_name(),
            "title": "Debug",
            "debug_info": debug_info,
            "recent_tasks": recent_tasks[:10],
            "subagents": subagents[:10]
        })

    # === Configuration ===

    @app.get("/config", response_class=HTMLResponse)
    async def config_page(request: Request):
        """Enhanced configuration page."""
        return templates.TemplateResponse("config.html", {
            "request": request,
            "name": identity.get_name(),
            "title": "Configuration",
            "config": config,
        })

    @app.post("/config", response_class=HTMLResponse)
    async def save_config(
        request: Request,
        daily_total: float = Form(...),
        daily_grok: float = Form(...),
        daily_sonnet: float = Form(...),
        weekly_opus: float = Form(...),
    ):
        """Save configuration."""
        config.budget.daily_total = daily_total
        config.budget.daily_grok = daily_grok
        config.budget.daily_sonnet = daily_sonnet
        config.budget.weekly_opus = weekly_opus
        config.save()

        return templates.TemplateResponse("partials/config_saved.html", {
            "request": request,
        })

    # === API Endpoints (for HTMX/AJAX) ===

    @app.get("/api/status")
    async def api_status():
        """API endpoint for status."""
        task_stats = task_manager.get_stats()
        budget = costs.get_budget_status()

        return {
            "name": identity.get_name(),
            "is_named": identity.is_named(),
            "budget": {
                "daily_spent": budget.daily_spent,
                "daily_budget": budget.daily_budget,
                "percent_used": budget.percent_used,
            },
            "tasks": task_stats,
            "timestamp": datetime.now().isoformat()
        }

    @app.get("/api/costs")
    async def api_costs():
        """API endpoint for costs."""
        return costs.get_budget_status().__dict__

    return app


def run_web(config: Optional[Config] = None):
    """Run the web server."""
    import uvicorn
    config = config or get_config()
    app = create_app(config)
    print(f"Starting Hearth Web UI on http://{config.web_host}:{config.web_port}")
    print(f"Features: Chat, Tasks, Skills, Projects, Proposals, Status, Reflections, Debug, Config")
    uvicorn.run(app, host=config.web_host, port=config.web_port)
