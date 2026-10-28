"""Signature generation engine:  EMPLOYEE + TEMPLATE + CURRENT BANNER -> HTML.

Nothing here is persisted. Every call reads the current published banner, so
publishing a new banner changes every employee's signature with zero writes to
employee records. This module is also the integration point for future
Outlook add-in / Gmail signature sync clients.
"""
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app import branding
from app.database.models import AppSettings, Banner, Employee, SignatureTemplate
from app.database.types import utcnow
from app.renderers import render_layout
from app.renderers.context import BannerView, EmployeeView, LogoView, SignatureContext, TemplateStyle
from app.renderers.html_utils import e
from app.services import banner_service, employee_service, settings_service, template_service
from app.utils.urls import resolve_public_url


@dataclass
class SignatureResult:
    employee: Employee
    template: SignatureTemplate | None
    banner: Banner | None
    html: str
    # Same signature, but the banner uses the live /banner/current(.png) addresses. This is the
    # version employees paste into Outlook once: new banners then appear without re-pasting.
    live_html: str = ""
    generated_at: datetime = field(default_factory=utcnow)


def _other_label(url: str) -> str:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    return (host.split(".")[0] or "Link").capitalize()


def employee_view(employee: Employee, app_settings: AppSettings | None) -> EmployeeView:
    socials = []
    if employee.linkedin_url:
        socials.append(("LinkedIn", employee.linkedin_url))
    if employee.twitter_url:
        socials.append(("X", employee.twitter_url))
    if employee.instagram_url:
        socials.append(("Instagram", employee.instagram_url))
    if employee.other_social_url:
        socials.append((_other_label(employee.other_social_url), employee.other_social_url))
    return EmployeeView(
        name=employee.full_name,
        designation=employee.designation,
        department=employee.department,
        company=employee.company or (app_settings.company_name if app_settings else None),
        email=employee.email,
        phone=employee.phone,
        mobile=employee.mobile,
        website=employee.website or (app_settings.company_website if app_settings else None),
        address=", ".join(p.strip() for p in (employee.address or "").splitlines() if p.strip()) or None,
        photo_src=resolve_public_url(employee.profile_photo_url),
        socials=socials,
    )


def template_style(template: SignatureTemplate | None) -> TemplateStyle:
    if template is None:
        return TemplateStyle()  # built-in default design
    return TemplateStyle(
        layout=template.layout,
        primary_color=template.primary_color,
        accent_color=template.accent_color,
        font_family=template.font_family,
        show_photo=template.show_photo,
        show_social=template.show_social,
    )


# Fixed public addresses that always serve the CURRENT published banner (app/api/live_banner.py).
LIVE_BANNER_IMAGE = "/banner/current.png"
LIVE_BANNER_LINK = "/banner/current"


def banner_version(banner: Banner | None) -> str:
    """Changes whenever the banner in signatures changes: another banner, an edit, or none."""
    if banner is None:
        return "none"
    return f"{banner.id}-{int(banner.updated_at.timestamp() * 1_000_000)}"


def live_banner_view(app_settings: AppSettings | None, version: str | None = None) -> BannerView:
    """Banner that points at the live addresses instead of one specific banner.

    Used for signatures pasted or installed into Outlook: whatever banner is published at
    the moment an email is opened is the one shown, so nobody needs to re-paste or reinstall.

    With `version` (see banner_version) the addresses get "?v=<version>". Outlook and Microsoft's
    image proxy cache images by URL and ignore no-cache, so a fixed URL keeps showing the old
    banner; a new URL per banner is fetched fresh. The endpoints ignore the parameter, so an
    email sent with an older version still shows the current banner once its cache expires.
    """
    query = f"?v={version}" if version else ""
    return BannerView(
        title=app_settings.company_name if app_settings else "Company banner",
        image_src=(resolve_public_url(LIVE_BANNER_IMAGE) or "") + query,
        target_url=resolve_public_url(LIVE_BANNER_LINK) + query,
    )


def render_signature_html(
    employee: Employee,
    template: SignatureTemplate | None,
    banner: Banner | None,
    app_settings: AppSettings | None = None,
    *,
    live_banner: bool = False,
    versioned_banner: bool = False,
) -> str:
    if live_banner:
        banner_view = live_banner_view(app_settings, banner_version(banner) if versioned_banner else None)
    else:
        banner_view = banner_service.banner_view(banner) if banner else None
    ctx = SignatureContext(
        employee=employee_view(employee, app_settings),
        style=template_style(template),
        banner=banner_view,
        disclaimer=app_settings.legal_disclaimer if app_settings else None,
        logo=logo_view(app_settings),
    )
    return render_layout(ctx)


def logo_view(app_settings: AppSettings | None) -> LogoView | None:
    """The built-in company logo, unless an admin switched it off in Settings."""
    if app_settings is None or not app_settings.show_logo_in_signature:
        return None
    width, height = branding.logo_display_size()
    return LogoView(
        src=resolve_public_url(branding.LOGO_PATH) or "",
        alt=app_settings.company_name,
        width=width,
        height=height,
    )


def generate_employee_signature(
    db: Session, employee_id: int, template_id: int | None = None, *, live_banner: bool = False,
    versioned_banner: bool = False,
) -> SignatureResult:
    """`versioned_banner` (with `live_banner`): live addresses with ?v=<banner version>, for
    signatures generated fresh for every email (the Outlook add-in). Saved signatures (installer,
    setup page, live_html) keep the plain addresses, which can't be updated once saved."""
    employee = employee_service.get_employee(db, employee_id)                   # 1. employee
    template = (                                                                 # 2. template
        template_service.get_template(db, template_id)
        if template_id is not None
        else template_service.get_active_template(db)
    )
    banner = banner_service.get_current_published_banner(db)                    # 3. banner
    app_settings = settings_service.get_app_settings(db)
    html = render_signature_html(employee, template, banner, app_settings,                     # 4.
                                 live_banner=live_banner, versioned_banner=versioned_banner)
    live_html = (
        html if live_banner and not versioned_banner
        else render_signature_html(employee, template, banner, app_settings, live_banner=True)
    )
    return SignatureResult(employee=employee, template=template, banner=banner, html=html, live_html=live_html)  # 5.


def wrap_document(fragment: str, title: str) -> str:
    """A standalone HTML document around a signature (for download / browser preview)."""
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en"><head><meta charset="utf-8" />'
        '<meta name="viewport" content="width=device-width, initial-scale=1" />'
        f"<title>{e(title)}</title></head>"
        '<body style="margin:0;padding:24px;background:#ffffff;">\n'
        f"<!-- Email signature generated by Signature Studio -->\n{fragment}\n"
        "</body></html>\n"
    )
