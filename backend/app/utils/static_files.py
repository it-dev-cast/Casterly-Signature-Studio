from starlette.staticfiles import StaticFiles


class RevalidatingStaticFiles(StaticFiles):
    """Static files that clients must re-check (by ETag) before reusing a cached copy.

    Without a Cache-Control header, browsers and mail clients guess how long to keep a file,
    so a replaced photo or image could keep showing for hours.
    """

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response
