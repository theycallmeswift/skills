from pathlib import Path

import pytest

from tests.support.harness.runner import run_eval as harness_run_eval

pytest_plugins = ["tests.support.harness.reporter"]


def pytest_addoption(parser):
    parser.addoption(
        "--model",
        action="store",
        default=None,
        help="Override the model the agent uses for eval runs",
    )


@pytest.fixture(scope="session")
def project_root():
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def eval_model(request):
    return request.config.getoption("--model")


@pytest.fixture(scope="session")
def run_eval(project_root, eval_model):
    def _run(**kwargs):
        if eval_model and "model" not in kwargs:
            kwargs["model"] = eval_model
        return harness_run_eval(project_root=project_root, **kwargs)

    return _run
