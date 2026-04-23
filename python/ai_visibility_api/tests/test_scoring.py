from app.utils.scoring import opportunity_score


def test_opportunity_score_bounds():
    s = opportunity_score(volume=1000, difficulty_0_100=50, domain_visible=False, query_text="best seo tool")
    assert 0.0 <= s <= 1.0


def test_visibility_gap_effect():
    a = opportunity_score(volume=1000, difficulty_0_100=50, domain_visible=False, query_text="best seo tool")
    b = opportunity_score(volume=1000, difficulty_0_100=50, domain_visible=True, query_text="best seo tool")
    assert a > b

