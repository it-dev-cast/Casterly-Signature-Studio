"""THE single banner renderer.

Used by the final signature renderer AND by every banner preview in the UI
(admin preview, overview, employee page), so previews can never drift from
what is actually sent.
"""
from app.renderers.context import BannerView
from app.renderers.html_utils import TABLE_ATTRS, e

BANNER_WIDTH = 480  # compact: keeps the whole signature small in the email


def render_banner_html(banner: BannerView, width: int = BANNER_WIDTH) -> str:
    img = (
        f'<img src="{e(banner.image_src)}" alt="{e(banner.title)}" title="{e(banner.title)}" '
        f'width="{width}" style="display:block;width:100%;max-width:{width}px;height:auto;'
        f'border:0;outline:none;text-decoration:none;" />'
    )
    if banner.target_url:
        img = (
            f'<a href="{e(banner.target_url)}" target="_blank" rel="noopener" '
            f'style="text-decoration:none;border:0;">{img}</a>'
        )
    return (
        f'<table {TABLE_ATTRS} width="{width}" '
        f'style="border-collapse:collapse;width:100%;max-width:{width}px;">'
        f'<tr><td style="padding:0;">{img}</td></tr></table>'
    )
