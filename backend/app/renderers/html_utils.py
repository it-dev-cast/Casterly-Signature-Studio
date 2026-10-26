"""Small helpers for building email-safe HTML."""
import html
import re
from html.parser import HTMLParser

TABLE_ATTRS = 'role="presentation" cellpadding="0" cellspacing="0" border="0"'
# Outlook for Windows ignores line-height without this, so lines come out taller than designed.
EXACT = "mso-line-height-rule:exactly;"


def e(value: str | None) -> str:
    """HTML-escape any user-provided value (text or attribute)."""
    return html.escape(value or "", quote=True)


def tel_href(number: str) -> str:
    return "tel:" + re.sub(r"[^0-9+]", "", number)


def display_url(url: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", url).rstrip("/")


def link(href: str, text: str, style: str) -> str:
    return f'<a href="{e(href)}" target="_blank" rel="noopener" style="{style}">{e(text)}</a>'


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("tr", "br"):
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def html_to_text(markup: str) -> str:
    """Plain-text version of a signature (Outlook uses it for plain-text emails)."""
    parser = _TextExtractor()
    parser.feed(markup)
    text = "".join(parser.parts).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def logo_img(logo) -> str:
    return (
        f'<img src="{e(logo.src)}" alt="{e(logo.alt)}" width="{logo.width}" height="{logo.height}" '
        f'style="display:block;width:{logo.width}px;height:{logo.height}px;border:0;outline:none;" />'
    )

