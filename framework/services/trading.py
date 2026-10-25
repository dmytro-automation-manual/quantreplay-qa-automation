"""Order entry service: business actions on the FIX order session (place, replace, cancel, wait for fills).

Layer rule: depends on a session object with send()/receive() (duck-typed, injected by the caller),
on the FIX mapping and on the models. Makes no assertions - tests decide what is right.
"""
from decimal import Decimal
from typing import Protocol

from framework.fix import messages
from framework.fix.tags import TERMINAL_ORD_STATUSES, ExecType, MsgType, OrdStatus, Tag
from framework.models.orders import ExecutionReport, NewOrderRequest, Order, OrderCancelReject


class Session(Protocol):
    def send(self, msg_type: str, fields) -> None: ...
    def receive(self, predicate, timeout: float | None = None): ...


_KEEP = object()


class TradingService:
    """One instance per test: it remembers every order the test created, so the test teardown
    can cancel what is still active and leave the order book as it found it."""

    def __init__(self, session: Session):
        self._session = session
        self.orders: list[Order] = []

    # --- requests --------------------------------------------------------------------------------
    def place(self, request: NewOrderRequest) -> tuple[Order | None, ExecutionReport]:
        """Send NewOrderSingle; return the order (None if rejected) and the first execution report."""
        cl_ord_id = messages.new_id()
        self._session.send(MsgType.NEW_ORDER_SINGLE.value,
                           messages.new_order_single(request, cl_ord_id, messages.transact_time()))
        report = self._wait_report(cl_ord_id)
        if report.ord_status == OrdStatus.REJECTED:
            return None, report
        order = Order(order_id=report.order_id, cl_ord_id=cl_ord_id, symbol=request.symbol, side=request.side,
                      order_qty=request.order_qty, price=request.price, ord_type=request.ord_type,
                      time_in_force=request.time_in_force, ord_status=report.ord_status, history=[report])
        self.orders.append(order)
        return order, report

    def replace(self, order: Order, *, order_qty: Decimal | None = None, price: Decimal | None = None,
                time_in_force=_KEEP) -> ExecutionReport | OrderCancelReject:
        """Send OrderCancelReplaceRequest; unchanged fields are taken from the order."""
        cl_ord_id = messages.new_id()
        new_qty = order_qty if order_qty is not None else order.order_qty
        new_price = price if price is not None else order.price
        new_tif = order.time_in_force if time_in_force is _KEEP else time_in_force
        self._session.send(MsgType.ORDER_CANCEL_REPLACE_REQUEST.value,
                           messages.order_cancel_replace_request(order, cl_ord_id, messages.transact_time(),
                                                                 order_qty=new_qty, price=new_price,
                                                                 time_in_force=new_tif))
        report = self._wait_report(cl_ord_id)
        if isinstance(report, ExecutionReport) and report.exec_type == ExecType.REPLACED:
            order.cl_ord_id, order.order_qty, order.price = cl_ord_id, new_qty, new_price
            self._track(order, report)
        return report

    def cancel(self, order: Order) -> ExecutionReport | OrderCancelReject:
        """Send OrderCancelRequest."""
        cl_ord_id = messages.new_id()
        self._session.send(MsgType.ORDER_CANCEL_REQUEST.value,
                           messages.order_cancel_request(order, cl_ord_id, messages.transact_time()))
        report = self._wait_report(cl_ord_id)
        if isinstance(report, ExecutionReport) and report.exec_type == ExecType.CANCELED:
            order.cl_ord_id = cl_ord_id
            self._track(order, report)
        return report

    def cancel_with_ids(self, order: Order, *, order_id: str, orig_cl_ord_id: str) -> OrderCancelReject | ExecutionReport:
        """OrderCancelRequest with explicit identifiers (negative tests: unknown order)."""
        fake = Order(order_id=order_id, cl_ord_id=orig_cl_ord_id, symbol=order.symbol, side=order.side,
                     order_qty=order.order_qty, price=order.price, ord_type=order.ord_type,
                     time_in_force=order.time_in_force, ord_status=order.ord_status)
        cl_ord_id = messages.new_id()
        self._session.send(MsgType.ORDER_CANCEL_REQUEST.value,
                           messages.order_cancel_request(fake, cl_ord_id, messages.transact_time()))
        return self._wait_report(cl_ord_id)

    # --- unsolicited reports ---------------------------------------------------------------------
    def next_report(self, order: Order, exec_type: ExecType | None = None,
                    timeout: float | None = None) -> ExecutionReport:
        """Wait for the next execution report of an order (fills of a resting order, IOC remainder cancel)."""
        def match(msg) -> bool:
            if msg.get(Tag.MSG_TYPE) != MsgType.EXECUTION_REPORT.value.encode():
                return False
            if msg.get(Tag.ORDER_ID) != order.order_id.encode():
                return False
            return exec_type is None or msg.get(Tag.EXEC_TYPE) == exec_type.value.encode()

        report = messages.execution_report(self._session.receive(match, timeout))
        self._track(order, report)
        return report

    def refresh(self, order: Order, wait: float = 0.3) -> None:
        """Apply execution reports that already arrived for the order (e.g. fills nobody waited for)."""
        while True:
            try:
                self.next_report(order, timeout=wait)
            except TimeoutError:
                return

    def active_orders(self) -> list[Order]:
        for order in self.orders:
            if order.ord_status not in TERMINAL_ORD_STATUSES:
                self.refresh(order)
        return [o for o in self.orders if o.ord_status not in TERMINAL_ORD_STATUSES]

    # --- internals -------------------------------------------------------------------------------
    def _wait_report(self, cl_ord_id: str) -> ExecutionReport | OrderCancelReject:
        wanted = cl_ord_id.encode()
        msg = self._session.receive(
            lambda m: m.get(Tag.MSG_TYPE) in (b"8", b"9") and m.get(Tag.CL_ORD_ID) == wanted)
        if messages.msg_type(msg) == MsgType.ORDER_CANCEL_REJECT.value:
            return messages.order_cancel_reject(msg)
        return messages.execution_report(msg)

    @staticmethod
    def _track(order: Order, report: ExecutionReport) -> None:
        order.history.append(report)
        if report.ord_status == OrdStatus.REPLACED:
            return                                    # replaced order stays active
        order.ord_status = report.ord_status
