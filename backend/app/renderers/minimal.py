"""Minimal layout: text-only, compact contact line; banner below."""
from app.renderers.banner import BANNER_WIDTH, render_banner_html
from app.renderers.context import SignatureContext
from app.renderers.html_utils import EXACT, TABLE_ATTRS, display_url, e, link, logo_img, tel_href

TEXT = "#374151"


def render(ctx: SignatureContext) -> str:
    emp, s = ctx.employee, ctx.style
    title = " | ".join(e(x) for x in (emp.designation, emp.department, emp.company) if x)
    link_style = f"color:{TEXT};text-decoration:none;"
    contacts = []
    if emp.email:
        contacts.append(link(f"mailto:{emp.email}", emp.email, link_style))
    if emp.phone:
        contacts.append(link(tel_href(emp.phone), emp.phone, link_style))
    if emp.mobile:
        contacts.append(link(tel_href(emp.mobile), emp.mobile, link_style))
    if emp.website:
        contacts.append(link(emp.website, display_url(emp.website), link_style))
    if s.show_social:
        contacts.extend(
            link(url, label, f"color:{s.accent_color};text-decoration:none;") for label, url in emp.socials
        )
    sep = '<span style="color:#D1D5DB;">&nbsp;&middot;&nbsp;</span>'
    address_row = (
        f'<tr><td style="padding:1px 0 0 0;font-size:10px;line-height:13px;{EXACT}color:#6B7280;">{e(emp.address)}</td></tr>'
        if emp.address else ""
    )

    rows = [
        f'<tr><td style="padding:0;font-size:14px;line-height:18px;{EXACT}font-weight:bold;'
        f'color:{s.primary_color};">{e(emp.name)}</td></tr>',
        f'<tr><td style="padding:0 0 3px 0;font-size:11px;line-height:15px;{EXACT}color:#6B7280;">{title}</td></tr>',
    ]
    if contacts:
        rows.append(f'<tr><td style="padding:0;font-size:11px;line-height:15px;{EXACT}">{sep.join(contacts)}</td></tr>')
    if address_row:
        rows.append(address_row)
    if ctx.logo:
        # Right-aligned in a banner-wide table, directly above the banner.
        # Its own line height: an inherited exact one would make Word clip the logo.
        rows.append(
            f'<tr><td align="right" style="padding:6px 0 0 0;line-height:{ctx.logo.height}px;{EXACT}">'
            f"{logo_img(ctx.logo)}</td></tr>"
        )
    if ctx.banner:
        top = 6 if ctx.logo else 8
        rows.append(f'<tr><td style="padding:{top}px 0 0 0;">{render_banner_html(ctx.banner)}</td></tr>')
    if ctx.disclaimer:
        rows.append(
            f'<tr><td style="padding:6px 0 0 0;font-size:9px;line-height:12px;{EXACT}color:#9CA3AF;">'
            f"{e(ctx.disclaimer)}</td></tr>"
        )
    width = f' width="{BANNER_WIDTH}"' if ctx.logo else ""
    # Classic Outlook ignores max-width, so the pixel width is the CSS width (as in classic.py).
    # No font-size/line-height here: every row sets its own, and Word would pass them to images.
    width_css = f"width:{BANNER_WIDTH}px;max-width:100%;" if ctx.logo else ""
    return (
        f'<table {TABLE_ATTRS}{width} style="border-collapse:collapse;{width_css}font-family:{s.font_family};'
        f'color:{TEXT};">{"".join(rows)}</table>'
    )
