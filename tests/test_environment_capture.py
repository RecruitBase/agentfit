"""
Tests for EnvironmentCapture — the sys.audit-based observer that records
actual network/filesystem/process activity independent of anything a tool
or model claims it did.
"""

import os
import socket
import subprocess
import sys
import tempfile

from agentfit.protocol.environment_capture import EnvironmentCapture


class TestEnvironmentCapture:
    def test_captures_filesystem_open(self):
        with EnvironmentCapture() as cap:
            with tempfile.NamedTemporaryFile(delete=False) as f:
                path = f.name
        try:
            events = cap.to_list()
            fs_events = [e for e in events if e["event_type"] == "filesystem"]
            assert any(path in e["detail"].get("path", "") for e in fs_events)
        finally:
            os.remove(path)

    def test_captures_network_connect_attempt(self):
        # Bind a local socket to get a port nothing is listening on, then
        # attempt (and let fail) a connection — the audit event fires
        # before the connect syscall completes, so it's captured either way.
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        _, closed_port = probe.getsockname()
        probe.close()  # nothing listening on this port now

        with EnvironmentCapture() as cap:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            try:
                s.connect(("127.0.0.1", closed_port))
            except OSError:
                pass
            finally:
                s.close()

        events = cap.to_list()
        net_events = [e for e in events if e["event_type"] == "network"]
        assert any(e["detail"].get("port") == closed_port for e in net_events)

    def test_captures_process_spawn(self):
        with EnvironmentCapture() as cap:
            subprocess.run([sys.executable, "-c", "pass"], check=True)

        events = cap.to_list()
        proc_events = [e for e in events if e["event_type"] == "process"]
        assert len(proc_events) >= 1

    def test_events_outside_block_not_captured(self):
        with EnvironmentCapture() as cap:
            pass
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name
        try:
            events = cap.to_list()
            assert not any(path in e["detail"].get("path", "") for e in events)
        finally:
            os.remove(path)

    def test_sequential_captures_do_not_leak(self):
        with EnvironmentCapture() as cap1:
            with tempfile.NamedTemporaryFile(delete=False) as f:
                path1 = f.name
        try:
            with EnvironmentCapture() as cap2:
                with tempfile.NamedTemporaryFile(delete=False) as f:
                    path2 = f.name
            try:
                events1 = cap1.to_list()
                events2 = cap2.to_list()
                assert any(path1 in e["detail"].get("path", "") for e in events1)
                assert not any(path1 in e["detail"].get("path", "") for e in events2)
                assert any(path2 in e["detail"].get("path", "") for e in events2)
                assert not any(path2 in e["detail"].get("path", "") for e in events1)
            finally:
                os.remove(path2)
        finally:
            os.remove(path1)

    def test_nested_captures_both_record(self):
        with EnvironmentCapture() as outer:
            with EnvironmentCapture() as inner:
                with tempfile.NamedTemporaryFile(delete=False) as f:
                    path = f.name
            try:
                outer_events = outer.to_list()
                inner_events = inner.to_list()
                assert any(path in e["detail"].get("path", "") for e in outer_events)
                assert any(path in e["detail"].get("path", "") for e in inner_events)
            finally:
                os.remove(path)
