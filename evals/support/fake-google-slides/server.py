"""Stdio MCP server replaying the Google Slides and Google Drive connectors from the cassette.

Usage: server.py <Google_Slides|Google_Drive> <state-dir> [<thumbnail-port>]

The cassette (see RECORDING.md) is a synthetic 10-slide deck. setup.sh copies it into
<state-dir>/deck.json and both servers read it from there, so the Slides server's edits show up
in Drive reads. `update_presentation` applies text edits (insertText, deleteText, replaceAllText)
and object creates, duplicates and deletes, then rewrites deck.json and deck.txt; every other
request is validated and logged but changes nothing. Batches are atomic. Each `tools/call`
appends one JSON line, server, tool and arguments, to <state-dir>/calls.log.

Thumbnails: the Slides server serves the recorded PNGs over http on 127.0.0.1:<thumbnail-port>
(default 8765). A slide changed since recording has no render, so its thumbnail is a tool error.
Standard library only: the eval guest has just the distribution's python3.
"""

import copy
import json
import re
import sys
import threading
import uuid
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CASSETTE = Path(__file__).parent
TOOLS = json.loads((CASSETTE / "tools.json").read_text(encoding="utf-8"))
RECORDED = json.loads((CASSETTE / "deck.json").read_text(encoding="utf-8"))["content"]
FILE_ID = "acme-onboarding-fixture"
THUMBNAIL_PATH = re.compile(rf"/docsdf/{FILE_ID}-(p-\d\d)=s800")
SNIPPET_LIMITS = {"BRIEF": 1000, "MEDIUM": 2500, "DETAILED": 5000}
ERROR_PREFIX = (
    "Invalid argument: <eye3 title='/PresentationsService.BatchUpdatePresentation, "
    "INVALID_ARGUMENT'/> APPLICATION_ERROR;slides.v1/BatchUpdatePresentation;"
    "ExternalBadRequestException: "
)
STYLE_ONLY = {
    "updateTextStyle",
    "updateParagraphStyle",
    "updateShapeProperties",
    "updatePageElementTransform",
    "updatePageProperties",
    "updateSlideProperties",
    "updatePageElementAltText",
    "updateLineProperties",
    "updateImageProperties",
    "createParagraphBullets",
    "deleteParagraphBullets",
    "updateSlidesPosition",
    "updatePageElementsZOrder",
    "groupObjects",
    "ungroupObjects",
}


class BadRequest(Exception):
    """One request in a batch is invalid; the whole batch is rejected."""


def dump(value: object) -> str:
    """Compact JSON with sorted keys, the way the live connectors return it."""
    return json.dumps(value, separators=(",", ":"), sort_keys=True, ensure_ascii=False)


def text(result: object, is_error: bool = False) -> dict:
    """A tool result carrying `result` as one text block."""
    body = result if isinstance(result, str) else dump(result)
    return {"content": [{"type": "text", "text": body}], "isError": is_error}


# --- field masks ------------------------------------------------------------------------


def parse_mask(mask: str) -> dict:
    """Parse `a.b(c,d.e),f` into a nested dict; a None leaf selects the whole subtree."""
    tree: dict = {}
    position = 0
    name = re.compile(r"\s*([\w*]+(?:\.[\w*]+)*)\s*")

    def parse_list(into: dict) -> None:
        nonlocal position
        while True:
            match = name.match(mask, position)
            if not match:
                raise BadRequest(f"Invalid field selection {mask}")
            position = match.end()
            *parents, leaf = match.group(1).split(".")
            node: dict | None = into
            for part in parents:
                assert node is not None
                node = node.setdefault(part, {})
                if node is None:
                    break
            child: dict | None = None
            if position < len(mask) and mask[position] == "(":
                position += 1
                child = {}
                parse_list(child)
                if position >= len(mask) or mask[position] != ")":
                    raise BadRequest(f"Invalid field selection {mask}")
                position += 1
            if node is not None:
                merge(node, {leaf: child})
            if position < len(mask) and mask[position] == ",":
                position += 1
                continue
            return

    parse_list(tree)
    if position != len(mask):
        raise BadRequest(f"Invalid field selection {mask}")
    return tree


