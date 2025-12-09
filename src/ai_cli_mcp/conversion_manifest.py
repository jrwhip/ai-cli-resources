"""
Conversion manifest for ai-cli-resources.

Classifies commands and agents into tiers for multi-CLI conversion:
- Tier 1: No Claude references, convert as-is
- Tier 2: Path/file references only, convert with path replacement
- Tier 3: Claude-specific features, skip for other CLIs
"""

# Commands by tier
COMMAND_TIERS = {
    'tier1': [
        # Mental models (12)
        'consider/10-10-10',
        'consider/5-whys',
        'consider/eisenhower-matrix',
        'consider/first-principles',
        'consider/inversion',
        'consider/occams-razor',
        'consider/one-thing',
        'consider/opportunity-cost',
        'consider/pareto',
        'consider/second-order',
        'consider/swot',
        'consider/via-negativa',
        # Other generic commands (9)
        'audit-skill',
        'audit-slash-command',
        'audit-subagent',
        'create-plan',
        'create-slash-command',
        'debug',
        'heal-skill',
        'run-plan',
        'run-prompt',
    ],
    'tier2': [
        # Path references only - need replacement
        'check-todos',
        'create-prompt',
    ],
    'tier3': [
        # Claude-specific features - skip
        'add-to-todos',
        'create-agent-skill',
        'create-hook',
        'create-meta-prompt',
        'create-subagent',
        'whats-next',
    ],
}

# Agents by tier
AGENT_TIERS = {
    'tier1': [
        # Generic agents
        'architect',
        'code-auditor',
        'code-reviewer',
        'mentor',
        'refactor',
    ],
    'tier2': [
        # Path references only
        'angular-perfectionist-reviewer',
    ],
    'tier3': [
        # Claude Code specific auditors - skip
        'skill-auditor',
        'slash-command-auditor',
        'subagent-auditor',
    ],
}

# Path replacements per CLI
PATH_REPLACEMENTS = {
    'gemini': [
        ('~/.claude/skills/', '~/.gemini/skills/'),
        ('~/.claude/commands/', '~/.gemini/commands/'),
        ('~/.claude/agents/', '~/.gemini/agents/'),
        ('~/.claude/', '~/.gemini/'),
        ('.claude/skills/', '.gemini/skills/'),
        ('.claude/commands/', '.gemini/commands/'),
        ('.claude/agents/', '.gemini/agents/'),
        ('.claude/', '.gemini/'),
        ('CLAUDE.md', 'GEMINI.md'),
    ],
    'copilot': [
        ('~/.claude/skills/', '~/.copilot/'),
        ('~/.claude/commands/', '~/.copilot/'),
        ('~/.claude/agents/', '~/.copilot/agents/'),
        ('~/.claude/', '~/.copilot/'),
        ('.claude/skills/', '.github/'),
        ('.claude/commands/', '.github/'),
        ('.claude/agents/', '.github/agents/'),
        ('.claude/', '.github/'),
        ('CLAUDE.md', '.github/copilot-instructions.md'),
    ],
}


def get_tier(name: str, resource_type: str) -> int:
    """Get tier for a resource (1, 2, or 3)."""
    tiers = COMMAND_TIERS if resource_type == 'command' else AGENT_TIERS

    for tier_num, tier_name in [(1, 'tier1'), (2, 'tier2'), (3, 'tier3')]:
        if name in tiers[tier_name]:
            return tier_num

    # Default to tier 3 (skip) if not found
    return 3


def get_convertible_commands(cli: str) -> list:
    """Get list of commands convertible for a CLI (tier 1 + tier 2)."""
    return COMMAND_TIERS['tier1'] + COMMAND_TIERS['tier2']


def get_convertible_agents(cli: str) -> list:
    """Get list of agents convertible for a CLI (tier 1 + tier 2)."""
    return AGENT_TIERS['tier1'] + AGENT_TIERS['tier2']


def apply_path_replacements(content: str, cli: str) -> str:
    """Apply path replacements for a target CLI."""
    if cli not in PATH_REPLACEMENTS:
        return content

    for old, new in PATH_REPLACEMENTS[cli]:
        content = content.replace(old, new)

    return content
