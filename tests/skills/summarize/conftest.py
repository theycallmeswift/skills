from textwrap import dedent

import pytest

# --- Source content per input type ---


@pytest.fixture(scope="session")
def url_source():
    return "https://github.blog/news-insights/product-news/introducing-github-models/"


@pytest.fixture(scope="session")
def pasted_source():
    return dedent("""\
        Remote work is reshaping how engineering teams operate. A survey of 2,400
        engineering managers found that 68% of teams are now fully distributed,
        up from 29% in 2019. The shift has forced companies to rethink everything
        from code review workflows to how they run standups.

        The biggest surprise in the data is about productivity. Teams that adopted
        async-first communication reported 23% faster cycle times compared to those
        that kept synchronous meetings as the default. The key factor wasn't the
        tools they used but whether leadership explicitly set norms around response
        times and documentation.

        Not everything improved, though. Junior developer onboarding took 40% longer
        in fully remote setups. Companies that assigned dedicated mentors and paired
        new hires on real projects from day one cut that gap to just 12%. The pattern
        is clear: remote work scales well for experienced teams but requires deliberate
        investment in onboarding infrastructure.

        For teams considering the shift, the report recommends starting with async
        standups and written design docs before eliminating offices entirely. The
        full dataset is available at https://stateofremote.dev/2025.""")


@pytest.fixture(scope="session")
def file_source():
    return dedent("""\
        # Hackathon Organizer Guide

        Running a successful hackathon requires careful planning across several
        key areas: venue logistics, sponsor management, mentorship coordination,
        and participant experience.

        ## Venue and Logistics

        Book your venue at least 3 months in advance. You need reliable WiFi
        that can handle 500+ simultaneous connections, enough power outlets for
        every table, and a layout that encourages collaboration. Budget $15-25
        per participant for food across the full 24-36 hour event.

        ## Sponsorship

        Start outreach 4-6 months before the event. Companies typically commit
        $5,000-$25,000 for hackathon sponsorships. Offer API credits, mentors,
        and branded challenges as activation options beyond just logo placement.

        ## Mentorship

        Recruit 1 mentor per 10 participants. Brief them on common issues:
        environment setup, API authentication, and deployment. The best mentors
        ask questions rather than writing code for teams.

        ## Judging

        Use a rubric with 4 categories: technical complexity, design, impact,
        and presentation. Give judges 3 minutes per demo with 1 minute for Q&A.
        Calibrate scoring with a practice round before demos begin.""")


# --- Prompts per input type ---


@pytest.fixture(scope="session")
def url_prompt(url_source):
    return f"Summarize this: {url_source}"


@pytest.fixture(scope="session")
def pasted_prompt(pasted_source):
    return f"Summarize this:\n\n{pasted_source}"


@pytest.fixture(scope="session")
def file_prompt(runner, file_source):
    """Write source to a .md file in the runner's cwd, then ask to summarize it."""
    file_path = runner.cwd / "hackathon-guide.md"
    file_path.write_text(file_source)
    return f"Summarize this file: {file_path}"


# --- Cached outputs (one CLI call per input type) ---


@pytest.fixture(scope="session")
def url_output(runner, url_prompt):
    return runner.run(url_prompt)


@pytest.fixture(scope="session")
def pasted_output(runner, pasted_prompt):
    return runner.run(pasted_prompt)


@pytest.fixture(scope="session")
def file_output(runner, file_prompt):
    return runner.run(file_prompt)
