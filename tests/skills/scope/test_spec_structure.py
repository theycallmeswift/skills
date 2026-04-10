def test_has_goal_section(result):
    assert result.file_contains("references/specs/*.md", regex=r"(?im)^##\s*Goal")


def test_has_non_goals_section(result):
    assert result.file_contains("references/specs/*.md", regex=r"(?im)^##\s*Non.?Goals")


def test_has_approach_section(result):
    assert result.file_contains("references/specs/*.md", regex=r"(?im)^##\s*Approach")


def test_has_components_section(result):
    assert result.file_contains("references/specs/*.md", regex=r"(?im)^##\s*Components")


def test_has_testing_section(result):
    assert result.file_contains("references/specs/*.md", regex=r"(?im)^##\s*Testing")


def test_mentions_routing(result):
    assert result.file_contains(
        "references/specs/*.md",
        regex=r"(?i)(allowlist|routing table|repo.{0,10}channel)",
    )


def test_mentions_durable_queue(result):
    assert result.file_contains(
        "references/specs/*.md",
        regex=r"(?i)(Redis|BullMQ|persistent queue|durable queue)",
    )


def test_mentions_events(result):
    assert result.file_contains("references/specs/*.md", text="opened")
    assert result.file_contains("references/specs/*.md", text="ready_for_review")
    assert result.file_contains("references/specs/*.md", text="closed")


def test_mentions_out_of_scope(result):
    assert result.file_contains("references/specs/*.md", regex=r"(?i)out of scope")


def test_mentions_infrastructure(result):
    assert result.file_contains("references/specs/*.md", text="Fly.io")
    assert result.file_contains("references/specs/*.md", text="Node.js")


def test_mentions_yaml_config(result):
    assert result.file_contains("references/specs/*.md", regex=r"(?i)YAML")
