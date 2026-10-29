"""Plain data passed into renderers.

Renderers never touch the database or ORM objects. The signature service resolves
everything (absolute URLs, fallbacks) into these views first, which keeps renderers
pure, easily testable and reusable by future Outlook / Gmail integrations.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TemplateStyle:
    layout: str = "classic"
    primary_color: str = "#1F2A44"
    accent_color: str = "#2563EB"
    font_family: str = "Arial, Helvetica, sans-serif"
    show_photo: bool = True
    show_social: bool = True


@dataclass(frozen=True)
class BannerView:
    title: str
    image_src: str  # absolute http(s) URL
    target_url: str | None = None
    # Displayed height in px at the banner width. Classic Outlook needs it to size the image;
    # left out when the image behind image_src can change shape (saved live signatures).
    height: int | None = None


@dataclass(frozen=True)
class EmployeeView:
    name: str
    designation: str
    department: str | None = None
    company: str | None = None
    email: str | None = None
    phone: str | None = None
    mobile: str | None = None
    website: str | None = None
    address: str | None = None  # one line
    photo_src: str | None = None  # absolute http(s) URL
    socials: list[tuple[str, str]] = field(default_factory=list)  # (label, url)


@dataclass(frozen=True)
class LogoView:
    src: str  # absolute http(s) URL
    alt: str  # company name
    width: int
    height: int


@dataclass(frozen=True)
class SignatureContext:
    employee: EmployeeView
    style: TemplateStyle
    banner: BannerView | None = None
    disclaimer: str | None = None
    logo: LogoView | None = None  # shown at the right, just above the banner
