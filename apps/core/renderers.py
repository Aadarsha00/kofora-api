from rest_framework.renderers import JSONRenderer


class EnvelopedJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        if renderer_context is None:
            return super().render(data, accepted_media_type, renderer_context)

        response = renderer_context.get("response")
        if response is None:
            return super().render(data, accepted_media_type, renderer_context)

        if isinstance(data, dict) and {"success", "message", "data", "errors"}.issubset(data.keys()):
            payload = data
        elif response.status_code >= 400:
            payload = {
                "success": False,
                "message": "Request failed",
                "data": None,
                "errors": data,
            }
        else:
            payload = {
                "success": True,
                "message": "Request successful",
                "data": data,
                "errors": None,
            }

        return super().render(payload, accepted_media_type, renderer_context)
