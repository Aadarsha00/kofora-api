from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_success(message: str, data=None, status_code: int = status.HTTP_200_OK) -> Response:
    return Response(
        {
            "success": True,
            "message": message,
            "data": data,
            "errors": None,
        },
        status=status_code,
    )


def api_error(message: str, errors=None, status_code: int = status.HTTP_400_BAD_REQUEST) -> Response:
    return Response(
        {
            "success": False,
            "message": message,
            "data": None,
            "errors": errors,
        },
        status=status_code,
    )


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return api_error("Unexpected server error", errors={"detail": str(exc)}, status_code=500)

    message = "Request failed"
    if isinstance(response.data, dict) and "detail" in response.data:
        message = str(response.data.get("detail"))

    return api_error(message=message, errors=response.data, status_code=response.status_code)
