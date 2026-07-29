"""
Environment Capture.

Records what a block of code actually did at the OS level — network
connections opened, filesystem paths touched, processes spawned — using
CPython's `sys.audit` hooks. This is independent of anything a tool
implementation or model *claims* it did: it observes the interpreter
directly, so out-of-band behaviour (a tool reaching a host it wasn't
supposed to, touching a file outside its declared scope, spawning a
subprocess) shows up here even if the declared ToolResult looks clean.

Scope: this only sees activity inside the current Python process. It does
not see activity inside a genuinely separate sandboxed container/VM that a
real tool implementation might shell out to — that would need OS-level
tracing outside the interpreter.
"""

from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


_NETWORK_EVENTS = {"socket.connect", "socket.connect_ex", "urllib.Request"}
_FILESYSTEM_EVENTS = {
    "open",
    "os.remove",
    "os.rename",
    "os.mkdir",
    "os.rmdir",
    "shutil.copyfile",
    "shutil.move",
}
_PROCESS_PREFIXES = ("os.exec", "os.spawn", "os.posix_spawn")
_PROCESS_EVENTS = {"subprocess.Popen", "os.system", "os.fork"}


def _classify(event: str) -> Optional[str]:
    if event in _NETWORK_EVENTS:
        return "network"
    if event in _FILESYSTEM_EVENTS:
        return "filesystem"
    if event in _PROCESS_EVENTS or event.startswith(_PROCESS_PREFIXES):
        return "process"
    return None


def _describe(event: str, args: tuple) -> Dict[str, Any]:
    """Best-effort structured extraction of the interesting bits of an audit event's args."""
    try:
        if event in ("socket.connect", "socket.connect_ex") and len(args) >= 2:
            address = args[1]
            if isinstance(address, tuple) and len(address) >= 2:
                return {"host": address[0], "port": address[1]}
            return {"address": str(address)}
        if event == "urllib.Request" and args:
            return {"url": str(args[0])}
        if event == "open" and args:
            return {"path": str(args[0]), "mode": str(args[1]) if len(args) > 1 else ""}
        if event in ("os.remove", "os.rename", "os.mkdir", "os.rmdir") and args:
            return {"path": str(args[0])}
        if event in ("shutil.copyfile", "shutil.move") and len(args) >= 2:
            return {"src": str(args[0]), "dst": str(args[1])}
        if event == "subprocess.Popen" and args:
            return {"cmd": str(args[0])}
        if event == "os.system" and args:
            return {"cmd": str(args[0])}
        return {"raw_args": str(args)[:500]}
    except Exception:
        return {"raw_args": "<unrepresentable>"}


@dataclass
class EnvironmentEvent:
    """One observed OS-level side effect."""

    event_type: str  # "network" | "filesystem" | "process"
    audit_event: str  # raw sys.audit event name, e.g. "socket.connect"
    detail: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "audit_event": self.audit_event,
            "detail": self.detail,
            "timestamp": self.timestamp,
        }


_local = threading.local()
_hook_installed = False
_install_lock = threading.Lock()


def _active_stack() -> List["EnvironmentCapture"]:
    stack = getattr(_local, "stack", None)
    if stack is None:
        stack = []
        _local.stack = stack
    return stack


def _global_audit_hook(event: str, args: tuple) -> None:
    kind = _classify(event)
    if kind is None:
        return
    stack = getattr(_local, "stack", None)
    if not stack:
        return
    record = EnvironmentEvent(event_type=kind, audit_event=event, detail=_describe(event, args))
    for capture in stack:
        capture.events.append(record)


def _ensure_hook_installed() -> None:
    global _hook_installed
    if _hook_installed:
        return
    with _install_lock:
        if not _hook_installed:
            sys.addaudithook(_global_audit_hook)
            _hook_installed = True


class EnvironmentCapture:
    """
    Context manager that records real network/filesystem/process activity
    triggered on the current thread while the block runs.

        with EnvironmentCapture() as cap:
            _execute_tool(tc, tools)
        tool_result.environment_events = cap.to_list()

    Audit hooks cannot be removed once installed, so this installs exactly
    one process-wide dispatcher (guarded, idempotent) and routes it through
    a thread-local stack of active captures — inactive captures cost a
    single list-emptiness check per audited event.
    """

    def __init__(self) -> None:
        self.events: List[EnvironmentEvent] = []

    def __enter__(self) -> "EnvironmentCapture":
        _ensure_hook_installed()
        _active_stack().append(self)
        return self

    def __exit__(self, *exc_info: Any) -> bool:
        stack = _active_stack()
        if stack and stack[-1] is self:
            stack.pop()
        return False

    def to_list(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self.events]
