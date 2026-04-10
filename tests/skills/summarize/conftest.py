from textwrap import dedent

import pytest

# --- Source content per input type ---


@pytest.fixture(scope="session")
def url_source():
    return "https://github.blog/engineering/the-technology-behind-github-models/"


@pytest.fixture(scope="session")
def pasted_source():
    return dedent("""\
        The landscape of developer education is changing rapidly. Traditional
        computer science programs are struggling to keep pace with industry demands,
        and students are increasingly turning to hands-on learning experiences to
        build the skills employers actually want. At Major League Hacking (MLH),
        we've seen this firsthand through our hackathon community, which now reaches
        1 in 3 CS students globally.

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
