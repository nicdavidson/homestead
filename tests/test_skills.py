from common.skills import SkillManager


def test_save_and_list(skills_dir):
    """Save a skill, list it back."""
    mgr = SkillManager(skills_dir)
    mgr.save("git-rebase", "Interactive rebase workflow", "Steps to rebase...", tags=["git"])

    skills = mgr.list_skills()
    assert len(skills) == 1
    assert skills[0].name == "git-rebase"
    assert skills[0].description == "Interactive rebase workflow"
    assert skills[0].content == "Steps to rebase..."
    assert skills[0].tags == ["git"]


def test_get_skill(skills_dir):
    """Save and retrieve by name."""
    mgr = SkillManager(skills_dir)
    mgr.save("deploy", "Deploy to prod", "Run deploy script", tags=["ops"])

    skill = mgr.get("deploy")
    assert skill is not None
    assert skill.name == "deploy"
    assert skill.description == "Deploy to prod"
    assert skill.content == "Run deploy script"

    # Non-existent skill returns None
    assert mgr.get("nonexistent") is None


def test_search(skills_dir):
    """Save multiple, search by name/description/tag."""
    mgr = SkillManager(skills_dir)
    mgr.save("git-rebase", "Interactive rebase", "body1", tags=["git", "workflow"])
    mgr.save("git-merge", "Merge branches", "body2", tags=["git"])
    mgr.save("docker-build", "Build docker images", "body3", tags=["docker", "workflow"])

    # Search by name substring
    results = mgr.search("git")
    assert len(results) == 2
    names = {s.name for s in results}
    assert names == {"git-rebase", "git-merge"}

    # Search by description substring
    results = mgr.search("docker")
    assert len(results) == 1
    assert results[0].name == "docker-build"

    # Search by tag
    results = mgr.search("workflow")
    assert len(results) == 2


def test_parse_frontmatter(skills_dir):
    """Skill with YAML front-matter parsed correctly."""
    content = "---\nname: my-skill\ndescription: A great skill\ntags: alpha, beta\n---\n\nThe body here."
    (skills_dir / "my-skill.md").write_text(content, encoding="utf-8")

    mgr = SkillManager(skills_dir)
    skill = mgr.get("my-skill")
    assert skill is not None
    assert skill.name == "my-skill"
    assert skill.description == "A great skill"
    assert skill.tags == ["alpha", "beta"]
    assert skill.content == "The body here."


def test_no_frontmatter(skills_dir):
    """Skill without front-matter uses filename as name."""
    (skills_dir / "plain-skill.md").write_text("Just some content", encoding="utf-8")

    mgr = SkillManager(skills_dir)
    skill = mgr.get("plain-skill")
    assert skill is not None
    assert skill.name == "plain-skill"
    assert skill.description == ""
    assert skill.tags == []
    assert skill.content == "Just some content"
