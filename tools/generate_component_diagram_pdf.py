#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from textwrap import wrap


PAGE_W = 792
PAGE_H = 612
MARGIN = 32


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def fmt(num: float) -> str:
    if abs(num - round(num)) < 1e-6:
        return str(int(round(num)))
    return f"{num:.2f}".rstrip("0").rstrip(".")


class PDFBuilder:
    def __init__(self) -> None:
        self.objects: list[bytes | None] = []

    def reserve(self) -> int:
        self.objects.append(None)
        return len(self.objects)

    def set_object(self, obj_id: int, data: bytes) -> None:
        self.objects[obj_id - 1] = data

    def build(self, path: Path) -> None:
        offsets: list[int] = []
        out = bytearray()
        out.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        for i, obj in enumerate(self.objects, start=1):
            offsets.append(len(out))
            out.extend(f"{i} 0 obj\n".encode("ascii"))
            out.extend(obj or b"<<>>")
            out.extend(b"\nendobj\n")
        xref_pos = len(out)
        out.extend(f"xref\n0 {len(self.objects) + 1}\n".encode("ascii"))
        out.extend(b"0000000000 65535 f \n")
        for off in offsets:
            out.extend(f"{off:010d} 00000 n \n".encode("ascii"))
        out.extend(
            (
                "trailer\n"
                f"<< /Size {len(self.objects) + 1} /Root {len(self.objects)} 0 R >>\n"
                "startxref\n"
                f"{xref_pos}\n"
                "%%EOF\n"
            ).encode("ascii")
        )
        path.write_bytes(out)


class Page:
    def __init__(self) -> None:
        self.parts: list[str] = []

    def text(self, x: float, y: float, text: str, size: int = 11, font: str = "F1") -> None:
        self.parts.append(f"BT /{font} {size} Tf {fmt(x)} {fmt(y)} Td ({esc(text)}) Tj ET")

    def wrap_text(self, x: float, y: float, text: str, size: int = 11, width: int = 92, leading: int | None = None, font: str = "F1") -> float:
        leading = leading or int(size * 1.35)
        cur_y = y
        for line in wrap(text, width=width):
            self.text(x, cur_y, line, size=size, font=font)
            cur_y -= leading
        return cur_y

    def bullets(self, x: float, y: float, items: list[str], size: int = 11, width: int = 84, leading: int | None = None) -> float:
        leading = leading or int(size * 1.35)
        cur_y = y
        for item in items:
            lines = wrap(item, width=width)
            self.text(x, cur_y, f"- {lines[0]}", size=size)
            cur_y -= leading
            for line in lines[1:]:
                self.text(x + 12, cur_y, line, size=size)
                cur_y -= leading
            cur_y -= 2
        return cur_y

    def box(self, x: float, y: float, w: float, h: float, title: str, body: list[str], fill=(0.96, 0.97, 0.99), stroke=(0.27, 0.34, 0.42)) -> None:
        self.parts.append(
            f"q {fmt(fill[0])} {fmt(fill[1])} {fmt(fill[2])} rg {fmt(stroke[0])} {fmt(stroke[1])} {fmt(stroke[2])} RG "
            f"{fmt(x)} {fmt(y)} {fmt(w)} {fmt(h)} re B Q"
        )
        self.text(x + 8, y + h - 16, title, size=10, font="F2")
        cy = y + h - 30
        for line in body:
            for seg in wrap(line, width=max(18, int(w / 4.8))):
                if cy < y + 10:
                    break
                self.text(x + 8, cy, seg, size=8)
                cy -= 10

    def arrow(self, x1: float, y1: float, x2: float, y2: float) -> None:
        self.parts.append(f"q 0.3 w {fmt(x1)} {fmt(y1)} m {fmt(x2)} {fmt(y2)} l S Q")
        dx = x2 - x1
        dy = y2 - y1
        length = (dx * dx + dy * dy) ** 0.5 or 1.0
        ux = dx / length
        uy = dy / length
        left_x = x2 - 8 * ux + 4 * uy
        left_y = y2 - 8 * uy - 4 * ux
        right_x = x2 - 8 * ux - 4 * uy
        right_y = y2 - 8 * uy + 4 * ux
        self.parts.append(
            f"q 0.3 w {fmt(x2)} {fmt(y2)} m {fmt(left_x)} {fmt(left_y)} l S "
            f"{fmt(x2)} {fmt(y2)} m {fmt(right_x)} {fmt(right_y)} l S Q"
        )

    def header(self, title: str, subtitle: str = "") -> None:
        self.text(MARGIN, PAGE_H - 42, title, size=20, font="F2")
        if subtitle:
            self.text(MARGIN, PAGE_H - 62, subtitle, size=10)
        self.parts.append(f"q 0.70 0.74 0.80 rg {MARGIN} {PAGE_H - 72} {PAGE_W - 2 * MARGIN} 1.2 re f Q")

    def footer(self, page_no: int) -> None:
        self.parts.append(f"q 0.82 0.82 0.82 rg {MARGIN} 20 {PAGE_W - 2 * MARGIN} 0.8 re f Q")
        self.text(MARGIN, 8, "CloudLearn UML Component Diagram", size=9)
        self.text(PAGE_W - MARGIN - 46, 8, f"Page {page_no}", size=9)

    def content(self) -> bytes:
        return ("\n".join(self.parts) + "\n").encode("ascii")


