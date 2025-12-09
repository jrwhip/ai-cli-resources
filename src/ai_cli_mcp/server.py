#!/usr/bin/env python3
"""
AI CLI MCP Server - Shared tools for Claude, Gemini, and Copilot CLIs

Provides unified tools for managing projects, git operations, and accessing
shared commands, skills, and agents.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ai-cli")

# Workspace path from environment or None (will be set at runtime)
_workspace: Optional[Path] = None

# Package root (where agents/, commands/, skills/ live)
_package_root: Optional[Path] = None


def get_package_root() -> Path:
    """Get the package root directory (where resources are bundled)."""
    global _package_root
    if _package_root is None:
        # Go up from src/ai_cli_mcp/ to package root
        _package_root = Path(__file__).parent.parent.parent
    return _package_root


def get_workspace() -> Path:
    """Get the workspace path."""
    global _workspace
    if _workspace is None:
        ws = os.environ.get("AI_CLI_WORKSPACE")
        if ws:
            _workspace = Path(ws).expanduser().resolve()
        else:
            _workspace = Path.cwd()
    return _workspace


def get_shared_dir() -> Path:
    """Get the shared resources directory (workspace-local or bundled fallback)."""
    workspace = get_workspace()
    local_shared = workspace / ".ai-cli" / "shared"

    if local_shared.exists():
        return local_shared

    # Fall back to bundled defaults in package
    return get_package_root()


def get_commands_dir() -> Path:
    return get_shared_dir() / "commands"


def get_skills_dir() -> Path:
    return get_shared_dir() / "skills"


def get_agents_dir() -> Path:
    return get_shared_dir() / "agents"


def get_context_dir() -> Path:
    return get_shared_dir() / "context"


# ============================================================================
# PROJECT TOOLS
# ============================================================================

@mcp.tool()
def list_projects() -> str:
    """List all projects in the workspace with their status."""
    workspace = get_workspace()
    projects = []

    for item in workspace.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            project_info = {"name": item.name, "path": str(item)}

            pkg = item / "package.json"
            if pkg.exists():
                try:
                    with open(pkg) as f:
                        data = json.load(f)
                        project_info["type"] = data.get("name", "unknown")
                        project_info["version"] = data.get("version", "unknown")
                except Exception:
                    pass

            if (item / ".git").exists():
                project_info["git"] = True
                try:
                    result = subprocess.run(
                        ["git", "status", "--porcelain"],
                        cwd=item,
                        capture_output=True,
                        text=True
                    )
                    project_info["dirty"] = bool(result.stdout.strip())
                except Exception:
                    pass

            project_info["has_claude"] = (item / ".claude").exists() or (item / "CLAUDE.md").exists()
            project_info["has_gemini"] = (item / ".gemini").exists() or (item / "GEMINI.md").exists()

            projects.append(project_info)

    return json.dumps(projects, indent=2)


@mcp.tool()
def get_project_context(project_name: str) -> str:
    """Get the full context for a project including its CLAUDE.md, package.json, etc."""
    workspace = get_workspace()
    project_path = workspace / project_name

    if not project_path.exists():
        return f"Error: Project '{project_name}' not found in {workspace}"

    context = {"project": project_name, "path": str(project_path)}

    claude_md = project_path / "CLAUDE.md"
    if claude_md.exists():
        context["claude_md"] = claude_md.read_text()

    pkg = project_path / "package.json"
    if pkg.exists():
        try:
            with open(pkg) as f:
                context["package"] = json.load(f)
        except Exception as e:
            context["package_error"] = str(e)

    context["structure"] = [
        item.name for item in project_path.iterdir()
        if not item.name.startswith('.') and item.name != "node_modules"
    ][:20]

    return json.dumps(context, indent=2)


# ============================================================================
# GIT TOOLS
# ============================================================================

@mcp.tool()
def git_status(project_name: str) -> str:
    """Get git status for a project."""
    workspace = get_workspace()
    project_path = workspace / project_name

    if not project_path.exists():
        return f"Error: Project '{project_name}' not found"

    if not (project_path / ".git").exists():
        return f"Error: Project '{project_name}' is not a git repository"

    try:
        result = subprocess.run(
            ["git", "status"],
            cwd=project_path,
            capture_output=True,
            text=True
        )
        return result.stdout or result.stderr
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def git_diff(project_name: str, staged: bool = False) -> str:
    """Get git diff for a project. Set staged=True for staged changes only."""
    workspace = get_workspace()
    project_path = workspace / project_name

    if not project_path.exists():
        return f"Error: Project '{project_name}' not found"

    cmd = ["git", "diff"]
    if staged:
        cmd.append("--staged")

    try:
        result = subprocess.run(
            cmd,
            cwd=project_path,
            capture_output=True,
            text=True
        )
        return result.stdout or "No changes"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def git_log(project_name: str, count: int = 10) -> str:
    """Get recent git commits for a project."""
    workspace = get_workspace()
    project_path = workspace / project_name

    if not project_path.exists():
        return f"Error: Project '{project_name}' not found"

    try:
        result = subprocess.run(
            ["git", "log", f"-{count}", "--oneline", "--decorate"],
            cwd=project_path,
            capture_output=True,
            text=True
        )
        return result.stdout or result.stderr
    except Exception as e:
        return f"Error: {e}"


# ============================================================================
# SHARED RESOURCES
# ============================================================================

@mcp.tool()
def list_shared_commands() -> str:
    """List all available shared commands."""
    commands = []
    commands_dir = get_commands_dir()
    if commands_dir.exists():
        for cmd_file in commands_dir.rglob("*.md"):
            rel_path = cmd_file.relative_to(commands_dir)
            commands.append({"name": str(rel_path.with_suffix('')), "file": str(cmd_file)})
    return json.dumps(commands, indent=2)


@mcp.tool()
def get_shared_command(command_name: str) -> str:
    """Get the content of a shared command."""
    cmd_file = get_commands_dir() / f"{command_name}.md"
    if cmd_file.exists():
        return cmd_file.read_text()
    return f"Error: Command '{command_name}' not found"


@mcp.tool()
def list_shared_skills() -> str:
    """List all available shared skills."""
    skills = []
    skills_dir = get_skills_dir()
    if skills_dir.exists():
        # Skills are directories with SKILL.md inside
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    skills.append({"name": skill_dir.name, "file": str(skill_file)})
    return json.dumps(skills, indent=2)


@mcp.tool()
def get_shared_skill(skill_name: str) -> str:
    """Get the content of a shared skill."""
    skill_file = get_skills_dir() / skill_name / "SKILL.md"
    if skill_file.exists():
        return skill_file.read_text()
    return f"Error: Skill '{skill_name}' not found"


@mcp.tool()
def list_shared_agents() -> str:
    """List all available shared agents."""
    agents = []
    agents_dir = get_agents_dir()
    if agents_dir.exists():
        for agent_file in agents_dir.glob("*.md"):
            agents.append({"name": agent_file.stem, "file": str(agent_file)})
    return json.dumps(agents, indent=2)


@mcp.tool()
def get_shared_agent(agent_name: str) -> str:
    """Get the content of a shared agent."""
    agent_file = get_agents_dir() / f"{agent_name}.md"
    if agent_file.exists():
        return agent_file.read_text()
    return f"Error: Agent '{agent_name}' not found"


@mcp.tool()
def list_shared_context() -> str:
    """List all available shared context documents."""
    docs = []
    context_dir = get_context_dir()
    if context_dir.exists():
        for doc_file in context_dir.glob("*.md"):
            docs.append({"name": doc_file.stem, "file": str(doc_file)})
    return json.dumps(docs, indent=2)


@mcp.tool()
def get_shared_context(context_name: str) -> str:
    """Get the content of a shared context document."""
    ctx_file = get_context_dir() / f"{context_name}.md"
    if ctx_file.exists():
        return ctx_file.read_text()
    return f"Error: Context '{context_name}' not found"


# ============================================================================
# DEV TOOLS
# ============================================================================

@mcp.tool()
def run_npm_script(project_name: str, script: str) -> str:
    """Run an npm/pnpm script in a project. Returns the output."""
    workspace = get_workspace()
    project_path = workspace / project_name

    if not project_path.exists():
        return f"Error: Project '{project_name}' not found"

    pkg = project_path / "package.json"
    if not pkg.exists():
        return f"Error: No package.json in '{project_name}'"

    if (project_path / "pnpm-lock.yaml").exists():
        cmd = ["pnpm", "run", script]
    elif (project_path / "yarn.lock").exists():
        cmd = ["yarn", script]
    else:
        cmd = ["npm", "run", script]

    try:
        result = subprocess.run(
            cmd,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=120
        )
        output = result.stdout
        if result.stderr:
            output += "\n\nSTDERR:\n" + result.stderr
        return output or "Script completed with no output"
    except subprocess.TimeoutExpired:
        return "Error: Script timed out after 120 seconds"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def check_build(project_name: str) -> str:
    """Run type-check/build on a project to check for errors."""
    workspace = get_workspace()
    project_path = workspace / project_name

    if not project_path.exists():
        return f"Error: Project '{project_name}' not found"

    pkg = project_path / "package.json"
    if pkg.exists():
        try:
            with open(pkg) as f:
                data = json.load(f)
                scripts = data.get("scripts", {})

                for script in ["typecheck", "type-check", "tsc", "build"]:
                    if script in scripts:
                        return run_npm_script(project_name, script)

                return "No typecheck or build script found in package.json"
        except Exception as e:
            return f"Error reading package.json: {e}"

    return "No package.json found"


# ============================================================================
# ENTRY POINT
# ============================================================================

def run_server(workspace: Optional[str] = None) -> int:
    """Run the MCP server."""
    global _workspace
    if workspace:
        _workspace = Path(workspace).expanduser().resolve()
    mcp.run()
    return 0
