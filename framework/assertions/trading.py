"""Trading checks with the mandatory fields built into the signature.

Every execution report check must state order_id, exec_type, ord_status, symbol, order_qty and price -
the keyword-only parameters make it impossible to forget one. Extra fields go into **more.
"""
from typing import Any

from framework.assertions.expect import Matcher, check_fields


def check_execution_report(report: Any, title: str, *, order_id: Any, exec_type: Any, ord_status: Any,
                           symbol: Any, order_qty: Any, price: Any, **more: Any) -> None:
    check_fields(title, report, {"msg_type": _msg_type("8"), "order_id": order_id, "exec_type": exec_type,
                                 "ord_status": ord_status, "symbol": symbol, "order_qty": order_qty,
                                 "price": price, **more})


def check_cancel_reject(reject: Any, title: str, *, order_id: Any, ord_status: Any, cxl_rej_response_to: Any,
                        text: Any, **more: Any) -> None:
    """OrderCancelReject (35=9) has no symbol/qty/price tags; the order itself is then checked in the book."""
    check_fields(title, reject, {"msg_type": _msg_type("9"), "order_id": order_id, "ord_status": ord_status,
                                 "cxl_rej_response_to": cxl_rej_response_to, "text": text, **more})


class _msg_type(Matcher):
    def __init__(self, value: str):
        self.value = value

    def matches(self, actual: Any) -> bool:
        return getattr(actual, "value", actual) == self.value

    def __str__(self) -> str:
        return {"8": "EXECUTION_REPORT(8)", "9": "ORDER_CANCEL_REJECT(9)"}[self.value]
