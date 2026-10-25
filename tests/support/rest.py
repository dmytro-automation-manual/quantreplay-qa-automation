"""REST response checks."""
from framework.assertions.expect import check_fields


def check_response(response, title: str, *, status_code: int, result=None) -> None:
    """HTTP status always; the `result` message only where the documentation and the venue agree."""
    expected = {"status_code": status_code}
    if result is not None:
        expected["result"] = result
    check_fields(title, response, expected)
