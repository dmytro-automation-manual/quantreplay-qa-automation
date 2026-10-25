"""FIX session transport: socket, session-level messages (Logon, Logout, Heartbeat, TestRequest), inbox.

Layer rule: knows nothing about orders, market data or the framework models.
It sends (tag, value) pairs and returns raw simplefix messages.
"""
import datetime
import logging
import socket
import time
from collections.abc import Callable, Iterable

import simplefix

SOH = b"\x01"

log = logging.getLogger("fix")


def utc_timestamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y%m%d-%H:%M:%S.%f")[:-3]


def readable(msg: simplefix.FixMessage) -> str:
    return msg.encode().replace(SOH, b"|").decode()


class FixSession:
    """FIXT.1.1 initiator. Messages received while waiting for something else are kept in the inbox,
    so a later receive() can still find them (e.g. a trade report for the resting side of a match)."""

    def __init__(self, host: str, port: int, sender_comp_id: str, target_comp_id: str,
                 timeout: float = 5, heartbeat: int = 30,
                 begin_string: str = "FIXT.1.1", default_appl_ver_id: str = "9"):
        self.host, self.port = host, port
        self.sender_comp_id, self.target_comp_id = sender_comp_id, target_comp_id
        self.timeout = timeout
        self.heartbeat = heartbeat
        self.begin_string = begin_string
        self.default_appl_ver_id = default_appl_ver_id   # 9 = FIX 5.0 SP2
        self._seq = 1
        self._sock: socket.socket | None = None
        self._parser = simplefix.FixParser()
        self._inbox: list[simplefix.FixMessage] = []

    # --- session level ---------------------------------------------------------------------------
    def logon(self) -> simplefix.FixMessage:
        self.close()
        self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self._sock.settimeout(0.2)
        self._seq = 1
        self._parser = simplefix.FixParser()
        self._inbox.clear()
        self.send("A", [(98, 0), (108, self.heartbeat), (141, "Y"), (1137, self.default_appl_ver_id)])
        return self.receive(lambda m: m.get(35) == b"A")

    def logout(self) -> None:
        if self._sock is None:
            return
        try:
            self.send("5", [])
            self.receive(lambda m: m.get(35) == b"5")
        except (OSError, TimeoutError):
            pass                                  # the venue may already have dropped the connection
        finally:
            self.close()

    def close(self) -> None:
        """Drop the TCP connection without a Logout (e.g. the venue is being reset)."""
        if self._sock is not None:
            self._sock.close()
            self._sock = None

    @property
    def connected(self) -> bool:
        return self._sock is not None

    # --- messaging -------------------------------------------------------------------------------
    def send(self, msg_type: str, fields: Iterable[tuple[int, object]]) -> None:
        msg = simplefix.FixMessage()
        msg.append_pair(8, self.begin_string)
        msg.append_pair(35, msg_type)
        msg.append_pair(49, self.sender_comp_id)
        msg.append_pair(56, self.target_comp_id)
        msg.append_pair(34, self._seq)
        msg.append_pair(52, utc_timestamp())
        for tag, value in fields:
            if value is not None:
                msg.append_pair(tag, value)
        self._seq += 1
        log.info(">> %s", readable(msg))
        self._sock.sendall(msg.encode())

    def receive(self, predicate: Callable[[simplefix.FixMessage], bool],
                timeout: float | None = None) -> simplefix.FixMessage:
        """Return the first message (inbox first, then the socket) that matches the predicate."""
        deadline = time.monotonic() + (timeout if timeout is not None else self.timeout)
        while True:
            for i, msg in enumerate(self._inbox):
                if predicate(msg):
                    return self._inbox.pop(i)
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Expected FIX message not received within "
                                   f"{timeout if timeout is not None else self.timeout}s")
            self._read_into_inbox()

    def wait_disconnect(self, timeout: float) -> bool:
        """Wait until the venue closes the connection (e.g. during a venue reset). True if it did."""
        deadline = time.monotonic() + timeout
        try:
            while time.monotonic() < deadline:
                self._read_into_inbox()
        except (ConnectionError, OSError):
            self.close()
            return True
        return False

    def clear_inbox(self) -> None:
        """Drop unread messages, e.g. between tests, so nothing leaks from one test into another."""
        self._read_into_inbox()
        self._inbox.clear()

    def _read_into_inbox(self) -> None:
        msg = self._parser.get_message()
        if msg is None:
            try:
                data = self._sock.recv(65536)
            except (socket.timeout, TimeoutError):
                return
            if not data:
                raise ConnectionError("FIX connection closed by the simulator")
            self._parser.append_buffer(data)
            msg = self._parser.get_message()
        while msg is not None:
            log.info("<< %s", readable(msg))
            if msg.get(35) == b"1":                       # TestRequest -> Heartbeat
                self.send("0", [(112, msg.get(112).decode())])
            elif msg.get(35) != b"0":                     # Heartbeats are not interesting for tests
                self._inbox.append(msg)
            msg = self._parser.get_message()