def apply_mask(value: object, tree: dict | None) -> object:
    """`value` cut down to the fields `tree` selects."""
    if tree is None:
        return value
    if isinstance(value, list):
        return [apply_mask(each, tree) for each in value]
    if not isinstance(value, dict):
        return value
    kept = {}
    for key, sub in tree.items():
        if key == "*":
            kept.update(value)
        elif key in value:
            kept[key] = apply_mask(value[key], sub)
    return kept


def masked(value: dict, fields: list[str] | None) -> object:
    """`value` cut to every mask in `fields`, or whole when there are none."""
    if not fields:
        return value
    tree: dict = {}
    for mask in fields:
        merge(tree, parse_mask(mask))
    return apply_mask(value, tree)


def merge(into: dict, tree: dict) -> None:
    """Union `tree` into `into`, a None leaf winning over any subselection."""
    for key, sub in tree.items():
        if key in into and (into[key] is None or sub is None):
            into[key] = None
        elif isinstance(into.get(key), dict) and isinstance(sub, dict):
            merge(into[key], sub)
        else:
            into[key] = sub


# --- deck model -------------------------------------------------------------------------


def all_pages(deck: dict) -> list[dict]:
    """Every slide and every slide's notes page."""
    pages = []
    for slide in deck["slides"]:
        pages.append(slide)
        notes = slide.get("slideProperties", {}).get("notesPage")
        if notes:
            pages.append(notes)
    return pages


def walk(elements: list[dict]):
    """Yield (element, containing list) for every element, descending into groups."""
    for element in elements:
        yield element, elements
        if "elementGroup" in element:
            yield from walk(element["elementGroup"]["children"])


def find(deck: dict, object_id: str) -> tuple[dict, list[dict] | None]:
    """The slide or element with `object_id` and the list holding it."""
    for slide in deck["slides"]:
        if slide["objectId"] == object_id:
            return slide, deck["slides"]
    for page in all_pages(deck):
        for element, holder in walk(page.get("pageElements", [])):
            if element["objectId"] == object_id:
                return element, holder
    raise BadRequest(f"The object ({object_id}) could not be found.")


def all_ids(deck: dict) -> set[str]:
    """Every object ID in the deck: slides, notes pages and their elements."""
    ids = {deck["presentationId"]}
    for page in all_pages(deck):
        ids.add(page["objectId"])
        ids.update(element["objectId"] for element, _ in walk(page.get("pageElements", [])))
    for page in deck.get("layouts", []) + deck.get("masters", []):
        ids.add(page["objectId"])
    return ids


def new_id(deck: dict, wanted: str | None) -> str:
    """`wanted` checked against the API's ID rules, or a generated ID."""
    if wanted is None:
        return f"g{uuid.uuid4().hex[:12]}"
    if len(wanted) < 5:
        raise BadRequest(f"The object ID ({wanted}) length should not be less than 5.")
    if not re.fullmatch(r"[a-zA-Z0-9_][a-zA-Z0-9_\-:]{4,49}", wanted):
        raise BadRequest(f"The object ID ({wanted}) is not a valid ID.")
    if wanted in all_ids(deck):
        raise BadRequest(
            f"The object ID ({wanted}) should be unique among all pages and page elements."
        )
    return wanted


def plain(shape: dict) -> str:
    """The shape's text as one string."""
    elements = shape.get("text", {}).get("textElements", [])
    return "".join(each["textRun"]["content"] for each in elements if "textRun" in each)


