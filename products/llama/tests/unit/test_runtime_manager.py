from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


SOURCE_ROOT = Path(__file__).resolve().parents[2]
LOADER = importlib.machinery.SourceFileLoader(
    "llama_runtime_manager", str(SOURCE_ROOT / "payload/bin/llama-manager")
)
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC is not None
runtime_manager = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(runtime_manager)


class RuntimeManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.install_root = root / "opt/llama.cpp"
        self.state_root = root / "var/lib/llama.cpp"
        self.runtime = self.install_root / "versions/b10054-amd64"
        self.model = self.state_root / "models/model.gguf"
        self.runtime.mkdir(parents=True)
        self.model.parent.mkdir(parents=True)
        (self.runtime / "llama-server").write_text("#!/bin/sh\n", encoding="utf-8")
        (self.runtime / "llama-server").chmod(0o755)
        self.model.write_bytes(b"model")
        self.config = root / "etc/llama.cpp/config.json"
        self.config.parent.mkdir(parents=True)
        self.config.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "port": 8080,
                    "model_id": "fixture",
                    "model_path": str(self.model),
                    "context_size": 2048,
                    "threads": 2,
                    "runtime_release": "b10054",
                    "runtime_dir": str(self.runtime),
                }
            ),
            encoding="utf-8",
        )
        runtime_manager.CONFIG_PATH = self.config
        runtime_manager.INSTALL_ROOT = self.install_root
        runtime_manager.STATE_ROOT = self.state_root

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_load_config_rejects_non_loopback_port_and_outside_model(self) -> None:
        value = json.loads(self.config.read_text(encoding="utf-8"))
        value["port"] = 8081
        self.config.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            runtime_manager.load_config()
        value["port"] = 8080
        value["model_path"] = "/tmp/unmanaged.gguf"
        self.config.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            runtime_manager.load_config()

    def test_status_reports_stopped_service(self) -> None:
        original_property = runtime_manager.service_property
        original_systemctl = runtime_manager.systemctl
        runtime_manager.service_property = lambda _name: "inactive"
        runtime_manager.systemctl = lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0, stdout="enabled\n", stderr=""
        )
        try:
            status = runtime_manager.status_payload()
        finally:
            runtime_manager.service_property = original_property
            runtime_manager.systemctl = original_systemctl
        self.assertEqual(status["state"], "installed-stopped")
        self.assertFalse(status["healthy"])

    def test_serve_forces_loopback_and_declared_model(self) -> None:
        captured: dict[str, object] = {}
        original_execv = runtime_manager.os.execv
        original_library_path = os.environ.get("LD_LIBRARY_PATH")

        def fake_execv(path: Path, arguments: list[str]) -> None:
            captured["path"] = path
            captured["arguments"] = arguments
            captured["library_path"] = os.environ["LD_LIBRARY_PATH"]
            raise StopIteration

        runtime_manager.os.execv = fake_execv
        os.environ.pop("LD_LIBRARY_PATH", None)
        try:
            with self.assertRaises(StopIteration):
                runtime_manager.serve()
        finally:
            runtime_manager.os.execv = original_execv
            if original_library_path is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = original_library_path
        self.assertEqual(captured["path"], self.runtime / "llama-server")
        arguments = captured["arguments"]
        assert isinstance(arguments, list)
        self.assertEqual(arguments[arguments.index("--host") + 1], "127.0.0.1")
        self.assertEqual(arguments[arguments.index("--port") + 1], "8080")
        self.assertEqual(arguments[arguments.index("--model") + 1], str(self.model))
        self.assertEqual(captured["library_path"], str(self.runtime))


if __name__ == "__main__":
    unittest.main()
