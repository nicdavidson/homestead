from common.models import AgentIdentity, AGENTS, format_agent_message


def test_agent_identity():
    """Create AgentIdentity, verify fields."""
    agent = AgentIdentity(
        name="tester",
        display_name="Test Agent",
        emoji="\U0001f916",
        model_tier="sonnet",
    )
    assert agent.name == "tester"
    assert agent.display_name == "Test Agent"
    assert agent.emoji == "\U0001f916"
    assert agent.model_tier == "sonnet"


def test_agents_registry():
    """Verify all expected agents in AGENTS dict."""
    expected = {"herald", "nightshift", "researcher", "steward", "hearth"}
    assert set(AGENTS.keys()) == expected

    # Each value should be an AgentIdentity with all fields populated
    for name, agent in AGENTS.items():
        assert isinstance(agent, AgentIdentity)
        assert agent.name == name
        assert len(agent.display_name) > 0
        assert len(agent.emoji) > 0
        assert agent.model_tier in ("grok", "sonnet", "opus", "claude-cli")


def test_format_agent_message_herald():
    """Herald messages have no prefix."""
    result = format_agent_message("herald", "Hello there")
    assert result == "Hello there"


def test_format_agent_message_other():
    """Other agents get emoji+name prefix."""
    result = format_agent_message("nightshift", "Good evening")
    agent = AGENTS["nightshift"]
    expected = f"{agent.emoji} <b>{agent.display_name}</b>\n\nGood evening"
    assert result == expected


def test_format_agent_message_unknown():
    """Unknown agent gets bracketed name."""
    result = format_agent_message("mystery", "Who am I?")
    assert result == "<b>[mystery]</b>\n\nWho am I?"