def characters(shape: dict) -> list[tuple[str, str, str]]:
    """Each character with its run style and paragraph marker, both as JSON."""
    out = []
    marker = "{}"
    for element in shape.get("text", {}).get("textElements", []):
        if "paragraphMarker" in element:
            marker = dump(element["paragraphMarker"])
        for kind in ("textRun", "autoText"):
            if kind in element:
                style = dump(element[kind].get("style", {}))
                out.extend((char, style, marker) for char in element[kind]["content"])
    return out


def set_characters(shape: dict, chars: list[tuple[str, str, str]]) -> None:
    """Rebuild the shape's textElements from styled characters; Slides keeps a final newline."""
    if not chars:
        shape.pop("text", None)
        return
    if chars[-1][0] != "\n":
        chars = chars + [("\n", chars[-1][1], chars[-1][2])]
    elements: list[dict] = []
    start = 0
    while start < len(chars):
        end = next(i for i in range(start, len(chars)) if chars[i][0] == "\n") + 1
        marker = json.loads(chars[end - 1][2])
        elements.append(span(start, end, {"paragraphMarker": marker}))
        run_start = start
        for i in range(start + 1, end + 1):
            if i == end or chars[i][1] != chars[run_start][1]:
                content = "".join(char for char, _, _ in chars[run_start:i])
                run = {"content": content, "style": json.loads(chars[run_start][1])}
                elements.append(span(run_start, i, {"textRun": run}))
                run_start = i
        start = end
    shape.setdefault("text", {})["textElements"] = elements


def span(start: int, end: int, body: dict) -> dict:
    """A text element covering [start, end); a zero startIndex is omitted, as the API does."""
    element = {"endIndex": end, **body}
    if start:
        element["startIndex"] = start
    return element


def text_shape(deck: dict, object_id: str) -> dict:
    """The shape with `object_id`, which must be able to hold text."""
    element, _ = find(deck, object_id)
    if "shape" not in element:
        raise BadRequest(f"The object ({object_id}) does not allow text editing.")
    return element["shape"]


def bounds(text_range: dict, length: int) -> tuple[int, int]:
    """The [start, end) a Range selects, never including the final newline."""
    kind = text_range.get("type", "ALL")
    start = text_range.get("startIndex", 0) if kind != "ALL" else 0
    end = text_range.get("endIndex", length) if kind == "FIXED_RANGE" else length
    end = min(end, max(length - 1, 0))
    if not 0 <= start <= end:
        raise BadRequest("The text range is out of bounds.")
    return start, end


def insert_text(deck: dict, request: dict) -> dict:
    """insertText: new characters take the style of the one before them."""
    shape = text_shape(deck, request["objectId"])
    chars = characters(shape)
    index = request.get("insertionIndex", 0)
    if not 0 <= index <= max(len(chars) - 1, 0):
        raise BadRequest(f"The insertion index ({index}) is out of bounds.")
    neighbor = chars[index - 1] if index else (chars[0] if chars else ("", "{}", "{}"))
    added = [(char, neighbor[1], neighbor[2]) for char in request.get("text", "")]
    set_characters(shape, chars[:index] + added + chars[index:])
    return {}


def delete_text(deck: dict, request: dict) -> dict:
    """deleteText over the request's textRange."""
    shape = text_shape(deck, request["objectId"])
    chars = characters(shape)
    start, end = bounds(request.get("textRange", {}), len(chars))
    set_characters(shape, chars[:start] + chars[end:])
    return {}


