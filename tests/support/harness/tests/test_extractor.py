import textwrap
from unittest.mock import patch

from pydantic import BaseModel, Field, field_validator

from tests.support.harness.extractor import extract_fields


class SimpleOutput(BaseModel):
    title: str
    summary: str
    items: list[str] = Field(min_length=1, max_length=5)


def test_extract_fields_from_mock():
    mock_result = {"title": "Test", "summary": "A summary", "items": ["one", "two"]}
    with patch("tests.support.harness.extractor._extract_async") as mock_extract:
        mock_extract.return_value = mock_result
        result = extract_fields("some content", SimpleOutput)
        assert isinstance(result, SimpleOutput)
        assert result.title == "Test"
        assert result.items == ["one", "two"]


class StrictOutput(BaseModel):
    name: str
    count: int

    @field_validator("count")
    @classmethod
    def count_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("count must be positive")
        return v


def test_extract_fields_validates_with_pydantic():
    mock_result = {"name": "Test", "count": -1}
    with patch("tests.support.harness.extractor._extract_async") as mock_extract:
        mock_extract.return_value = mock_result
        try:
            extract_fields("some content", StrictOutput)
            assert False, "Should have raised ValidationError"
        except Exception as e:
            assert "count must be positive" in str(e)


def test_extract_fields_generates_schema():
    """Verify model_json_schema() produces a usable schema."""
    schema = SimpleOutput.model_json_schema()
    assert "title" in schema["properties"]
    assert "summary" in schema["properties"]
    assert "items" in schema["properties"]
