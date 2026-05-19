from pathlib import Path
import re
import subprocess
import time
from uuid import uuid4
from html.parser import HTMLParser

from langchain_core.tools import tool


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output"


BROWSER_PATHS = [
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
]


class ContractHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.blocks = []
        self.current_tag = ""
        self.buffer = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"head", "style", "script", "title"}:
            self.skip_depth += 1
            return
        if tag in {"h1", "h2", "p", "div"}:
            self._flush()
            self.current_tag = tag

    def handle_endtag(self, tag):
        if tag in {"head", "style", "script", "title"}:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if tag in {"h1", "h2", "p", "div"}:
            self._flush()
            self.current_tag = ""

    def handle_data(self, data):
        if self.skip_depth:
            return
        text = " ".join(data.split())
        if text:
            self.buffer.append(text)

    def _flush(self):
        if not self.buffer:
            return
        text = " ".join(self.buffer).strip()
        if text:
            self.blocks.append((self.current_tag or "p", text))
        self.buffer = []


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap_text(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines, line = [], ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if len(candidate) <= max_chars:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word[:max_chars]
    if line:
        lines.append(line)
    return lines


def _extract_blocks(html_content: str) -> list[tuple[str, str]]:
    parser = ContractHTMLParser()
    parser.feed(html_content)
    parser._flush()
    cleaned = []
    for tag, text in parser.blocks:
        text = re.sub(r"\s+", " ", text).strip()
        if text and "{{" not in text:
            cleaned.append((tag, text))
    return cleaned


def _pdf_color(hex_color: str) -> str:
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255
    g = int(hex_color[2:4], 16) / 255
    b = int(hex_color[4:6], 16) / 255
    return f"{r:.3f} {g:.3f} {b:.3f}"


def _text_op(x: int, y: int, text: str, font: str = "F1", size: int = 10, color: str = "#1f2937") -> str:
    return f"BT /{font} {size} Tf {_pdf_color(color)} rg {x} {y} Td ({_escape_pdf_text(text)}) Tj ET"


def _rect_op(x: int, y: int, width: int, height: int, fill: str | None = None, stroke: str | None = None) -> str:
    ops = []
    if fill:
        ops.append(f"{_pdf_color(fill)} rg")
    if stroke:
        ops.append(f"{_pdf_color(stroke)} RG")
    mode = "B" if fill and stroke else "f" if fill else "S"
    ops.append(f"{x} {y} {width} {height} re {mode}")
    return "\n".join(ops)


def _write_fallback_pdf(html_content: str, output_path: Path) -> None:
    blocks = _extract_blocks(html_content)
    pages: list[list[str]] = [[]]
    y = 792
    page_width = 595
    margin = 46
    content_width = page_width - (margin * 2)

    def page() -> list[str]:
        return pages[-1]

    def new_page():
        nonlocal y
        pages.append([])
        y = 792
        draw_header()

    def ensure_space(height: int):
        if y - height < 72:
            new_page()

    def draw_header():
        page().append(_text_op(margin, 810, "MULTI-AGENT ENTERPRISE CONTRACT GENERATOR", "F2", 8, "#2563eb"))
        page().append(_rect_op(margin, 802, content_width, 1, fill="#dbe3ef"))

    def add_paragraph(text: str, x: int = margin, width_chars: int = 88, size: int = 10, color: str = "#334155"):
        nonlocal y
        for line in _wrap_text(text, width_chars):
            ensure_space(16)
            page().append(_text_op(x, y, line, "F1", size, color))
            y -= 14
        y -= 4

    draw_header()

    for tag, text in blocks:
        if "Source request:" in text:
            ensure_space(58)
            page().append(_rect_op(margin, y - 36, content_width, 48, fill="#f8fafc", stroke="#dbe3ef"))
            page().append(_text_op(margin + 14, y - 4, "SOURCE REQUEST", "F2", 8, "#2563eb"))
            add_paragraph(text.replace("Source request:", "").strip(), margin + 14, 78, 9, "#475569")
            y -= 10
        elif tag == "h1":
            ensure_space(92)
            page().append(_rect_op(0, 682, page_width, 160, fill="#f8fafc"))
            page().append(_rect_op(0, 682, 7, 160, fill="#2563eb"))
            page().append(_text_op(margin, 748, "ENTERPRISE CONFIDENTIAL DOCUMENT", "F2", 9, "#2563eb"))
            page().append(_text_op(margin, 718, text.upper(), "F2", 24, "#111827"))
            page().append(_rect_op(margin, 700, 190, 3, fill="#2563eb"))
            y = 650
        elif tag == "h2":
            ensure_space(54)
            y -= 8
            page().append(_rect_op(margin, y - 19, content_width, 30, fill="#ffffff", stroke="#d7dee9"))
            page().append(_rect_op(margin, y - 19, 5, 30, fill="#2563eb"))
            page().append(_text_op(margin + 14, y - 9, text, "F2", 13, "#0f172a"))
            y -= 34
        elif len(text) > 260 and tag == "div":
            continue
        else:
            add_paragraph(text)

    ensure_space(112)
    page().append(_text_op(margin, y - 4, "EXECUTION", "F2", 13, "#0f172a"))
    y -= 34
    box_w = int((content_width - 22) / 2)
    page().append(_rect_op(margin, y - 72, box_w, 72, fill="#f8fafc", stroke="#d7dee9"))
    page().append(_rect_op(margin + box_w + 22, y - 72, box_w, 72, fill="#f8fafc", stroke="#d7dee9"))
    page().append(_text_op(margin + 12, y - 20, "DISCLOSING PARTY", "F2", 9, "#2563eb"))
    page().append(_text_op(margin + 12, y - 44, "Name: __________________________", "F1", 9, "#334155"))
    page().append(_text_op(margin + 12, y - 60, "Date: __________________________", "F1", 9, "#334155"))
    page().append(_text_op(margin + box_w + 34, y - 20, "RECEIVING PARTY", "F2", 9, "#2563eb"))
    page().append(_text_op(margin + box_w + 34, y - 44, "Name: __________________________", "F1", 9, "#334155"))
    page().append(_text_op(margin + box_w + 34, y - 60, "Date: __________________________", "F1", 9, "#334155"))

    objects = []
    catalog_id = 1
    pages_id = 2
    font_id = 3
    bold_font_id = 4
    page_ids = []

    for page_number, page_ops in enumerate(pages, start=1):
        footer = [
            _rect_op(margin, 42, content_width, 1, fill="#dbe3ef"),
            _text_op(margin, 26, f"Multi-Agent Enterprise Contract Generator | Page {page_number} of {len(pages)}", "F1", 8, "#64748b"),
        ]
        content_parts = page_ops + footer
        stream = "\n".join(content_parts).encode("latin-1", errors="replace")
        content_id = len(objects) + 5
        page_id = content_id + 1
        objects.append(f"{content_id} 0 obj\n<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream\nendobj\n")
        objects.append(
            f"{page_id} 0 obj\n<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 {font_id} 0 R /F2 {bold_font_id} 0 R >> >> /Contents {content_id} 0 R >>\nendobj\n".encode()
        )
        page_ids.append(page_id)

    header_objects = [
        f"{catalog_id} 0 obj\n<< /Type /Catalog /Pages {pages_id} 0 R >>\nendobj\n".encode(),
        f"{pages_id} 0 obj\n<< /Type /Pages /Kids [{' '.join(f'{pid} 0 R' for pid in page_ids)}] /Count {len(page_ids)} >>\nendobj\n".encode(),
        f"{font_id} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n".encode(),
        f"{bold_font_id} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n".encode(),
    ]
    all_objects = header_objects + objects
    pdf = [b"%PDF-1.4\n"]
    offsets = [0]
    for obj in all_objects:
        offsets.append(sum(len(part) for part in pdf))
        pdf.append(obj)
    xref = sum(len(part) for part in pdf)
    pdf.append(f"xref\n0 {len(all_objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        pdf.append(f"{offset:010d} 00000 n \n".encode())
    pdf.append(
        f"trailer\n<< /Size {len(all_objects) + 1} /Root {catalog_id} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    output_path.write_bytes(b"".join(pdf))


def _write_browser_pdf(html_content: str, output_path: Path) -> bool:
    browser = next((path for path in BROWSER_PATHS if path.exists()), None)
    if not browser:
        return False

    html_path = output_path.with_suffix(".print.html")
    user_data_dir = OUTPUT_DIR / f"browser_profile_{uuid4().hex[:8]}"
    html_path.write_text(_prepare_browser_print_html(html_content), encoding="utf-8")

    command = [
        str(browser),
        "--headless",
        "--disable-gpu",
        "--no-first-run",
        f"--user-data-dir={user_data_dir}",
        f"--print-to-pdf={output_path}",
        html_path.resolve().as_uri(),
    ]
    try:
        subprocess.run(command, check=False, timeout=45, capture_output=True)
        for _ in range(20):
            if output_path.exists() and output_path.stat().st_size > 1000:
                return True
            time.sleep(0.25)
    finally:
        try:
            html_path.unlink(missing_ok=True)
        except OSError:
            pass
    return output_path.exists() and output_path.stat().st_size > 1000


def _prepare_browser_print_html(html_content: str) -> str:
    print_css = """
    <style>
      @page { size: A4; margin: 12mm 14mm; }
      html, body { margin: 0 !important; padding: 0 !important; background: #ffffff !important; }
      body {
        color: #111827 !important;
        font-family: "Segoe UI", Arial, sans-serif !important;
        font-size: 11px !important;
        line-height: 1.42 !important;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
      }
      .cover { margin-bottom: 12px !important; padding: 0 0 12px !important; page-break-after: avoid !important; }
      .summary { margin: 8px 0 10px !important; padding: 8px 10px !important; }
      .contract-section {
        margin: 9px 0 !important;
        padding: 9px 12px !important;
        page-break-inside: auto !important;
        break-inside: auto !important;
      }
      h1 { font-size: 24px !important; margin: 6px 0 8px !important; }
      h2 { font-size: 13px !important; margin: 0 0 5px !important; }
      p { margin: 0 0 5px !important; }
      .signature-grid { margin-top: 14px !important; gap: 16px !important; }
      .meta { margin-top: 8px !important; }
    </style>
    """
    if "</head>" in html_content:
        return html_content.replace("</head>", f"{print_css}</head>", 1)
    return f"<!DOCTYPE html><html><head>{print_css}</head><body>{html_content}</body></html>"


@tool
def generate_pdf(html_content: str) -> str:
    """Generate a PDF from HTML content and return the saved file path."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = OUTPUT_DIR / f"nda_contract_{uuid4().hex[:10]}.pdf"

    if not _write_browser_pdf(html_content, output_path):
        try:
            from weasyprint import HTML

            HTML(string=_prepare_browser_print_html(html_content), base_url=str(PROJECT_ROOT)).write_pdf(str(output_path))
        except OSError:
            _write_fallback_pdf(html_content, output_path)
    return str(output_path)
