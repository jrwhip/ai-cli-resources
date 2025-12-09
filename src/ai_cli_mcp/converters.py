"""
Format converters for ai-cli-resources.

Converts Claude format (Markdown + YAML frontmatter) to:
- Gemini CLI TOML commands
- Copilot CLI .agent.md files
"""

import yaml


def parse_claude(content: str) -> dict:
    """
    Parse Claude format file (YAML frontmatter + body).

    Returns:
        dict with 'frontmatter' (parsed YAML dict) and 'body' (remaining content)
    """
    content = content.strip()

    # No frontmatter
    if not content.startswith('---'):
        return {'frontmatter': {}, 'body': content}

    # Find end of frontmatter
    rest = content[3:]  # Skip opening ---
    end_idx = rest.find('\n---')

    if end_idx == -1:
        # Malformed - no closing ---, treat as no frontmatter
        return {'frontmatter': {}, 'body': content}

    yaml_content = rest[:end_idx].strip()
    body = rest[end_idx + 4:].strip()  # Skip \n---

    # Parse YAML
    try:
        frontmatter = yaml.safe_load(yaml_content) or {}
    except yaml.YAMLError:
        frontmatter = {}

    return {'frontmatter': frontmatter, 'body': body}


def to_gemini_toml(content: str) -> str:
    """
    Convert Claude command format to Gemini TOML format.

    Conversions:
    - $ARGUMENTS → {{args}}
    - description → description field
    - argument-hint, allowed-tools → ignored (no Gemini equivalent)
    """
    parsed = parse_claude(content)
    frontmatter = parsed['frontmatter']
    body = parsed['body']

    # Replace argument placeholder
    body = body.replace('$ARGUMENTS', '{{args}}')

    # Escape triple quotes in body if present
    body = body.replace('"""', '\\"\\"\\"')

    # Build TOML
    lines = []

    if 'description' in frontmatter:
        # Escape quotes in description
        desc = frontmatter['description'].replace('"', '\\"')
        lines.append(f'description = "{desc}"')

    lines.append(f'prompt = """\n{body}\n"""')

    return '\n'.join(lines)


def to_copilot_agent(content: str) -> str:
    """
    Convert Claude agent format to Copilot .agent.md format.

    Conversions:
    - name → name (lowercase-with-hyphens for filename)
    - description → description
    - tools → mapped to Copilot equivalents
    - body → unchanged (Markdown works in both)
    """
    parsed = parse_claude(content)
    frontmatter = parsed['frontmatter']
    body = parsed['body']

    # Tool mapping: Claude → Copilot
    tool_map = {
        'Read': 'read',
        'Write': 'edit',
        'Edit': 'edit',
        'Grep': 'search',
        'Glob': 'search',
        'Bash': 'shell',
        'Task': 'custom-agent',
    }

    # Build new frontmatter
    new_fm = {}

    if 'name' in frontmatter:
        new_fm['name'] = frontmatter['name']

    if 'description' in frontmatter:
        new_fm['description'] = frontmatter['description']

    # Map tools if present
    if 'tools' in frontmatter:
        claude_tools = frontmatter['tools']
        if isinstance(claude_tools, str):
            claude_tools = [t.strip() for t in claude_tools.split(',')]

        copilot_tools = set()
        for tool in claude_tools:
            mapped = tool_map.get(tool, tool.lower())
            copilot_tools.add(mapped)

        if copilot_tools:
            new_fm['tools'] = sorted(list(copilot_tools))

    # Build output
    if new_fm:
        yaml_str = yaml.dump(new_fm, default_flow_style=False, sort_keys=False).strip()
        return f"---\n{yaml_str}\n---\n\n{body}"
    else:
        return body
