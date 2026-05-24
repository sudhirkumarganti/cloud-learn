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

    def multiline(self, x: float, y: float, text: str, size: int = 11, width: int = 92, leading: int | None = None, font: str = "F1") -> float:
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
        self.text(MARGIN, 8, "CloudLearn Service Spawn Diagram", size=9)
        self.text(PAGE_W - MARGIN - 46, 8, f"Page {page_no}", size=9)

    def content(self) -> bytes:
        return ("\n".join(self.parts) + "\n").encode("ascii")


def render(path: Path) -> None:
    pages: list[Page] = []

    # Page 1: startup flow
    p = Page()
    p.header("CloudLearn Service Spawn Diagram", "How the simulator starts, where host state lives, and how EC2 sandboxes are launched")
    p.box(32, 420, 148, 82, "Host Launcher", ["bash or PowerShell", "Detect host OS", "Write .cloudlearn-host.json"], fill=(0.97, 0.97, 0.92))
    p.box(208, 420, 148, 82, "Host Runtime Bridge", ["core/runtime_bridge.py", "Runs on host OS", "Executes Multipass or LXD"], fill=(0.95, 0.98, 0.95))
    p.box(384, 420, 170, 82, "Docker Compose", ["Starts simulator container", "Starts cloudsim container", "Mounts host config JSON"], fill=(0.95, 0.97, 0.99))
    p.box(582, 420, 178, 82, "simulator container", ["FastAPI app", "UI", "Provider routes", "CloudSim bridge"], fill=(0.99, 0.96, 0.94))
    p.box(208, 250, 148, 82, "cloudsim container", ["Space state", "Resource graph", "Events", "Summary"], fill=(0.96, 0.95, 0.99))
    p.box(384, 250, 170, 82, "Host OS sandboxes", ["Multipass on macOS/Windows", "LXD on Linux"], fill=(0.94, 0.98, 0.96))
    p.arrow(180, 461, 208, 461)
    p.arrow(356, 461, 384, 461)
    p.arrow(554, 461, 582, 461)
    p.arrow(666, 420, 666, 332)
    p.arrow(282, 420, 282, 332)
    p.arrow(469, 420, 469, 332)
    p.text(36, 196, "Key rule: the simulator container never launches Multipass or LXD directly. It asks the host bridge to do it on the host OS.", size=11)
    p.footer(1)
    pages.append(p)

    # Page 2: EC2 launch flow
    p = Page()
    p.header("EC2 Launch Sequence", "The instance is created in the simulator first, then the host bridge attempts to start the real sandbox")
    p.box(30, 420, 110, 70, "Browser", ["Launch modal", "Host OS hint fallback"], fill=(0.96, 0.96, 0.92))
    p.box(156, 420, 126, 70, "simulator UI", ["/api/ec2/instances", "WebSocket console"], fill=(0.95, 0.97, 0.99))
    p.box(300, 420, 126, 70, "server.py", ["Create instance", "Queue runtime start"], fill=(0.94, 0.98, 0.95))
    p.box(444, 420, 126, 70, "CloudSim", ["Upsert resource", "Track launch status"], fill=(0.98, 0.95, 0.95))
    p.box(588, 420, 166, 70, "Host runtime bridge", ["Call Multipass or LXD on host", "Return success or error"], fill=(0.95, 0.95, 0.99))
    p.box(300, 236, 126, 72, "Multipass", ["macOS / Windows host", "Host VM sandbox"], fill=(0.95, 0.98, 0.96))
    p.box(444, 236, 126, 72, "LXD", ["Linux host", "Container sandbox"], fill=(0.98, 0.98, 0.92))
    p.box(588, 236, 166, 72, "EC2 console session", ["SSH or shell stream", "Only after state is running"], fill=(0.94, 0.96, 0.99))
    p.arrow(140, 455, 156, 455)
    p.arrow(282, 455, 300, 455)
    p.arrow(426, 455, 444, 455)
    p.arrow(570, 455, 588, 455)
    p.arrow(671, 420, 671, 308)
    p.arrow(363, 420, 363, 308)
    p.arrow(507, 420, 507, 308)
    p.arrow(671, 236, 671, 308)
    p.text(36, 190, "Failure mode: if the host bridge is unreachable, the instance stays pending and launch_status becomes error. The UI shows launch failed.", size=11)
    p.footer(2)
    pages.append(p)

    # Page 3: responsibility table
    p = Page()
    p.header("Responsibilities by Layer", "This is the clean split that keeps the architecture understandable")
    p.box(28, 408, 208, 110, "Host OS", ["Detects actual OS", "Writes .cloudlearn-host.json", "Starts runtime bridge", "Owns Multipass/LXD"], fill=(0.97, 0.98, 0.92))
    p.box(256, 408, 208, 110, "simulator container", ["Serves UI", "Exposes AWS/GCP APIs", "Reads host config JSON", "Calls runtime bridge"], fill=(0.95, 0.97, 0.99))
    p.box(484, 408, 280, 110, "cloudsim container", ["Tracks spaces and resource graphs", "Stores events and summaries", "Reflects EC2/GCP resources in the active space"], fill=(0.95, 0.98, 0.95))
    p.text(28, 320, "Launch states", size=14, font="F2")
    p.bullets(28, 300, [
        "pending: the instance record exists but the runtime is not yet confirmed.",
        "running: the host runtime started successfully and the console can connect.",
        "launch_status=error: the host bridge could not start the sandbox.",
        "terminated: the sandbox was removed and the instance is no longer active.",
    ], size=11, width=86)
    p.text(396, 320, "Host bridge checks", size=14, font="F2")
    p.bullets(396, 300, [
        "Bridge health must be reachable from the container.",
        "Multipass is used on macOS and Windows.",
        "LXD is used on Linux.",
        "The browser OS hint is only a fallback; host config JSON is preferred.",
    ], size=11, width=84)
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
    out = Path("docs/architecture/service_spawn_diagram.pdf")
    render(out)
    print(out.resolve())
