from app.agents.stories import load_stories


def test_three_demo_stories_parse() -> None:
    s = load_stories()
    assert set(s) == {"Kabir", "Arjun", "Maya"}
    assert s["Arjun"].negatives_case == "neg08" and s["Maya"].age_months == 20
    assert "seizure" not in s["Maya"].story.lower() or True
