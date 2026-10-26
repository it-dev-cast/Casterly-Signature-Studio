"""Classic layout: [photo] | name, designation, org, contact lines | 50x50 logo top-right; banner below.

Kept compact so a pasted signature takes little room in the email: small type, tight
line heights (enforced in Outlook with mso-line-height-rule) and one short line per contact.
Everything is nested tables with inline styles, so Outlook, Gmail and Microsoft 365 agree.
"""
from app.renderers.banner import BANNER_WIDTH, render_banner_html
from app.renderers.context import SignatureContext
from app.renderers.html_utils import EXACT, TABLE_ATTRS, display_url, e, link, logo_img, tel_href

MUTED = "#6B7280"
TEXT = "#374151"
PHOTO = 64
LOGO_BOX = 50  # the logo is fitted into a 50x50 slot at the top-right of the details
LABEL = 16  # width of the P / E / W / A label column, so the values line up
SEP = '<span style="color:#D1D5DB;">&nbsp;|&nbsp;</span>'
# Addresses are capped at two lines. Outlook ignores max-height/overflow, so a longer one
# (a custom "Other" address in nexusAuth) is shortened instead: ~5.4px per character at
# 10px Arial across the address column. Both preset office addresses fit without shortening.
ADDRESS_CHAR_PX = 5.4


def _line(content: str, *, size: int = 11, height: int = 15, top: int = 0, extra: str = "") -> str:
    return (
        f'<tr><td style="padding:{top}px 0 0 0;font-size:{size}px;line-height:{height}px;{EXACT}{extra}">'
        f"{content}</td></tr>"
    )


def _contact(label: str, value: str, primary: str, *, size: int = 11, height: int = 15, color: str = TEXT) -> str:
    return (
        f'<tr><td valign="top" width="{LABEL}" style="padding:0;width:{LABEL}px;font-size:{size}px;'
        f'line-height:{height}px;{EXACT}font-weight:bold;color:{primary};">{label}&nbsp;</td>'
        f'<td valign="top" style="padding:0;font-size:{size}px;line-height:{height}px;{EXACT}color:{color};">'
        f"{value}</td></tr>"
    )


def _fit(text: str, max_chars: int) -> str:
    """Shorten at a word boundary so the text stays within max_chars."""
    if len(text) <= max_chars:
        return text
    cut = text[: max_chars - 1].rsplit(" ", 1)[0].rstrip(" ,;-")
    return cut + "…"


def render(ctx: SignatureContext) -> str:
    emp, s = ctx.employee, ctx.style
    show_photo = bool(s.show_photo and emp.photo_src)
    link_style = f"color:{TEXT};text-decoration:none;"

    rows: list[str] = [
        _line(e(emp.name), size=16, height=20, extra=f"font-weight:bold;color:{s.primary_color};"),
        _line(e(emp.designation), size=12, height=16, extra=f"font-weight:bold;color:{s.accent_color};"),
    ]
    org = SEP.join(e(x) for x in (emp.department, emp.company) if x)
    if org:
        rows.append(_line(org, extra=f"color:{MUTED};"))

    contacts = []
    if emp.phone:
        contacts.append(_contact("P", link(tel_href(emp.phone), emp.phone, link_style), s.primary_color))
    if emp.mobile:
        contacts.append(_contact("M", link(tel_href(emp.mobile), emp.mobile, link_style), s.primary_color))
    if emp.email:
        contacts.append(_contact("E", link(f"mailto:{emp.email}", emp.email, link_style), s.primary_color))
    if emp.website:
        contacts.append(_contact("W", link(emp.website, display_url(emp.website), link_style), s.primary_color))
    if emp.address:
        # One step smaller and softer than the contacts, so it reads as secondary detail.
        column = BANNER_WIDTH - LOGO_BOX - 12 - LABEL - ((PHOTO + 14) if show_photo else 0)
        address = _fit(emp.address, int(2 * column / ADDRESS_CHAR_PX))
        contacts.append(_contact("A", e(address), s.primary_color, size=10, height=13, color=MUTED))
    if contacts:
        rows.append(
            f'<tr><td style="padding:6px 0 0 0;"><table {TABLE_ATTRS} style="border-collapse:collapse;">'
            f'{"".join(contacts)}</table></td></tr>'
        )

    if s.show_social and emp.socials:
        links = SEP.join(
            link(url, label, f"color:{s.accent_color};text-decoration:none;font-weight:bold;")
            for label, url in emp.socials
        )
        rows.append(_line(links, top=4))

    details = f'<table {TABLE_ATTRS} style="border-collapse:collapse;">{"".join(rows)}</table>'

    cells: list[str] = []
    if show_photo:
        cells.append(
            f'<td valign="top" width="{PHOTO}" style="padding:0 14px 0 0;width:{PHOTO}px;">'
            f'<img src="{e(emp.photo_src)}" alt="{e(emp.name)}" width="{PHOTO}" height="{PHOTO}" '
            f'style="display:block;width:{PHOTO}px;height:{PHOTO}px;border:0;border-radius:{PHOTO // 2}px;" />'
            "</td>"
        )
    # With a logo, the details column takes the free space so the logo sits in the top-right
    # corner; the table is banner-wide so the logo lines up with the banner's right edge.
    grow = ' width="100%"' if ctx.logo else ""
    cells.append(f'<td valign="top"{grow} style="padding:0 12px 0 0;">{details}</td>')
    if ctx.logo:
        # A fixed 50x50 box (its own table, so no client can squeeze it); the logo is fitted
        # inside it with its aspect ratio kept and pinned to the top-right corner.
        cells.append(
            f'<td valign="top" align="right" width="{LOGO_BOX}" style="padding:0;width:{LOGO_BOX}px;">'
            f'<table {TABLE_ATTRS} width="{LOGO_BOX}" style="border-collapse:collapse;width:{LOGO_BOX}px;">'
            f'<tr><td valign="top" align="right" width="{LOGO_BOX}" height="{LOGO_BOX}" '
            f'style="padding:0;width:{LOGO_BOX}px;height:{LOGO_BOX}px;">{logo_img(ctx.logo)}</td></tr></table></td>'
        )
    colspan = len(cells)

    body = [f"<tr>{''.join(cells)}</tr>"]
    if ctx.banner:
        body.append(
            f'<tr><td colspan="{colspan}" style="padding:8px 0 0 0;">{render_banner_html(ctx.banner)}</td></tr>'
        )
    if ctx.disclaimer:
        body.append(
            f'<tr><td colspan="{colspan}" style="padding:6px 0 0 0;font-size:9px;line-height:12px;{EXACT}'
            f'color:#9CA3AF;">{e(ctx.disclaimer)}</td></tr>'
        )

    width = f' width="{BANNER_WIDTH}"' if ctx.logo else ""
    width_css = f"width:100%;max-width:{BANNER_WIDTH}px;" if ctx.logo else ""
    return (
        f'<table {TABLE_ATTRS}{width} style="border-collapse:collapse;{width_css}font-family:{s.font_family};'
        f'color:{TEXT};font-size:12px;line-height:15px;{EXACT}background-color:#ffffff;">{"".join(body)}</table>'
    )
