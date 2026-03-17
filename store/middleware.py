from django.utils import translation

from .geo import get_geo_profile, get_preferred_language, override_profile_language
from .request_context import set_current_request, clear_current_request


class GeoProfileMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_request(request)
        profile = get_geo_profile(request)
        preferred_language = get_preferred_language(request, profile.language)
        profile = override_profile_language(profile, preferred_language)
        request.geo_profile = profile

        if profile.language:
            translation.activate(profile.language)
            request.LANGUAGE_CODE = profile.language

        try:
            response = self.get_response(request)
        finally:
            translation.deactivate()
            clear_current_request()
        return response