def render(path: Path) -> None:
    pages: list[Page] = []

    p = Page()
    p.header("CloudLearn UML Component Diagram", "How the simulator, CloudSim, provider services, and host runtime bridge fit together")
    p.box(28, 418, 128, 82, "<<component>> Browser", ["UI entrypoint", "Shows AWS/GCP consoles", "Opens WebSockets"], fill=(0.96, 0.96, 0.92))
    p.box(176, 418, 132, 82, "<<component>> simulator", ["FastAPI app", "static/index.html", "server.py"], fill=(0.95, 0.97, 0.99))
    p.box(328, 418, 132, 82, "<<component>> provider services", ["providers/aws_*", "providers/gcp_*", "Route modules"], fill=(0.95, 0.98, 0.95))
    p.box(480, 418, 132, 82, "<<component>> CloudSim", ["Spaces", "Resource graph", "Events and summaries"], fill=(0.98, 0.95, 0.95))
    p.box(632, 418, 132, 82, "<<component>> host bridge", ["core/runtime_bridge.py", "Host API", "Multipass / LXD"], fill=(0.95, 0.95, 0.99))
    p.box(328, 252, 132, 82, "<<component>> host config", [".cloudlearn-host.json", "Host OS + bridge URL", "Browser fallback"], fill=(0.99, 0.97, 0.93))
    p.box(176, 252, 132, 82, "<<component>> EC2 runtime", ["Launch / stop / reboot", "Console sessions", "Sandbox state"], fill=(0.94, 0.98, 0.97))
    p.box(480, 252, 132, 82, "<<component>> GCP services", ["Compute, Storage", "SQL, Pub/Sub", "Firestore, IAM"], fill=(0.96, 0.95, 0.99))
    p.box(632, 252, 132, 82, "<<component>> AWS services", ["S3, IAM, VPC", "RDS, Lambda", "SQS, DynamoDB, API GW"], fill=(0.99, 0.96, 0.94))
    p.arrow(156, 459, 176, 459)
    p.arrow(308, 459, 328, 459)
    p.arrow(460, 459, 480, 459)
    p.arrow(612, 459, 632, 459)
    p.arrow(328, 418, 328, 334)
    p.arrow(176, 418, 176, 334)
    p.arrow(480, 418, 480, 334)
    p.arrow(632, 418, 632, 334)
    p.wrap_text(28, 190, "The browser only talks to the simulator container. The simulator container talks to CloudSim for simulation state and to the host bridge for real host-side runtime control.", size=11, width=120)
    p.footer(1)
    pages.append(p)

    p = Page()
    p.header("How Requests Move", "The provider routes are thin; the shared backend does the heavy lifting and mirrors resource changes into CloudSim")
    p.box(28, 420, 126, 70, "<<component>> AWS/GCP request", ["API, query, CLI, SDK"], fill=(0.96, 0.96, 0.92))
    p.box(170, 420, 126, 70, "<<component>> API router", ["server.py", "FastAPI routes"], fill=(0.95, 0.97, 0.99))
    p.box(312, 420, 126, 70, "<<component>> provider module", ["Provider-specific handlers", "Shared state adapters"], fill=(0.95, 0.98, 0.95))
    p.box(454, 420, 126, 70, "<<component>> CloudSim sync", ["Upsert resource", "Emit event", "Update summary"], fill=(0.98, 0.95, 0.95))
    p.box(596, 420, 168, 70, "<<component>> runtime decision", ["Host OS selection", "Sandbox backend", "Host bridge call"], fill=(0.95, 0.95, 0.99))
    p.box(312, 230, 126, 78, "<<component>> instance state", ["pending", "running", "stopped", "terminated"], fill=(0.95, 0.98, 0.97))
    p.box(454, 230, 126, 78, "<<component>> console session", ["SSH / shell stream", "WebSocket terminal"], fill=(0.97, 0.96, 0.99))
    p.box(596, 230, 168, 78, "<<component>> resource graph", ["Per-space nodes", "Provider separation", "Topology view"], fill=(0.99, 0.97, 0.94))
    p.arrow(154, 455, 170, 455)
    p.arrow(296, 455, 312, 455)
    p.arrow(438, 455, 454, 455)
    p.arrow(580, 455, 596, 455)
    p.arrow(354, 420, 354, 308)
    p.arrow(497, 420, 497, 308)
    p.arrow(680, 420, 680, 308)
    p.wrap_text(28, 186, "CloudSim never launches sandboxes itself. It records and reflects the resource lifecycle, while the host bridge owns the actual runtime execution.", size=11, width=120)
    p.footer(2)
    pages.append(p)

    p = Page()
    p.header("Integration Responsibilities", "This keeps each component focused and makes the system easier to reason about")
    p.text(28, 484, "<<component>> simulator container", size=14, font="F2")
    p.bullets(28, 464, [
        "Serve the browser UI and provider consoles.",
        "Expose AWS/GCP REST, query, and action routes.",
        "Maintain shared simulator state and per-space data.",
        "Forward resource updates into CloudSim.",
        "Open terminal sessions for running EC2 instances.",
    ], size=11, width=88)
    p.text(280, 484, "<<component>> CloudSim container", size=14, font="F2")
    p.bullets(280, 464, [
        "Store active-space state and resource graph summaries.",
        "Track events, counts, and runtime bundle usage.",
        "Surface the local cloud backbone for the UI.",
        "Remain provider-neutral while reflecting provider resources.",
    ], size=11, width=88)
    p.text(522, 484, "<<component>> Host OS bridge", size=14, font="F2")
    p.bullets(522, 464, [
        "Execute Multipass on macOS and Windows.",
        "Execute LXD on Linux.",
        "Provide bridge health and host status endpoints.",
        "Keep sandbox launch outside the container boundary.",
    ], size=11, width=86)
    p.text(28, 184, "Important contract", size=14, font="F2")
    p.wrap_text(
        28,
        164,
        "The user-facing browser only talks to the simulator container. The simulator container consumes host OS hints from the launcher config file and uses the host runtime bridge to start the sandbox on the host machine. CloudSim is the simulation backbone that receives resource updates and exposes the active-space graph back to the UI.",
        size=11,
        width=112,
    )
    p.footer(3)
    pages.append(p)

    builder = PDFBuilder()
    font_regular = builder.reserve()
    font_bold = builder.reserve()
    content_ids: list[int] = []
    page_ids: list[int] = []
    for _ in pages:
        content_ids.append(builder.reserve())
        page_ids.append(builder.reserve())
    pages_id = builder.reserve()
    catalog_id = builder.reserve()
    builder.set_object(font_regular, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    builder.set_object(font_bold, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    for page, content_id, page_id in zip(pages, content_ids, page_ids):
        content = page.content()
        builder.set_object(
            content_id,
            b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"endstream",
        )
        builder.set_object(
            page_id,
            (
                f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
                f"/Resources << /Font << /F1 {font_regular} 0 R /F2 {font_bold} 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            ).encode("ascii"),
        )
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    builder.set_object(pages_id, f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii"))
    builder.set_object(catalog_id, f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("ascii"))
    builder.build(path)


if __name__ == "__main__":
    out = Path("docs/architecture/component_diagram.pdf")
    render(out)
    print(out.resolve())
