"""fake-google-slides replays its cassette, applies text edits, and logs every call."""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

FAKE = Path(__file__).parents[4] / "evals" / "support" / "fake-google-slides"
DECK = "acme-onboarding-fixture"


class Server:
    """One fake connector process speaking JSON-RPC over stdio."""

    def __init__(self, name: str, state: Path, port: int):
        self.process = subprocess.Popen(
            [sys.executable, FAKE / "server.py", name, state, str(port)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        self.next_id = 0

    def request(self, method: str, params: dict | None = None) -> dict:
        assert self.process.stdin and self.process.stdout
        self.next_id += 1
        message = {"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params or {}}
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()
        return json.loads(self.process.stdout.readline())["result"]

    def call(self, tool: str, **arguments: object) -> tuple[str, bool]:
        """The tool's text block and whether it is an error."""
        result = self.request("tools/call", {"name": tool, "arguments": arguments})
        return result["content"][0]["text"], result["isError"]

    def close(self) -> None:
        assert self.process.stdin
        self.process.stdin.close()
        self.process.wait(timeout=5)


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture
def state(tmp_path: Path) -> Path:
    shutil.copy(FAKE / "deck.json", tmp_path / "deck.json")
    return tmp_path


@pytest.fixture
def port() -> int:
    return free_port()


@pytest.fixture
def slides(state: Path, port: int):
    server = Server("Google_Slides", state, port)
    yield server
    server.close()


@pytest.fixture
def drive(state: Path, port: int):
    server = Server("Google_Drive", state, port)
    yield server
    server.close()


def cassette(name: str) -> str:
    """A recorded response compacted the way the live connector returns it."""
    value = json.loads((FAKE / name).read_text(encoding="utf-8"))
    return json.dumps(value, separators=(",", ":"), sort_keys=True, ensure_ascii=False)


def test_each_server_lists_its_recorded_tools(slides: Server, drive: Server):
    recorded = json.loads((FAKE / "tools.json").read_text(encoding="utf-8"))
    for server, name in ((slides, "Google_Slides"), (drive, "Google_Drive")):
        tools = server.request("tools/list")["tools"]
        expected = [
            {k: v for k, v in tool.items() if k != "server"}
            for tool in recorded
            if tool["server"] == name
        ]
        assert tools == expected


def test_unedited_reads_replay_the_cassette(slides: Server, drive: Server):
    assert slides.call("read_presentation", presentationId=DECK) == (cassette("deck.json"), False)
    for number in range(1, 11):
        page = f"s{number:02d}_slide"
        replay = slides.call("read_slide_page", presentationId=DECK, pageId=page)
        assert replay == (cassette(f"pages/p-{number:02d}.json"), False)
    assert drive.call("read_file_content", fileId=DECK) == (cassette("deck.txt"), False)
    assert drive.call("get_file_metadata", fileId=DECK) == (cassette("meta.json"), False)


def test_field_masks_select_nested_fields(slides: Server):
    body, _ = slides.call(
        "read_presentation",
        presentationId=DECK,
        fields=["revisionId", "slides(objectId,pageElements(objectId,shape.shapeType))"],
    )
    deck = json.loads(body)["content"]
    assert set(deck) == {"revisionId", "slides"}
    assert deck["slides"][0] == {
        "objectId": "s01_slide",
        "pageElements": [
            {"objectId": "s01_title", "shape": {"shapeType": "TEXT_BOX"}},
            {"objectId": "s01_subtitle", "shape": {"shapeType": "TEXT_BOX"}},
            {"objectId": "s01_accent_bar", "shape": {"shapeType": "RECTANGLE"}},
        ],
    }


def test_text_edits_show_in_later_reads_on_both_servers(slides: Server, drive: Server):
    requests = [
        {
            "replaceAllText": {
                "containsText": {"text": "4 Review", "matchCase": True},
                "replaceText": "4 Approve",
            }
        },
        {"deleteText": {"objectId": "s07_stat_value", "textRange": {"type": "ALL"}}},
        {"insertText": {"objectId": "s07_stat_value", "text": "4 min"}},
    ]
    body, error = slides.call(
        "update_presentation",
        presentationId=DECK,
        requests=requests,
        writeControl={"requiredRevisionId": "fixture-revision-0001"},
    )

    assert not error
    assert json.loads(body) == {"replies": [{"replaceAllText": {"occurrencesChanged": 5}}, {}, {}]}
    content, _ = drive.call("read_file_content", fileId=DECK)
    text = json.loads(content)["fileContent"]
    assert text.count("4 Approve") == 5 and "4 Review" not in text
    assert "4 min  \naverage review" in text
    page, _ = slides.call("read_slide_page", presentationId=DECK, pageId="s07_slide")
    value = json.loads(page)["content"]["pageElements"][9]["shape"]["text"]["textElements"]
    assert value[1]["textRun"]["content"] == "4 min\n"
    recorded = json.loads((FAKE / "pages" / "p-07.json").read_text())["content"]["pageElements"]
    assert (
        value[1]["textRun"]["style"]
        == recorded[9]["shape"]["text"]["textElements"][1]["textRun"]["style"]
    )
    meta, _ = drive.call("get_file_metadata", fileId=DECK)
    assert "about 10 minutes" in json.loads(meta)["contentSnippet"]


def test_a_bad_request_rejects_the_whole_batch(slides: Server, drive: Server):
    requests = [
        {"insertText": {"objectId": "s09_title", "text": "Five "}},
        {"createSlide": {"objectId": "s01"}},
    ]
    body, error = slides.call("update_presentation", presentationId=DECK, requests=requests)

    assert error
    assert body.startswith("Invalid argument: <eye3 title=")
    assert "Invalid requests[1].createSlide: The object ID (s01) length" in body
    assert drive.call("read_file_content", fileId=DECK) == (cassette("deck.txt"), False)


def test_a_stale_revision_is_refused(slides: Server):
    edit = [{"insertText": {"objectId": "s09_title", "text": "Five "}}]
    guard = {"requiredRevisionId": "fixture-revision-0001"}
    assert not slides.call("update_presentation", presentationId=DECK, requests=edit)[1]

    body, error = slides.call(
        "update_presentation", presentationId=DECK, requests=edit, writeControl=guard
    )

    assert error and "does not match" in body


def test_creates_keep_the_recorded_size_quirk(slides: Server):
    shape = {
        "objectId": "s09_card_1",
        "shapeType": "RECTANGLE",
        "elementProperties": {
            "pageObjectId": "s09_slide",
            "size": {
                "width": {"magnitude": 2000000, "unit": "EMU"},
                "height": {"magnitude": 1000000, "unit": "EMU"},
            },
            "transform": {"scaleX": 1, "scaleY": 1, "translateX": 0, "translateY": 0},
        },
    }
    body, _ = slides.call(
        "update_presentation",
        presentationId=DECK,
        requests=[
            {"createShape": shape},
            {"insertText": {"objectId": "s09_card_1", "text": "Pilot first"}},
        ],
    )

    assert json.loads(body)["replies"][0] == {"createShape": {"objectId": "s09_card_1"}}
    page, _ = slides.call("read_slide_page", presentationId=DECK, pageId="s09_slide")
    card = json.loads(page)["content"]["pageElements"][-1]
    assert card["size"]["width"]["magnitude"] == 3000000
    assert card["transform"]["scaleX"] == 0.6667


def test_thumbnails_serve_the_recorded_png_until_the_slide_changes(slides: Server, port: int):
    body, error = slides.call("read_slide_page_thumbnail", presentationId=DECK, pageId="s09_slide")
    url = json.loads(body)["contentUrl"]

    assert not error and url.startswith(f"http://127.0.0.1:{port}/")
    with urllib.request.urlopen(url) as response:
        assert response.read() == (FAKE / "thumbs" / "p-09.png").read_bytes()

    edit = [{"insertText": {"objectId": "s09_title", "text": "Five "}}]
    slides.call("update_presentation", presentationId=DECK, requests=edit)
    assert slides.call("read_slide_page_thumbnail", presentationId=DECK, pageId="s09_slide")[1]
    assert not slides.call("read_slide_page_thumbnail", presentationId=DECK, pageId="s08_slide")[1]


def test_every_call_is_logged(slides: Server, drive: Server, state: Path):
    slides.call("read_slide_page", presentationId=DECK, pageId="s07_slide")
    drive.call("read_file_content", fileId=DECK)

    lines = [json.loads(line) for line in (state / "calls.log").read_text().splitlines()]
    assert [(line["server"], line["tool"]) for line in lines] == [
        ("Google_Slides", "read_slide_page"),
        ("Google_Drive", "read_file_content"),
    ]


def test_metadata_overlay_replaces_recorded_fields(drive: Server, state: Path):
    (state / "meta-overlay.json").write_text(json.dumps({"owner": "priya@example.com"}))

    meta = json.loads(drive.call("get_file_metadata", fileId=DECK)[0])

    assert meta["owner"] == "priya@example.com"
