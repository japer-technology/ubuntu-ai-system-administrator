from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import family
import tools


class FamilyToolTests(unittest.TestCase):
    def test_agent_plan_only_admits_mutating_target_operations(self) -> None:
        operations = set(
            tools.TOOL_REGISTRY["agent.plan"]["schema"]["properties"]["operation"][
                "enum"
            ]
        )
        self.assertEqual(operations, set(family.MUTATING_OPERATIONS))
        self.assertTrue(
            operations.isdisjoint({"describe", "status", "verify", "doctor"})
        )

    def test_manager_postprocessing_failure_has_correlated_audit_evidence(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = family.FamilyPaths(
                catalog=root / "catalog.json",
                inventory=root / "inventory.json",
                audit=root / "audit.jsonl",
                lock=root / "manager.lock",
                releases=root / "releases",
            )
            manager = family.FamilyManager(
                paths,
                enforce_system_ownership=False,
            )
            response = {
                "correlation_id": "c2d08146-81b0-43ac-b62f-f6c8b94d5692",
                "product_id": "llama",
                "instance_id": None,
                "operation": "update",
                "phase": "execute",
                "status": "ok",
                "changed": True,
                "receipt": None,
            }
            manager._audit_manager_failure(response)
            event = json.loads(paths.audit.read_text(encoding="utf-8"))
            self.assertEqual(event["correlation_id"], response["correlation_id"])
            self.assertEqual(event["result"], "failed")
            self.assertTrue(event["changed"])


if __name__ == "__main__":
    unittest.main()
