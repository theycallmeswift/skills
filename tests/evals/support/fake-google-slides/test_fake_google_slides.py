"""fake-google-slides replays its cassette, copies and creates decks, applies text edits, and logs
every call."""

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
TEMPLATE = "acme-template-fixture"
COPY = "acme-template-copy-fixture"
PRESENTATION = "application/vnd.google-apps.presentation"


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


def test_template_reads_replay_its_cassette(slides: Server, drive: Server):
    replay = slides.call("read_presentation", presentationId=TEMPLATE)
    assert replay == (cassette("template/deck.json"), False)
    for number in range(1, 4):
        page = f"t{number:02d}_slide"
        replay = slides.call("read_slide_page", presentationId=TEMPLATE, pageId=page)
        assert replay == (cassette(f"template/pages/p-{number:02d}.json"), False)
    assert drive.call("read_file_content", fileId=TEMPLATE) == (
        cassette("template/deck.txt"),
        False,
    )
    assert drive.call("get_file_metadata", fileId=TEMPLATE) == (
        cassette("template/meta.json"),
        False,
    )


def test_copy_file_serves_the_template_under_the_copy_id(slides: Server, drive: Server, port: int):
    title = "Acme brand template (eval fixture) copy"

    reply = drive.call("copy_file", fileId=TEMPLATE, title=title)

    assert reply == (cassette("template/copy_file.json"), False)
    deck = json.loads(slides.call("read_presentation", presentationId=COPY)[0])["content"]
    template = json.loads((FAKE / "template" / "deck.json").read_text())["content"]
    assert (deck["presentationId"], deck["title"]) == (COPY, title)
    assert deck["slides"] == template["slides"] and deck["layouts"] == template["layouts"]
    page, error = slides.call("read_slide_page", presentationId=COPY, pageId="t02_slide")
    assert not error and json.loads(page)["content"]["objectId"] == "t02_slide"
    body, error = slides.call("read_slide_page_thumbnail", presentationId=COPY, pageId="t03_slide")
    with urllib.request.urlopen(json.loads(body)["contentUrl"]) as response:
        assert response.read() == (FAKE / "template" / "thumbs" / "p-03.png").read_bytes()
    assert not error and f"127.0.0.1:{port}" in body


def test_editing_a_copy_leaves_the_template_alone(slides: Server, drive: Server, state: Path):
    drive.call("copy_file", fileId=TEMPLATE)
    edit = [{"insertText": {"objectId": "t02_title", "text": "New "}}]

    assert not slides.call("update_presentation", presentationId=COPY, requests=edit)[1]

    assert "# New State the takeaway" in (state / "files" / COPY / "deck.txt").read_text()
    assert drive.call("read_file_content", fileId=TEMPLATE) == (
        cassette("template/deck.txt"),
        False,
    )
    second = json.loads(drive.call("copy_file", fileId=TEMPLATE)[0])
    assert second["id"] == f"{COPY}-2"
    assert second["title"] == "Copy of Acme brand template (eval fixture)"


def test_create_file_makes_the_recorded_blank_deck(slides: Server, drive: Server):
    reply = drive.call(
        "create_file", title="Blank deck (eval fixture)", contentMimeType=PRESENTATION
    )

    assert reply == (cassette("template/create_file.json"), False)
    deck = slides.call("read_presentation", presentationId="blank-deck-fixture")
    assert deck == (cassette("template/blank.json"), False)
    refused = drive.call("create_file", title="Notes", contentMimeType="text/plain")
    assert refused[1] and "only blank presentations" in refused[0]


def test_created_slides_get_their_layouts_text_placeholders(slides: Server, drive: Server):
    drive.call("copy_file", fileId=TEMPLATE)
    create = {
        "objectId": "t04_slide",
        "slideLayoutReference": {"layoutId": "p5"},
        "placeholderIdMappings": [
            {"layoutPlaceholder": {"type": "TITLE"}, "objectId": "t04_title"},
            {"layoutPlaceholder": {"type": "BODY", "index": 1}, "objectId": "t04_right"},
        ],
    }
    requests = [
        {"createSlide": create},
        {"insertText": {"objectId": "t04_title", "text": "Two options"}},
        {"insertText": {"objectId": "t04_right", "text": "Option B"}},
    ]

    body, error = slides.call("update_presentation", presentationId=COPY, requests=requests)

    assert not error, body
    page = json.loads(slides.call("read_slide_page", presentationId=COPY, pageId="t04_slide")[0])
    elements = page["content"]["pageElements"]
    assert [e["shape"]["placeholder"]["type"] for e in elements] == ["TITLE", "BODY", "BODY"]
    assert elements[0]["objectId"] == "t04_title" and elements[2]["objectId"] == "t04_right"
    assert page["content"]["slideProperties"]["layoutObjectId"] == "p5"
    content = json.loads(drive.call("read_file_content", fileId=COPY)[0])["fileContent"]
    assert "# Two options" in content and "Option B" in content
    assert slides.call("read_slide_page_thumbnail", presentationId=COPY, pageId="t04_slide")[1]