def replace_all_text(deck: dict, request: dict) -> dict:
    """replaceAllText across the slides' shapes, or only `pageObjectIds`."""
    contains = request.get("containsText", {})
    needle = str(contains.get("text", ""))
    if not needle:
        raise BadRequest("The containsText text must not be empty.")
    flags = 0 if contains.get("matchCase") else re.IGNORECASE
    pattern = re.compile(re.escape(needle), flags)
    pages = request.get("pageObjectIds")
    changed = 0
    for slide in deck["slides"]:
        if pages and slide["objectId"] not in pages:
            continue
        for element, _ in walk(slide.get("pageElements", [])):
            shape = element.get("shape")
            if not shape or "text" not in shape:
                continue
            chars = characters(shape)
            content = "".join(char for char, _, _ in chars)
            hits = list(pattern.finditer(content))
            for hit in reversed(hits):
                first = chars[hit.start()]
                added = [(char, first[1], first[2]) for char in request.get("replaceText", "")]
                chars = chars[: hit.start()] + added + chars[hit.end() :]
            if hits:
                set_characters(shape, chars)
                changed += len(hits)
    reply = {"occurrencesChanged": changed} if changed else {}
    return {"replaceAllText": reply}


def create_shape(deck: dict, request: dict) -> dict:
    """createShape: base size 3000000 EMU, real size carried in the scale, as the API does."""
    properties = request.get("elementProperties", {})
    page, _ = find(deck, properties.get("pageObjectId", ""))
    object_id = new_id(deck, request.get("objectId"))
    size = properties.get("size", {})
    transform = dict(properties.get("transform", {"scaleX": 1, "scaleY": 1, "unit": "EMU"}))
    for axis, scale in (("width", "scaleX"), ("height", "scaleY")):
        magnitude = size.get(axis, {}).get("magnitude", 3000000)
        if size.get(axis, {}).get("unit") == "PT":
            magnitude *= 12700
        transform[scale] = round(transform.get(scale, 1) * magnitude / 3000000, 4)
    base = {"magnitude": 3000000, "unit": "EMU"}
    page.setdefault("pageElements", []).append(
        {
            "objectId": object_id,
            "shape": {"shapeType": request.get("shapeType", "TEXT_BOX"), "shapeProperties": {}},
            "size": {"height": base, "width": base},
            "transform": transform,
        }
    )
    return {"createShape": {"objectId": object_id}}


def create_slide(deck: dict, request: dict) -> dict:
    """createSlide: an empty slide; layout placeholders are not instantiated."""
    object_id = new_id(deck, request.get("objectId"))
    slide = {"objectId": object_id, "pageElements": [], "pageProperties": {}, "slideProperties": {}}
    index = request.get("insertionIndex", len(deck["slides"]))
    deck["slides"].insert(index, slide)
    return {"createSlide": {"objectId": object_id}}


def duplicate_object(deck: dict, request: dict) -> dict:
    """duplicateObject: a copy placed right after the original, IDs remapped."""
    original, holder = find(deck, request["objectId"])
    wanted = request.get("objectIds", {})
    clone = copy.deepcopy(original)
    stack = [clone]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if "objectId" in node:
                node["objectId"] = new_id(deck, wanted.get(node["objectId"]))
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    assert holder is not None
    holder.insert(holder.index(original) + 1, clone)
    return {"duplicateObject": {"objectId": clone["objectId"]}}


def delete_object(deck: dict, request: dict) -> dict:
    """deleteObject: removes a slide or element."""
    element, holder = find(deck, request["objectId"])
    assert holder is not None
    holder.remove(element)
    return {}


def style_only(deck: dict, request: dict) -> dict:
    """Requests the fake accepts and logs without changing the deck."""
    for key in ("objectId", "pageObjectId"):
        if key in request:
            find(deck, request[key])
    for key in ("childrenObjectIds", "pageElementObjectIds", "slideObjectIds"):
        for object_id in request.get(key, []):
            find(deck, object_id)
    return {}


APPLY = {
    "insertText": insert_text,
    "deleteText": delete_text,
    "replaceAllText": replace_all_text,
    "createShape": create_shape,
    "createSlide": create_slide,
    "duplicateObject": duplicate_object,
    "deleteObject": delete_object,
}


