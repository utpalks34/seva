from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        email = (request.data.get("email") or "").strip().lower()
        return self.cache_format % {"scope": self.scope, "ident": f"{ident}:{email}"}