def test_transform_shape_and_position_updates_apply(slides: Server, drive: Server):
    requests = [
        {
            "updatePageElementTransform": {
                "objectId": "s09_title",
                "applyMode": "ABSOLUTE",
                "transform": {"scaleX": 2, "scaleY": 0.5, "translateX": 100, "unit": "EMU"},
            }
        },
        {
            "updatePageElementTransform": {
                "objectId": "s09_title",
                "applyMode": "RELATIVE",
                "transform": {"scaleX": 1, "scaleY": 1, "translateX": 50, "translateY": 20},
            }
        },
        {
            "updateShapeProperties": {
                "objectId": "s09_title",
                "shapeProperties": {
                    "shapeBackgroundFill": {"solidFill": {"color": {"themeColor": "ACCENT1"}}}
                },
                "fields": "shapeBackgroundFill.solidFill.color",
            }
        },
        {"updateSlidesPosition": {"slideObjectIds": ["s10_slide"], "insertionIndex": 8}},
    ]

    body, error = slides.call("update_presentation", presentationId=DECK, requests=requests)

    assert not error, body
    page = json.loads(slides.call("read_slide_page", presentationId=DECK, pageId="s09_slide")[0])
    title = next(e for e in page["content"]["pageElements"] if e["objectId"] == "s09_title")
    assert title["transform"] == {
        "scaleX": 2,
        "scaleY": 0.5,
        "translateX": 150,
        "translateY": 20,
        "unit": "EMU",
    }
    fill = title["shape"]["shapeProperties"]["shapeBackgroundFill"]["solidFill"]
    assert fill["color"] == {"themeColor": "ACCENT1"}
    content = json.loads(drive.call("read_file_content", fileId=DECK)[0])["fileContent"]
    assert content.index("Next steps for this week") < content.index("# Tips")


def test_relative_transforms_compose_as_matrices(slides: Server):
    absolute = {"scaleX": 2, "scaleY": 3, "translateX": 10, "translateY": 20, "unit": "EMU"}
    relative = {"scaleX": 0.5, "scaleY": 2, "shearX": 1, "translateX": 5, "translateY": 7}
    requests = [
        {
            "updatePageElementTransform": {
                "objectId": "s09_title",
                "applyMode": mode,
                "transform": transform,
            }
        }
        for mode, transform in (("ABSOLUTE", absolute), ("RELATIVE", relative))
    ]

    body, error = slides.call("update_presentation", presentationId=DECK, requests=requests)

    assert not error, body
    page = json.loads(slides.call("read_slide_page", presentationId=DECK, pageId="s09_slide")[0])
    title = next(e for e in page["content"]["pageElements"] if e["objectId"] == "s09_title")
    # [[0.5, 1, 5], [0, 2, 7]] x [[2, 0, 10], [0, 3, 20]] = [[1, 3, 30], [0, 6, 47]]
    assert title["transform"] == {
        "scaleX": 1,
        "shearX": 3,
        "translateX": 30,
        "scaleY": 6,
        "translateY": 47,
        "unit": "EMU",
    }


@pytest.mark.parametrize(
    "request_body",
    [
        {"updateSlidesPosition": {"slideObjectIds": ["s09_title"], "insertionIndex": 0}},
        {
            "updateSlidesPosition": {
                "slideObjectIds": ["s10_slide", "s10_slide"],
                "insertionIndex": 0,
            }
        },
        {
            "updatePageElementTransform": {
                "objectId": "s09_slide",
                "applyMode": "ABSOLUTE",
                "transform": {"scaleX": 1, "scaleY": 1},
            }
        },
    ],
)
def test_moves_and_transforms_reject_the_wrong_kind_of_object(
    slides: Server, drive: Server, request_body: dict
):
    body, error = slides.call("update_presentation", presentationId=DECK, requests=[request_body])

    assert error, body
    assert drive.call("read_file_content", fileId=DECK) == (cassette("deck.txt"), False)
