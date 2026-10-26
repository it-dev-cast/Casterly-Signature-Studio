"""Signature layout registry.

To add a new signature design: write a `render(ctx) -> str` module and register it
here. Admins can then create templates that use the new layout.
"""
from collections.abc import Callable
from dataclasses import dataclass

from app.renderers import classic, minimal
from app.renderers.context import SignatureContext


@dataclass(frozen=True)
class Layout:
    key: str
    name: str
    description: str
    render: Callable[[SignatureContext], str]


LAYOUTS: dict[str, Layout] = {
    "classic": Layout(
        "classic",
        "Classic",
        "Photo, accent divider, full contact details and social links.",
        classic.render,
    ),
    "minimal": Layout(
        "minimal",
        "Minimal",
        "Text-only, compact single-line contact details.",
        minimal.render,
    ),
}

DEFAULT_LAYOUT = "classic"


def render_layout(ctx: SignatureContext) -> str:
    layout = LAYOUTS.get(ctx.style.layout, LAYOUTS[DEFAULT_LAYOUT])
    return layout.render(ctx)
