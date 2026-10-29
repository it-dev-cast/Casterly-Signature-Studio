"""THE single banner renderer.

Used by the final signature renderer AND by every banner preview in the UI
(admin preview, overview, employee page), so previews can never drift from
what is actually sent.
"""
from app.renderers.context import BannerView
from app.renderers.html_utils import TABLE_ATTRS, e

BANNER_WIDTH = 480  # compact: keeps the whole signature small in the email


def render_banner_html(banner: BannerView, width: int = BANNER_WIDTH) -> str:
    # Classic Outlook ignores max-width and sizes the image from the width/height attributes;
    # every other client uses the CSS, so the banner still shrinks on narrow (mobile) screens.
    height = f' height="{banner.height}"' if banner.height else ""
    img = (
        f'<img src="{e(banner.image_src)}" alt="{e(banner.title)}" title="{e(banner.title)}" '
        f'width="{width}"{height} style="display:block;width:{width}px;max-width:100%;height:auto;'
        f'border:0;outline:none;text-decoration:none;" />'
    )
    if banner.target_url:
        img = (
            f'<a href="{e(banner.target_url)}" target="_blank" rel="noopener" '
            f'style="text-decoration:none;border:0;">{img}</a>'
        )
    return (
        f'<table {TABLE_ATTRS} width="{width}" '
        f'style="border-collapse:collapse;width:{width}px;max-width:100%;">'
        f'<tr><td style="padding:0;">{img}</td></tr></table>'
    )