def touched_pages(deck: dict, body: dict) -> set[str]:
    """Slide IDs a style-only request names, directly or through one of their elements."""
    ids = {body.get("objectId"), body.get("pageObjectId")}
    for key in ("childrenObjectIds", "pageElementObjectIds", "slideObjectIds"):
        ids.update(body.get(key, []))
    pages = set()
    for slide in deck["slides"]:
        inside = {element["objectId"] for element, _ in walk(slide.get("pageElements", []))}
        if slide["objectId"] in ids or inside & ids:
            pages.add(slide["objectId"])
    return pages


def render_key(slide: dict) -> str:
    """The parts of a slide its thumbnail shows: everything but the speaker notes."""
    properties = {k: v for k, v in slide.get("slideProperties", {}).items() if k != "notesPage"}
    return dump({**slide, "slideProperties": properties})


# --- derived Drive views ----------------------------------------------------------------


def paragraphs(shape: dict) -> list[tuple[str, bool]]:
    """(text, is_bullet) for each paragraph in the shape."""
    out = []
    bullet = False
    current = ""
    for element in shape.get("text", {}).get("textElements", []):
        if "paragraphMarker" in element:
            bullet = "bullet" in element["paragraphMarker"]
        if "textRun" in element:
            current += element["textRun"]["content"]
            if current.endswith("\n"):
                out.append((current[:-1], bullet))
                current = ""
    return out


def file_content(deck: dict) -> str:
    """Drive `read_file_content` text: shapes in order, speaker notes left out."""
    slides = []
    for slide in deck["slides"]:
        body = ""
        for element, _ in walk(slide.get("pageElements", [])):
            if "elementGroup" in element:
                continue
            shape = element.get("shape")
            if shape is None or "text" not in shape:
                body += "  \n"
            elif shape.get("placeholder", {}).get("type") in ("TITLE", "CENTERED_TITLE"):
                body += "# " + plain(shape).strip("\n") + "\n\n  \n"
            else:
                body += plain(shape).replace("\n", "  \n")
        slides.append("-----\n\n" + body + "\n-----")
    return "\n\n".join(slides)


def content_snippet(deck: dict) -> str:
    """Drive metadata `contentSnippet`: every paragraph, then the slide's speaker notes."""
    blocks = []
    count = len(deck["slides"])
    for number, slide in enumerate(deck["slides"], 1):
        shapes = [e["shape"] for e, _ in walk(slide.get("pageElements", [])) if "shape" in e]
        notes = slide.get("slideProperties", {}).get("notesPage")
        if notes:
            speaker = notes["notesProperties"]["speakerNotesObjectId"]
            shapes += [e["shape"] for e in notes["pageElements"] if e["objectId"] == speaker]
        lines = [f"# {number} of {count}"]
        for shape in shapes:
            for words, bullet in paragraphs(shape):
                if words.strip():
                    lines.append(("  - " if bullet else "") + " ".join(words.split()))
        block = lines[0]
        for before, line in zip(lines, lines[1:], strict=False):
            joined = before.startswith("  - ") and line.startswith("  - ")
            block += ("\n" if joined else "\n\n") + line
        blocks.append(block)
    return "\n\n".join(blocks)


# --- server -----------------------------------------------------------------------------


