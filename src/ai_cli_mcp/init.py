"""
Cross-platform initialization for ai-cli-resources.

Handles:
- Creating .ai-cli/ directory structure in workspace
- Copying default resources to workspace
- Registering MCP server with CLIs (Claude, Gemini, Copilot)
- Creating symlinks (Unix) or copying files (Windows) for commands/agents
"""

import json
import platform
import shutil
from pathlib import Path


def get_package_root() -> Path:
    """Get the package root directory (where bundled defaults live)."""
    return Path(__file__).parent.parent.parent


def is_windows() -> bool:
    return platform.system() == "Windows"


def get_home() -> Path:
    return Path.home()


def create_workspace_structure(workspace: Path) -> None:
    """Create .ai-cli directory structure in workspace."""
    ai_cli = workspace / ".ai-cli"
    dirs = [
        ai_cli / "shared" / "commands",
        ai_cli / "shared" / "skills",
        ai_cli / "shared" / "agents",
        ai_cli / "shared" / "context",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    print(f"Created {ai_cli}")


def copy_defaults(workspace: Path) -> None:
    """Copy default resources from package to workspace."""
    package_root = get_package_root()
    dest = workspace / ".ai-cli" / "shared"

    for category in ["commands", "skills", "agents", "context"]:
        src_dir = package_root / category
        dst_dir = dest / category

        if not src_dir.exists():
            continue

        # For skills, copy entire directories (each skill is a directory with SKILL.md)
        if category == "skills":
            for skill_dir in src_dir.iterdir():
                if skill_dir.is_dir():
                    dst_skill = dst_dir / skill_dir.name
                    if not dst_skill.exists():
                        shutil.copytree(skill_dir, dst_skill)
                        print(f"  Copied {category}/{skill_dir.name}/")
                    else:
                        print(f"  Skipped {category}/{skill_dir.name}/ (exists)")
        else:
            # For commands, agents, context - copy .md files
            for src_file in src_dir.glob("*.md"):
                dst_file = dst_dir / src_file.name
                if not dst_file.exists():
                    shutil.copy2(src_file, dst_file)
                    print(f"  Copied {category}/{src_file.name}")
                else:
                    print(f"  Skipped {category}/{src_file.name} (exists)")

            # Also handle subdirectories for commands (like consider/)
            if category == "commands":
                for subdir in src_dir.iterdir():
                    if subdir.is_dir():
                        dst_subdir = dst_dir / subdir.name
                        if not dst_subdir.exists():
                            shutil.copytree(subdir, dst_subdir)
                            print(f"  Copied {category}/{subdir.name}/")
                        else:
                            print(f"  Skipped {category}/{subdir.name}/ (exists)")


def get_mcp_config(workspace: Path) -> dict:
    """Generate MCP server configuration."""
    return {
        "ai-cli": {
            "command": "ai-cli",
            "args": [],
            "env": {
                "AI_CLI_WORKSPACE": str(workspace)
            }
        }
    }


def update_json_file(path: Path, key: str, value: dict) -> bool:
    """Update a JSON config file, merging the new value."""
    try:
        if path.exists():
            with open(path) as f:
                data = json.load(f)
        else:
            data = {}

        if key not in data:
            data[key] = {}

        data[key].update(value)

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        return True
    except Exception as e:
        print(f"  Warning: Could not update {path}: {e}")
        return False


def create_or_update_symlink(src: Path, dst: Path) -> None:
    """Create or update a symlink, removing existing if necessary."""
    if dst.is_symlink():
        dst.unlink()
    elif dst.exists():
        shutil.rmtree(dst)

    dst.parent.mkdir(parents=True, exist_ok=True)

    if is_windows():
        shutil.copytree(src, dst)
        print(f"  Copied {src.name} to {dst}")
    else:
        dst.symlink_to(src)
        print(f"  Symlinked: {dst} -> {src}")


def setup_claude(workspace: Path) -> None:
    """Configure Claude CLI."""
    print("\nClaude CLI:")

    shared_dir = workspace / ".ai-cli" / "shared"

    # Update ~/.claude.json with MCP server (global)
    claude_json = get_home() / ".claude.json"
    mcp_config = get_mcp_config(workspace)

    if claude_json.exists():
        try:
            with open(claude_json) as f:
                data = json.load(f)
        except Exception:
            data = {}
    else:
        data = {}

    if "mcpServers" not in data:
        data["mcpServers"] = {}

    data["mcpServers"].update(mcp_config)

    with open(claude_json, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Updated {claude_json}")

    # Symlink commands to workspace's .ai-cli/shared/commands
    commands_src = shared_dir / "commands"
    commands_dst = get_home() / ".claude" / "commands" / "ai"
    create_or_update_symlink(commands_src, commands_dst)

    # Symlink agents to workspace's .ai-cli/shared/agents
    agents_src = shared_dir / "agents"
    agents_dst = get_home() / ".claude" / "agents" / "ai"
    create_or_update_symlink(agents_src, agents_dst)

    # Symlink skills to workspace's .ai-cli/shared/skills
    skills_src = shared_dir / "skills"
    skills_dst = get_home() / ".claude" / "skills" / "ai"
    create_or_update_symlink(skills_src, skills_dst)


def setup_gemini(workspace: Path) -> None:
    """Configure Gemini CLI."""
    print("\nGemini CLI:")

    shared_dir = workspace / ".ai-cli" / "shared"

    gemini_settings = get_home() / ".gemini" / "settings.json"
    mcp_config = get_mcp_config(workspace)

    if update_json_file(gemini_settings, "mcpServers", mcp_config):
        print(f"  Updated {gemini_settings}")

    # Symlink commands to workspace's .ai-cli/shared/commands
    commands_src = shared_dir / "commands"
    commands_dst = get_home() / ".gemini" / "commands" / "ai"
    create_or_update_symlink(commands_src, commands_dst)


def setup_copilot(workspace: Path) -> None:
    """Configure Copilot CLI."""
    print("\nCopilot CLI:")

    copilot_config = get_home() / ".copilot" / "mcp-config.json"
    mcp_config = get_mcp_config(workspace)

    if update_json_file(copilot_config, "mcpServers", mcp_config):
        print(f"  Updated {copilot_config}")


def initialize_workspace(workspace: Path) -> int:
    """Initialize ai-cli-resources for a workspace."""
    print(f"Initializing ai-cli-resources")
    print(f"Workspace: {workspace}")
    print("=" * 50)

    if not workspace.exists():
        print(f"Error: Directory does not exist: {workspace}")
        return 1

    # Create workspace structure
    print("\nCreating workspace structure...")
    create_workspace_structure(workspace)

    # Copy defaults to workspace
    print("\nCopying default resources...")
    copy_defaults(workspace)

    # Setup CLIs
    print("\nConfiguring AI CLIs...")
    setup_claude(workspace)
    setup_gemini(workspace)
    setup_copilot(workspace)

    print("\n" + "=" * 50)
    print("Setup complete!")
    print(f"\nWorkspace: {workspace}")
    print(f"Resources: {workspace / '.ai-cli' / 'shared'}")
    print("\nClaude Code:")
    print("  Commands: /ai:* (e.g., /ai:add-to-todos)")
    print("  Agents:   @ai/* (e.g., @ai/code-reviewer)")
    print("  Skills:   Available in ~/.claude/skills/ai/")
    print("\nGemini/Copilot: Use MCP tools (list_shared_*, get_shared_*)")
    print("\nRestart your CLI to load the MCP server.")

    return 0
