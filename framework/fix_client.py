import datetime
import socket
import time
import uuid

import simplefix

from framework import config


def utc_ts() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y%m%d-%H:%M:%S.%f")[:-3]


def new_cl_ord_id() -> str:
    return uuid.uuid4().hex[:16]


def readable(msg: simplefix.FixMessage) -> str:
    return msg.encode().replace(b"\x01", b"|").decode()


class FixClient:
    """Minimal FIXT.1.1 / FIX 5.0 SP2 initiator for the QuantReplay order session."""

    def __init__(self, host=config.FIX_HOST, port=config.FIX_PORT,
                 sender=config.FIX_SENDER, target=config.FIX_TARGET,
                 timeout=config.FIX_TIMEOUT, begin_string="FIXT.1.1"):
        self.begin_string = begin_string
        self.host, self.port = host, port
        self.sender, self.target = sender, target
        self.timeout = timeout
        self.seq = 1
        self.sock = None
        self.parser = simplefix.FixParser()
        self.log: list[str] = []

    # --- transport -------------------------------------------------------
    def send(self, msg_type: str, fields: list[tuple]) -> None:
        msg = simplefix.FixMessage()
        msg.append_pair(8, self.begin_string)
        msg.append_pair(35, msg_type)
        msg.append_pair(49, self.sender)
        msg.append_pair(56, self.target)
        msg.append_pair(34, self.seq)
        msg.append_pair(52, utc_ts())
        for tag, value in fields:
            msg.append_pair(tag, value)
        self.seq += 1
        self.log.append(">> " + readable(msg))
        self.sock.sendall(msg.encode())

    def receive(self, predicate, timeout=None) -> simplefix.FixMessage:
        """Read messages until predicate(msg) is true; answers TestRequest on the way."""
        deadline = time.time() + (timeout or self.timeout)
        while time.time() < deadline:
            msg = self.parser.get_message()
            if msg is None:
                try:
                    data = self.sock.recv(4096)
                except socket.timeout:
                    continue
                if not data:
                    raise ConnectionError("FIX connection closed by peer")
                self.parser.append_buffer(data)
                continue
            self.log.append("<< " + readable(msg))
            if msg.get(35) == b"1":
                self.send("0", [(112, msg.get(112).decode())])
                continue
            if predicate(msg):
                return msg
        raise TimeoutError("Expected FIX message not received. Log:\n" + "\n".join(self.log[-10:]))

    # --- session ---------------------------------------------------------
    def logon(self, heartbeat=30) -> simplefix.FixMessage:
        self.sock = socket.create_connection((self.host, self.port), timeout=1)
        fields = [(98, 0), (108, heartbeat), (141, "Y")]
        if self.begin_string == "FIXT.1.1":
            fields.append((1137, 9))  # DefaultApplVerID = FIX 5.0 SP2
        self.send("A", fields)
        return self.receive(lambda m: m.get(35) == b"A")

    def logout(self) -> None:
        try:
            self.send("5", [])
            self.receive(lambda m: m.get(35) == b"5")
        finally:
            self.sock.close()

    # --- orders ----------------------------------------------------------
    def execution_report(self, cl_ord_id: str) -> simplefix.FixMessage:
        return self.receive(lambda m: m.get(35) in (b"8", b"9") and m.get(11) == cl_ord_id.encode())

    def new_order(self, symbol, side, qty, price, ord_type=2, tif=0, cl_ord_id=None):
        cl_ord_id = cl_ord_id or new_cl_ord_id()
        self.send("D", [(11, cl_ord_id), (55, symbol), (54, side), (60, utc_ts()),
                        (40, ord_type), (44, price), (38, qty), (59, tif)])
        return cl_ord_id, self.execution_report(cl_ord_id)

    def replace_order(self, orig_cl_ord_id, order_id, symbol, side, qty, price, ord_type=2):
        cl_ord_id = new_cl_ord_id()
        self.send("G", [(41, orig_cl_ord_id), (11, cl_ord_id), (37, order_id), (55, symbol),
                        (54, side), (60, utc_ts()), (40, ord_type), (44, price), (38, qty)])
        return cl_ord_id, self.execution_report(cl_ord_id)

    def cancel_order(self, orig_cl_ord_id, order_id, symbol, side):
        cl_ord_id = new_cl_ord_id()
        self.send("F", [(41, orig_cl_ord_id), (11, cl_ord_id), (37, order_id),
                        (55, symbol), (54, side), (60, utc_ts())])
        return cl_ord_id, self.execution_report(cl_ord_id)

    # --- market data -----------------------------------------------------
    def market_data_request(self, symbol, md_req_id=None, subscription=0, depth=0,
                            entry_types=("0", "1")):
        md_req_id = md_req_id or new_cl_ord_id()
        fields = [(262, md_req_id), (263, subscription), (264, depth)]
        if subscription == 1:
            fields.append((265, 0))
        fields.append((267, len(entry_types)))
        fields += [(269, t) for t in entry_types]
        fields += [(146, 1), (55, symbol)]
        self.send("V", fields)
        return md_req_id

    def market_data_response(self, md_req_id) -> simplefix.FixMessage:
        return self.receive(lambda m: m.get(35) in (b"W", b"Y") and m.get(262) == md_req_id.encode())