class Fake:
    """Both connectors over one state directory."""

    def __init__(self, server: str, state: Path, port: int):
        self.server = server
        self.state = state
        self.port = port

    def load(self) -> dict:
        deck = json.loads((self.state / "deck.json").read_text(encoding="utf-8"))
        return deck.get("content", deck)

    def save(self, deck: dict) -> None:
        """Write the deck and its read_file_content view atomically, for the other server."""
        for name, body in (("deck.json", dump(deck)), ("deck.txt", file_content(deck))):
            scratch = self.state / f".{name}.{self.server}"
            scratch.write_text(body, encoding="utf-8")
            scratch.replace(self.state / name)

    def stale(self, deck: dict) -> set[str]:
        """Slides whose render would differ from the recorded thumbnail."""
        path = self.state / "styled-pages.json"
        styled = set(json.loads(path.read_text())) if path.exists() else set()
        recorded = {slide["objectId"]: render_key(slide) for slide in RECORDED["slides"]}
        changed = {
            slide["objectId"]
            for slide in deck["slides"]
            if recorded.get(slide["objectId"]) != render_key(slide)
        }
        return styled | changed

    def check_file(self, file_id: object) -> None:
        if file_id != FILE_ID:
            raise LookupError(f"Requested entity was not found: {file_id}")

    def call(self, name: object, arguments: dict) -> dict:
        try:
            if name in ("read_presentation", "read_slide_page", "update_presentation"):
                self.check_file(arguments.get("presentationId"))
            if name in ("read_file_content", "get_file_metadata"):
                self.check_file(arguments.get("fileId"))
            if name == "read_presentation":
                return text({"content": masked(self.load(), arguments.get("fields"))})
            if name == "read_slide_page":
                return text({"content": masked(self.page(arguments), arguments.get("fields"))})
            if name == "read_slide_page_thumbnail":
                return self.thumbnail(arguments)
            if name == "update_presentation":
                return self.update(arguments)
            if name == "read_file_content":
                deck = self.load()
                recorded = json.loads((CASSETTE / "deck.txt").read_text(encoding="utf-8"))
                return text({**recorded, "fileContent": file_content(deck)})
            if name == "get_file_metadata":
                return text(self.metadata(arguments))
        except (LookupError, BadRequest) as error:
            return text(str(error), is_error=True)
        return text(f"unknown tool {name}", is_error=True)

    def page(self, arguments: dict) -> dict:
        deck = self.load()
        for page in all_pages(deck):
            if page["objectId"] == arguments.get("pageId"):
                return {
                    **page,
                    "commentsViewMode": deck.get("commentsViewMode"),
                    "revisionId": deck["revisionId"],
                }
        raise LookupError(f"Requested entity was not found: page {arguments.get('pageId')}")

    def thumbnail(self, arguments: dict) -> dict:
        self.check_file(arguments.get("presentationId"))
        page_id = arguments.get("pageId", "")
        match = re.fullmatch(r"s(\d\d)_slide", page_id)
        if page_id in self.stale(self.load()) or not match:
            raise LookupError(
                f"Thumbnail unavailable for {page_id}: this fake serves only recorded renders, "
                "and the page was created or edited since recording."
            )
        recorded = json.loads((CASSETTE / f"thumbs/p-{match.group(1)}.json").read_text())
        url = recorded["contentUrl"].replace(
            "https://lh7-us.googleusercontent.com", f"http://127.0.0.1:{self.port}"
        )
        return text({**recorded, "contentUrl": url})

    def update(self, arguments: dict) -> dict:
        deck = self.load()
        required = arguments.get("writeControl", {}).get("requiredRevisionId")
        if required and required != deck["revisionId"]:
            raise BadRequest(
                f"{ERROR_PREFIX}The required revision ID ({required}) does not match the "
                f"latest revision ID ({deck['revisionId']}).;"
            )
        draft = copy.deepcopy(deck)
        replies = []
        styled = set()
        for index, request in enumerate(arguments.get("requests", [])):
            if len(request) != 1:
                raise BadRequest(f"{ERROR_PREFIX}Invalid requests[{index}]: one kind each.;")
            kind, body = next(iter(request.items()))
            try:
                if kind in APPLY:
                    replies.append(APPLY[kind](draft, body))
                elif kind in STYLE_ONLY:
                    replies.append(style_only(draft, body))
                    styled |= touched_pages(draft, body)
                else:
                    raise BadRequest(f"Unknown request kind {kind}.")
            except (BadRequest, KeyError) as error:
                detail = str(error) if isinstance(error, BadRequest) else f"missing {error}"
                message = f"{ERROR_PREFIX}Invalid requests[{index}].{kind}: {detail};"
                raise BadRequest(message) from None
        number = int(deck["revisionId"].rsplit("-", 1)[1]) + 1
        draft["revisionId"] = f"fixture-revision-{number:04d}"
        self.save(draft)
        path = self.state / "styled-pages.json"
        styled |= set(json.loads(path.read_text())) if path.exists() else set()
        path.write_text(json.dumps(sorted(styled)))
        (self.state / "modified").write_text(datetime.now(UTC).isoformat())
        return text({"replies": replies})

    def metadata(self, arguments: dict) -> dict:
        meta = json.loads((CASSETTE / "meta.json").read_text(encoding="utf-8"))
        overlay = self.state / "meta-overlay.json"
        if overlay.exists():
            meta.update(json.loads(overlay.read_text(encoding="utf-8")))
        modified = self.state / "modified"
        if modified.exists():
            stamp = datetime.fromisoformat(modified.read_text())
            meta["modifiedTime"] = stamp.strftime("%Y-%m-%dT%H:%M:%S.") + "000Z"
        if arguments.get("excludeContentSnippets"):
            meta.pop("contentSnippet", None)
        else:
            snippet = content_snippet(self.load())
            limit = SNIPPET_LIMITS.get(arguments.get("snippetVerbosity", "DETAILED"))
            meta["contentSnippet"] = snippet[:limit] if limit else snippet
        return meta

    def answer(self, message: dict) -> dict | None:
        """The JSON-RPC response to one message, or None for a notification."""
        if "id" not in message:
            return None
        method = message.get("method")
        params = message.get("params") or {}
        if method == "initialize":
            result: dict = {
                "protocolVersion": params.get("protocolVersion", "2025-06-18"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": self.server, "version": "0.0.0"},
            }
        elif method == "tools/list":
            tools = [
                {key: value for key, value in tool.items() if key != "server"}
                for tool in TOOLS
                if tool["server"] == self.server
            ]
            result = {"tools": tools}
        elif method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments") or {}
            line = {"server": self.server, "tool": name, "arguments": arguments}
            with (self.state / "calls.log").open("a", encoding="utf-8") as log:
                log.write(json.dumps(line, ensure_ascii=False) + "\n")
            result = self.call(name, arguments)
        elif method == "ping":
            result = {}
        else:
            error = {"code": -32601, "message": f"unsupported method {method}"}
            return {"jsonrpc": "2.0", "id": message["id"], "error": error}
        return {"jsonrpc": "2.0", "id": message["id"], "result": result}


class Thumbnails(BaseHTTPRequestHandler):
    """Serves thumbs/p-NN.png at the recorded contentUrl path."""

    def do_GET(self) -> None:  # noqa: N802 - http.server's naming
        match = THUMBNAIL_PATH.fullmatch(self.path)
        png = CASSETTE / f"thumbs/{match.group(1)}.png" if match else None
        if png is None or not png.exists():
            self.send_error(404)
            return
        body = png.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return


def serve_thumbnails(port: int) -> None:
    """Start the PNG server unless another fake process already holds the port."""
    try:
        httpd = ThreadingHTTPServer(("127.0.0.1", port), Thumbnails)
    except OSError:
        return
    threading.Thread(target=httpd.serve_forever, daemon=True).start()


def main() -> int:
    """Serve newline-delimited JSON-RPC on stdin and stdout until stdin closes."""
    if len(sys.argv) not in (3, 4) or sys.argv[1] not in ("Google_Slides", "Google_Drive"):
        print("usage: server.py <Google_Slides|Google_Drive> <state-dir> [<port>]", file=sys.stderr)
        return 2
    port = int(sys.argv[3]) if len(sys.argv) == 4 else 8765
    fake = Fake(sys.argv[1], Path(sys.argv[2]), port)
    if fake.server == "Google_Slides":
        serve_thumbnails(port)
    for line in sys.stdin:
        if not line.strip():
            continue
        response = fake.answer(json.loads(line))
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
