from fact_verifier.services.tier import classify_tier


def test_gov_sg_is_government():
    assert classify_tier("https://www.moh.gov.sg/advisory") == "government"


def test_cpf_is_government():
    assert classify_tier("https://www.cpf.gov.sg/member") == "government"


def test_iras_is_government():
    assert classify_tier("https://www.iras.gov.sg/taxes") == "government"


def test_singstat_is_government():
    assert classify_tier("https://tablebuilder.singstat.gov.sg/api/table/metadata/M810001") == "government"


def test_cna_is_news():
    assert classify_tier("https://www.channelnewsasia.com/singapore") == "news"


def test_straits_times_is_news():
    assert classify_tier("https://www.straitstimes.com/singapore") == "news"


def test_mothership_is_news():
    assert classify_tier("https://mothership.sg/2024/01/article") == "news"


def test_todayonline_is_news():
    assert classify_tier("https://www.todayonline.com/singapore") == "news"


def test_unknown_is_other():
    assert classify_tier("https://www.reddit.com/r/singapore") == "other"


def test_facebook_is_other():
    assert classify_tier("https://www.facebook.com/post/123") == "other"


def test_invalid_url_is_other():
    assert classify_tier("not-a-url") == "other"
