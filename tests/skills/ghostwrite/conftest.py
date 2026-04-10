from textwrap import dedent

import pytest


@pytest.fixture(scope="session")
def email_source():
    return dedent("""\
        Hey team, wanted to give a quick update on the hackathon season.
        We've now supported 500,000 developers across 1,500 events this year.
        The new platform features are driving 30% more signups compared to last quarter.
        Check out the dashboard at https://mlh.io/dashboard for the full breakdown.
        Also, Sarah from DevRel mentioned that the sponsor satisfaction scores
        are the highest they've ever been, which is great news for renewals.
        Let me know if you have any questions about the numbers.
        Best regards,
        Mike""")


@pytest.fixture(scope="session")
def linkedin_source():
    return dedent("""\
        I wanted to share some exciting news about what we've been building at MLH.
        This year we reached an incredible milestone of supporting 500,000 developers
        through 1,500 hackathons across 65 countries. Our community now includes
        1 in 3 computer science students globally. We've also launched a new
        fellowship program that has placed 200 early-career developers at companies
        like GitHub, Meta, and Shopify. The feedback from both fellows and companies
        has been overwhelmingly positive, with a 95% satisfaction rate.
        I'm so grateful to our team and community for making this possible.
        None of this happens without the organizers, mentors, and sponsors who
        believe in learning by doing. Here's to the next million developers.""")


@pytest.fixture(scope="session")
def slack_source():
    return dedent("""\
        Hey everyone, I wanted to give a heads up that we're planning to migrate
        the event platform to the new infrastructure next Tuesday. This should
        improve load times by about 40% based on our staging tests. If your team
        has any critical events running that week, please flag them in #ops so
        we can coordinate timing. Thanks!""")


@pytest.fixture(scope="session")
def blog_source():
    return dedent("""\
        The landscape of developer education is changing rapidly. Traditional
        computer science programs are struggling to keep pace with industry demands,
        and students are increasingly turning to hands-on learning experiences to
        build the skills employers actually want. At MLH, we've seen this firsthand
        through our hackathon community, which now reaches 1 in 3 CS students globally.

        Over the past year, we've supported 500,000 developers across 1,500 events
        in 65 countries. But the numbers only tell part of the story. What really
        matters is the transformation we see in participants. Students who attend
        their first hackathon often describe it as a turning point, the moment they
        went from studying code to shipping products.

        Our fellowship program has been another proof point. We've placed 200
        early-career developers at companies like GitHub, Meta, and Shopify, with
        a 95% satisfaction rate from both fellows and host companies. The common
        thread? Learning by doing beats learning by reading every time.

        If you're a student wondering whether to attend a hackathon, or an employer
        considering hands-on hiring, the data speaks for itself. Check out
        https://mlh.io/impact for the full report.""")


@pytest.fixture(scope="session")
def email_prompt(email_source):
    return f"Rewrite this as an email in my voice:\n\n{email_source}"


@pytest.fixture(scope="session")
def linkedin_prompt(linkedin_source):
    return f"Rewrite this as a LinkedIn post:\n\n{linkedin_source}"


@pytest.fixture(scope="session")
def slack_prompt(slack_source):
    return f"Rewrite this as a Slack message:\n\n{slack_source}"


@pytest.fixture(scope="session")
def blog_prompt(blog_source):
    return f"Rewrite this as a blog post for DEV:\n\n{blog_source}"


# --- Cached outputs (one CLI call per medium) ---


@pytest.fixture(scope="session")
def email_output(runner, email_prompt):
    return runner.run(email_prompt)


@pytest.fixture(scope="session")
def linkedin_output(runner, linkedin_prompt):
    return runner.run(linkedin_prompt)


@pytest.fixture(scope="session")
def slack_output(runner, slack_prompt):
    return runner.run(slack_prompt)


@pytest.fixture(scope="session")
def blog_output(runner, blog_prompt):
    return runner.run(blog_prompt)
