import re

from fastapi import HTTPException, Request
from starlette.requests import ClientDisconnect

MAX_FILE_BYTES = 1024 * 1024
INLINE = re.compile(r"(?P<delimiter>\*\*|__|\*|_)(?P<text>[^*_]+)(?P=delimiter)")
HEADING = re.compile(r"^(#{1,2})[ \t]+(.+)$")
LIST_ITEM = re.compile(r"^([-+*]|[0-9]{1,9}\.)[ \t]+(.*)$")


async def read_import(request: Request, filename: str) -> tuple[str, dict]:
    if request.headers.get("content-type") != "application/octet-stream":
        raise HTTPException(415, "Send the file bytes as application/octet-stream.")
    if any(character in filename for character in ("/", "\\", "\x00", "\r", "\n")):
        raise HTTPException(400, "Provide the original filename without a directory.")
    title, _, extension = filename.rpartition(".")
    extension = extension.lower()
    if extension not in {"txt", "md"}:
        raise HTTPException(415, "Choose a .txt or .md file.")
    title = title.strip()
    if not title or len(title) > 200:
        raise HTTPException(400, "The filename without its extension must contain 1 to 200 characters.")

    data = bytearray()
    try:
        async for chunk in request.stream():
            if len(data) + len(chunk) > MAX_FILE_BYTES:
                raise HTTPException(413, "The file exceeds the 1 MB limit.")
            data.extend(chunk)
    except ClientDisconnect:
        raise HTTPException(400, "The upload was interrupted.") from None
    try:
        source = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(400, "Save the file as UTF-8 and try again.") from None

    return title, parse_document(source, markdown=extension == "md")


def text_node(text: str) -> dict:
    return {"type": "text", "text": text}


def inline_nodes(line: str, markdown: bool) -> list[dict]:
    if not markdown:
        return [text_node(line)] if line else []
    nodes = []
    offset = 0
    for match in INLINE.finditer(line):
        if match.start() > offset:
            nodes.append(text_node(line[offset:match.start()]))
        mark = "bold" if len(match["delimiter"]) == 2 else "italic"
        nodes.append({**text_node(match["text"]), "marks": [{"type": mark}]})
        offset = match.end()
    if offset < len(line):
        nodes.append(text_node(line[offset:]))
    return nodes


def parse_document(source: str, *, markdown: bool) -> dict:
    blocks = []
    current_list = None
    # Emit text nodes directly, including HTML. No HTML parser or renderer is involved.
    for line in source.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        item = LIST_ITEM.match(line) if markdown else None
        if item:
            marker, body = item.groups()
            kind = "orderedList" if marker.endswith(".") else "bulletList"
            if current_list is None or current_list["type"] != kind:
                current_list = {"type": kind, "content": []}
                if kind == "orderedList":
                    current_list["attrs"] = {"start": int(marker[:-1])}
                blocks.append(current_list)
            paragraph = {"type": "paragraph", "content": inline_nodes(body, markdown)}
            current_list["content"].append({"type": "listItem", "content": [paragraph]})
            continue

        current_list = None
        heading = HEADING.match(line) if markdown else None
        if heading:
            blocks.append({
                "type": "heading", "attrs": {"level": len(heading[1])},
                "content": inline_nodes(heading[2], markdown),
            })
        else:
            blocks.append({"type": "paragraph", "content": inline_nodes(line, markdown)})
    return {"type": "doc", "content": blocks}
