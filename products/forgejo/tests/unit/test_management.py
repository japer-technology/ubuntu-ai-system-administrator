from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import tarfile
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

from forgejo.management import (
    ADOPT_CONFIRMATION,
    Configuration,
    Invocation,
    ManagementError,
    Manager,
    Paths,
    parser,
)


SOURCE_ROOT = Path(__file__).resolve().parents[2]


class ManagementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.paths = Paths(
            install_root=root / "opt/forgejo",
            configuration_root=root / "etc/forgejo",
            state_root=root / "var/lib/forgejo",
            log_root=root / "var/log/forgejo",
            cache_root=root / "var/cache/forgejo",
            unit=root / "etc/systemd/system/forgejo.service",
            logrotate=root / "etc/logrotate.d/forgejo-product",
            entrypoint=root / "usr/local/sbin/forgejo-manage",
            binary=root / "usr/local/bin/forgejo",
            lock=root / "run/lock/forgejo.lock",
            backup_root=root / "var/backups/forgejo",
            caddyfile=root / "etc/caddy/Caddyfile",
            legacy_caddy=root / "etc/caddy/conf.d/forgejo.caddy",
            avahi_service=root / "etc/avahi/services/forgejo.service",
            caddy_ca=root / "var/lib/caddy/root.crt",
            trusted_ca=root
            / "usr/local/share/ca-certificates/forgejo-local-ca.crt",
            migration_manifest=root / "var/lib/migration-source/components/forgejo",
        )
        self.manager = Manager(SOURCE_ROOT)
        self.manager.paths = self.paths

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def invocation(
        operation: str = "install",
        *,
        inputs: dict[str, object] | None = None,
        dry_run: bool = False,
        confirmation: str | None = None,
    ) -> Invocation:
        return Invocation(
            operation=operation,
            correlation_id=str(uuid.uuid4()),
            actor="operator",
            inputs=inputs or {},
            confirmation=confirmation,
            retain_state=True if operation == "uninstall" else None,
            dry_run=dry_run,
            json_output=True,
            non_interactive=True,
            assume_yes=True,
            supplied_plan_digest=None,
        )

    def test_descriptor_preserves_existing_namespaces(self) -> None:
        descriptor = self.manager.descriptor
        self.assertEqual(descriptor["install_root"], "/opt/forgejo")
        self.assertEqual(descriptor["state_root"], "/var/lib/forgejo")
        self.assertEqual(descriptor["accounts"][0], {"name": "git", "kind": "user"})
        self.assertEqual(
            descriptor["ports"][0],
            {"address": "127.0.0.1", "port": 3000, "protocol": "tcp"},
        )

    def test_default_configuration_is_loopback_and_https(self) -> None:
        with mock.patch.object(self.manager, "_host", return_value="forge.local"):
            configuration = self.manager.configuration(self.invocation())
        self.assertEqual(configuration.host, "forge.local")
        self.assertEqual(configuration.root_url, "https://forge.local/")
        self.assertEqual(configuration.database_name, "forgejo")
        self.assertEqual(configuration.upstream_version, "latest")
        self.assertNotIn("password", json.dumps(configuration.public_object()))

    def test_existing_public_host_is_preserved(self) -> None:
        self.paths.configuration_root.mkdir(parents=True)
        self.paths.app_ini.write_text(
            """[database]
NAME = forgejo
USER = forgejo
[server]
DOMAIN = existing.local
ROOT_URL = https://existing.local/
""",
            encoding="utf-8",
        )
        configuration = self.manager.configuration(self.invocation())
        self.assertEqual(configuration.host, "existing.local")

    def test_fixed_port_cannot_be_overridden(self) -> None:
        with mock.patch.dict(os.environ, {"FORGEJO_HTTP_PORT": "3001"}):
            with self.assertRaises(ManagementError) as raised:
                self.manager.configuration(self.invocation())
        self.assertEqual(raised.exception.code, "INVALID_CONFIGURATION")

    def test_interactive_install_collects_validated_configuration(self) -> None:
        arguments = parser().parse_args(["install"])
        inputs: dict[str, object] = {}
        answers = [
            "INVALID",
            "owner",
            "owner@example.test",
            "forge",
            "forge_role",
            "11.0.3",
            "no",
        ]
        with (
            mock.patch(
                "forgejo.management.sys.stdin.isatty",
                return_value=True,
            ),
            mock.patch.object(
                self.manager,
                "_prompt",
                side_effect=answers,
            ),
        ):
            self.manager._prepare_interactive_install(
                arguments,
                inputs,
                request_supplied=False,
                non_interactive=False,
            )
        self.assertEqual(
            inputs,
            {
                "admin_user": "owner",
                "admin_email": "owner@example.test",
                "database_name": "forge",
                "database_user": "forge_role",
                "upstream_version": "11.0.3",
                "boot": "disabled",
            },
        )

    def test_approved_install_skips_setup_questions(self) -> None:
        arguments = parser().parse_args(["install", "--yes"])
        with mock.patch.object(self.manager, "_prompt") as prompt:
            self.manager._prepare_interactive_install(
                arguments,
                {},
                request_supplied=False,
                non_interactive=False,
            )
        prompt.assert_not_called()

    def test_dry_run_is_non_mutating_and_stable(self) -> None:
        invocation = self.invocation(dry_run=True)
        with mock.patch.object(self.manager, "_host", return_value="forge.local"):
            result, exit_code = self.manager.run(invocation)
            repeated, repeated_exit = self.manager.run(invocation)
        self.assertEqual((exit_code, repeated_exit), (0, 0))
        self.assertEqual(result.plan_digest, repeated.plan_digest)
        self.assertFalse(result.changed)
        self.assertFalse(self.paths.lock.exists())
        self.assertFalse(self.paths.install_root.exists())

    def test_interactive_approval_displays_configuration_and_plan(self) -> None:
        invocation = self.invocation(
            inputs={
                "admin_user": "owner",
                "admin_email": "owner@example.test",
                "database_name": "forge",
                "database_user": "forge_role",
                "upstream_version": "11.0.3",
                "boot": "disabled",
            }
        )
        invocation.non_interactive = False
        invocation.assume_yes = False
        invocation.json_output = False
        output = io.StringIO()
        with (
            mock.patch.object(self.manager, "_host", return_value="forge.local"),
            mock.patch.object(self.manager, "_prompt", return_value="no"),
            mock.patch("sys.stdout", output),
        ):
            with self.assertRaises(ManagementError) as raised:
                self.manager.run(invocation)
        self.assertEqual(raised.exception.code, "CONFIRMATION_REQUIRED")
        self.assertIn("Public URL:", output.getvalue())
        self.assertIn("https://forge.local/", output.getvalue())
        self.assertIn("Administrator:", output.getvalue())
        self.assertIn("owner (owner@example.test)", output.getvalue())
        self.assertIn("Preserve secrets and deploy", output.getvalue())
        self.assertFalse(self.paths.lock.exists())

    def test_caddy_render_replaces_only_managed_legacy_block(self) -> None:
        self.paths.caddyfile.parent.mkdir(parents=True)
        self.paths.caddyfile.write_text(
            """unrelated.local {
  respond "ok"
}
# BEGIN install.sh Forgejo
https://old.local {
  tls internal
  reverse_proxy 127.0.0.1:3000
}
# END install.sh Forgejo
""",
            encoding="utf-8",
        )
        rendered = self.manager._render_caddyfile("new.local").decode()
        self.assertIn('unrelated.local {\n  respond "ok"\n}', rendered)
        self.assertIn("https://new.local {", rendered)
        self.assertNotIn("old.local", rendered)
        self.assertEqual(rendered.count("# BEGIN forgejo-manage Forgejo"), 1)

    def test_incomplete_caddy_ownership_is_rejected(self) -> None:
        with self.assertRaises(ManagementError) as raised:
            self.manager._without_managed_caddy_blocks(
                "# BEGIN install.sh Forgejo\nhttps://forge.local {\n"
            )
        self.assertEqual(raised.exception.code, "CADDY_OWNERSHIP_AMBIGUOUS")

    def test_overlapping_caddy_ownership_is_rejected(self) -> None:
        content = """# BEGIN forgejo-manage Forgejo
# BEGIN install.sh Forgejo
# END forgejo-manage Forgejo
# END install.sh Forgejo
"""
        with self.assertRaises(ManagementError) as raised:
            self.manager._without_managed_caddy_blocks(content)
        self.assertEqual(raised.exception.code, "CADDY_OWNERSHIP_AMBIGUOUS")

    def test_runner_boundary_requires_resolution_ca_and_restrictions(self) -> None:
        self.paths.configuration_root.mkdir(parents=True)
        self.paths.app_ini.write_text(
            """[database]
NAME = forgejo
USER = forgejo
[server]
DOMAIN = forge.local
ROOT_URL = https://forge.local/
""",
            encoding="utf-8",
        )
        runner = Path(self.temporary.name) / "runner.yaml"
        runner.write_text(
            """runner:
  envs:
    SSL_CERT_FILE: /etc/ssl/certs/ca-certificates.crt
    NODE_EXTRA_CA_CERTS: /etc/ssl/certs/ca-certificates.crt
container:
  network: host
  privileged: false
  options: "--add-host forge.local:127.0.0.1 --volume /etc/ssl/certs/ca-certificates.crt:/etc/ssl/certs/ca-certificates.crt:ro"
  valid_volumes: []
  docker_host: "-"
""",
            encoding="utf-8",
        )
        with mock.patch("forgejo.management.Path") as path_type:
            path_type.return_value = runner
            self.assertTrue(self.manager._runner_same_host_config_valid())
        runner.write_text("container:\n  network: host\n", encoding="utf-8")
        with mock.patch("forgejo.management.Path") as path_type:
            path_type.return_value = runner
            self.assertFalse(self.manager._runner_same_host_config_valid())

    def test_adoption_requires_exact_confirmation(self) -> None:
        with (
            mock.patch.object(
                self.manager, "_legacy_installation_valid", return_value=True
            ),
            mock.patch.object(self.manager, "load_marker", return_value=None),
            mock.patch.object(self.manager, "_transaction_instance", return_value=None),
        ):
            with self.assertRaises(ManagementError) as raised:
                self.manager._collision_preflight(self.invocation())
            self.assertEqual(
                raised.exception.code, "ADOPTION_CONFIRMATION_REQUIRED"
            )
            marker, instance_id, adopting = self.manager._collision_preflight(
                self.invocation(confirmation=ADOPT_CONFIRMATION)
            )
        self.assertIsNone(marker)
        self.assertTrue(adopting)
        uuid.UUID(instance_id)

    def test_migration_manifest_accepts_one_generic_version_field(self) -> None:
        manifest = self.paths.migration_manifest
        self.assertIsNotNone(manifest)
        assert manifest is not None
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            "\n".join(
                (
                    "format=1",
                    "component=forgejo",
                    "source_version=2026.08.11.00.00.00",
                    "converged_utc=2026-08-11T00:00:00Z",
                    "component_version=1.2.3",
                    "suboptions=",
                )
            )
            + "\n",
            encoding="utf-8",
        )
        manifest.chmod(0o644)
        real_lstat = Path.lstat

        def root_owned_lstat(path: Path) -> os.stat_result:
            metadata = real_lstat(path)
            if path != manifest:
                return metadata
            return os.stat_result(
                (
                    metadata.st_mode,
                    metadata.st_ino,
                    metadata.st_dev,
                    metadata.st_nlink,
                    0,
                    0,
                    metadata.st_size,
                    metadata.st_atime,
                    metadata.st_mtime,
                    metadata.st_ctime,
                )
            )

        with mock.patch.object(
            Path,
            "lstat",
            autospec=True,
            side_effect=root_owned_lstat,
        ):
            self.assertTrue(self.manager._legacy_manifest_valid())

    def test_archive_member_rejects_traversal_and_links(self) -> None:
        traversal = tarfile.TarInfo("forgejo-backup/../../escape")
        link = tarfile.TarInfo("forgejo-backup/link")
        link.type = tarfile.SYMTYPE
        link.linkname = "../../escape"
        safe = tarfile.TarInfo("forgejo-backup/database.dump")
        self.assertFalse(self.manager._safe_archive_member(traversal))
        self.assertFalse(self.manager._safe_archive_member(link))
        self.assertTrue(self.manager._safe_archive_member(safe))

    def test_backup_destination_rejects_product_state(self) -> None:
        invocation = self.invocation(
            "backup",
            inputs={
                "backup_destination": str(self.paths.state_root / "backup")
            },
        )
        with self.assertRaises(ManagementError) as raised:
            self.manager._backup_destination(invocation)
        self.assertEqual(
            raised.exception.code, "INVALID_BACKUP_DESTINATION"
        )

    def test_marker_writer_matches_shared_contract(self) -> None:
        self.paths.state_root.mkdir(parents=True)
        instance_id = str(uuid.uuid4())
        artifact = "a" * 64
        changed: list[str] = []
        with (
            mock.patch.dict(
                os.environ,
                {"FORGEJO_ARTIFACT_SHA256": artifact},
                clear=False,
            ),
            mock.patch.object(
                self.manager,
                "_source_revision",
                side_effect=AssertionError("artifact installs use their digest"),
            ),
            mock.patch("forgejo.management.os.fchown"),
        ):
            self.manager._write_marker(
                instance_id,
                existing=None,
                changed=changed,
            )
        marker = json.loads(self.paths.marker.read_text(encoding="utf-8"))
        self.assertEqual(
            set(marker),
            {
                "schema_version",
                "product_id",
                "instance_id",
                "version",
                "source_revision",
                "installed_at",
                "install_root",
                "lifecycle_entrypoint",
                "artifact_sha256",
            },
        )
        self.assertEqual(marker["instance_id"], instance_id)
        self.assertEqual(marker["install_root"], str(self.paths.install_root))
        self.assertEqual(
            marker["lifecycle_entrypoint"],
            str(self.paths.entrypoint),
        )
        self.assertEqual(marker["artifact_sha256"], artifact)
        self.assertEqual(marker["source_revision"], f"artifact-sha256:{artifact}")
        self.assertEqual(changed, [str(self.paths.marker)])

    def test_marker_writer_rejects_invalid_artifact_digest(self) -> None:
        self.paths.state_root.mkdir(parents=True)
        with mock.patch.dict(
            os.environ,
            {"FORGEJO_ARTIFACT_SHA256": "not-a-digest"},
            clear=False,
        ):
            with self.assertRaises(ManagementError) as raised:
                self.manager._write_marker(
                    str(uuid.uuid4()),
                    existing=None,
                    changed=[],
                )
        self.assertEqual(raised.exception.code, "INVALID_ARTIFACT_DIGEST")
        self.assertFalse(self.paths.marker.exists())

    def test_previous_release_marker_is_loaded_and_migrated(self) -> None:
        self.paths.state_root.mkdir(parents=True)
        instance_id = str(uuid.uuid4())
        previous = {
            "schema_version": 1,
            "product_id": "forgejo",
            "instance_id": instance_id,
            "version": self.manager.version,
            "source_revision": "source-tree-sha256:" + "a" * 64,
            "installed_at": "2026-08-10T00:00:00Z",
            "updated_at": "2026-08-10T00:01:00Z",
        }
        self.paths.marker.write_text(
            json.dumps(previous),
            encoding="utf-8",
        )
        self.paths.marker.chmod(0o644)
        real_lstat = Path.lstat

        def root_owned_lstat(path: Path) -> os.stat_result:
            metadata = real_lstat(path)
            if path != self.paths.marker:
                return metadata
            return os.stat_result(
                (
                    metadata.st_mode,
                    metadata.st_ino,
                    metadata.st_dev,
                    metadata.st_nlink,
                    0,
                    0,
                    metadata.st_size,
                    metadata.st_atime,
                    metadata.st_mtime,
                    metadata.st_ctime,
                )
            )

        with (
            mock.patch.object(
                Path,
                "lstat",
                autospec=True,
                side_effect=root_owned_lstat,
            ),
            mock.patch("forgejo.management.os.fchown"),
        ):
            normalized = self.manager.load_marker(required=True)
            migrated = self.manager._migrate_previous_marker()
        self.assertIsNotNone(normalized)
        self.assertEqual(normalized["instance_id"], instance_id)
        self.assertNotIn("updated_at", normalized)
        self.assertEqual(
            normalized["install_root"],
            str(self.paths.install_root),
        )
        self.assertIsNone(normalized["artifact_sha256"])
        self.assertTrue(migrated)
        self.assertEqual(
            set(json.loads(self.paths.marker.read_text(encoding="utf-8"))),
            {
                "schema_version",
                "product_id",
                "instance_id",
                "version",
                "source_revision",
                "installed_at",
                "install_root",
                "lifecycle_entrypoint",
                "artifact_sha256",
            },
        )

    def test_installed_entrypoint_preserves_artifact_provenance(self) -> None:
        self.paths.state_root.mkdir(parents=True)
        artifact = "b" * 64
        existing = {
            "schema_version": 1,
            "product_id": "forgejo",
            "instance_id": str(uuid.uuid4()),
            "version": self.manager.version,
            "source_revision": f"artifact-sha256:{artifact}",
            "installed_at": "2026-08-10T00:00:00Z",
            "install_root": str(self.paths.install_root),
            "lifecycle_entrypoint": str(self.paths.entrypoint),
            "artifact_sha256": artifact,
        }
        self.manager.source_root = self.paths.product_root.resolve(strict=False)
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch.object(
                self.manager,
                "_source_revision",
                side_effect=AssertionError(
                    "installed artifact provenance must be preserved"
                ),
            ),
            mock.patch("forgejo.management.os.fchown"),
        ):
            self.manager._write_marker(
                existing["instance_id"],
                existing=existing,
                changed=[],
            )
        marker = json.loads(self.paths.marker.read_text(encoding="utf-8"))
        self.assertEqual(marker["artifact_sha256"], artifact)
        self.assertEqual(
            marker["source_revision"],
            f"artifact-sha256:{artifact}",
        )

    def test_backup_streams_postgres_dump_without_path_access(self) -> None:
        self.paths.configuration_root.mkdir(parents=True)
        self.paths.state_root.mkdir(parents=True)
        self.paths.app_ini.write_text(
            """[database]
NAME = forgejo
USER = forgejo
""",
            encoding="utf-8",
        )
        streamed: list[bytes] = []

        def run_as(
            _user: str,
            command: list[str],
            **kwargs: object,
        ) -> subprocess.CompletedProcess[str]:
            if command[0] == "pg_dump":
                self.assertNotIn("--file", command)
                output = kwargs["stdout"]
                self.assertTrue(hasattr(output, "write"))
                getattr(output, "write")(b"fixture-database")
                streamed.append(b"fixture-database")
            return subprocess.CompletedProcess(command, 0, "", "")

        marker = {
            "version": self.manager.version,
            "instance_id": str(uuid.uuid4()),
        }
        with (
            mock.patch.object(
                self.manager,
                "load_marker",
                return_value=marker,
            ),
            mock.patch.object(
                self.manager,
                "_run_as",
                side_effect=run_as,
            ),
            mock.patch.object(
                self.manager,
                "_binary_record",
                return_value=None,
            ),
            mock.patch.object(
                self.manager,
                "_service_enabled",
                return_value="disabled",
            ),
            mock.patch("forgejo.management.os.chown"),
            mock.patch("forgejo.management.os.fchown"),
        ):
            archive = self.manager._create_backup("unit")
        self.assertEqual(streamed, [b"fixture-database"])
        self.assertTrue(archive.is_file())
        self.assertTrue(
            archive.with_suffix(archive.suffix + ".sha256").is_file()
        )

    def test_restore_database_streams_dump_to_postgres(self) -> None:
        extracted = Path(self.temporary.name) / "restore"
        extracted.mkdir()
        (extracted / "database.dump").write_bytes(b"fixture-database")
        configuration = extracted / "app.ini"
        configuration.write_text(
            """[database]
NAME = forgejo
USER = forgejo
PASSWD = valid-database-password
""",
            encoding="utf-8",
        )
        restored: list[bytes] = []

        def run_as(
            _user: str,
            command: list[str],
            **kwargs: object,
        ) -> subprocess.CompletedProcess[str]:
            if command[0] == "pg_restore":
                self.assertNotIn(str(extracted / "database.dump"), command)
                source = kwargs["stdin"]
                self.assertTrue(hasattr(source, "read"))
                restored.append(getattr(source, "read")())
            return subprocess.CompletedProcess(command, 0, "", "")

        with mock.patch.object(
            self.manager,
            "_run_as",
            side_effect=run_as,
        ):
            self.manager._restore_database(extracted, configuration)
        self.assertEqual(restored, [b"fixture-database"])

    def test_coordinated_backup_restores_complete_service_path(self) -> None:
        archive = self.paths.backup_root / "backup.tar.gz"
        with (
            mock.patch.object(
                self.manager,
                "_service_active",
                return_value=True,
            ),
            mock.patch.object(
                self.manager,
                "_stop_services",
                return_value=True,
            ),
            mock.patch.object(
                self.manager,
                "_create_backup",
                return_value=archive,
            ),
            mock.patch.object(self.manager, "_run") as run,
            mock.patch.object(self.manager, "_wait_healthy") as wait_loopback,
            mock.patch.object(
                self.manager,
                "_wait_https_healthy",
            ) as wait_https,
            mock.patch.object(
                self.manager,
                "_restore_runner",
            ) as restore_runner,
        ):
            result = self.manager._coordinated_backup("unit")
        self.assertEqual(result, archive)
        run.assert_called_once_with(
            ["systemctl", "start", "forgejo.service"]
        )
        wait_loopback.assert_called_once_with()
        wait_https.assert_called_once_with()
        restore_runner.assert_called_once_with(True)

    def test_backup_error_is_not_masked_by_restore_error(self) -> None:
        backup_error = ManagementError(
            1,
            "BACKUP_FAILED",
            "The database dump failed.",
        )
        restore_error = ManagementError(
            1,
            "SERVICE_START_FAILED",
            "Forgejo did not restart.",
        )
        with (
            mock.patch.object(
                self.manager,
                "_service_active",
                return_value=True,
            ),
            mock.patch.object(
                self.manager,
                "_stop_services",
                return_value=False,
            ),
            mock.patch.object(
                self.manager,
                "_create_backup",
                side_effect=backup_error,
            ),
            mock.patch.object(
                self.manager,
                "_run",
                side_effect=restore_error,
            ),
        ):
            with self.assertRaises(ManagementError) as raised:
                self.manager._coordinated_backup("unit")
        self.assertIs(raised.exception, backup_error)
        self.assertIs(raised.exception.__cause__, restore_error)
        self.assertIn("restoration also failed", backup_error.recovery[0])

    def test_completed_backup_path_survives_restore_failure(self) -> None:
        archive = self.paths.backup_root / "completed.tar.gz"
        restore_error = ManagementError(
            1,
            "SERVICE_START_FAILED",
            "Forgejo did not restart.",
        )
        with (
            mock.patch.object(
                self.manager,
                "_service_active",
                return_value=True,
            ),
            mock.patch.object(
                self.manager,
                "_stop_services",
                return_value=False,
            ),
            mock.patch.object(
                self.manager,
                "_create_backup",
                return_value=archive,
            ),
            mock.patch.object(
                self.manager,
                "_run",
                side_effect=restore_error,
            ),
        ):
            with self.assertRaises(ManagementError) as raised:
                self.manager._coordinated_backup("unit")
        self.assertEqual(raised.exception.code, "BACKUP_RESTORE_FAILED")
        self.assertIn(str(archive), raised.exception.message)
        self.assertIn(str(archive), raised.exception.recovery[0])
        self.assertIs(raised.exception.__cause__, restore_error)

    def test_runner_restart_requires_https_health(self) -> None:
        with (
            mock.patch.object(self.manager, "_health", return_value=True),
            mock.patch.object(
                self.manager,
                "_https_health",
                return_value=False,
            ),
            mock.patch.object(self.manager, "_run") as run,
        ):
            with self.assertRaises(ManagementError) as raised:
                self.manager._restore_runner(True)
        self.assertEqual(
            raised.exception.code,
            "RUNNER_DEPENDENCY_UNHEALTHY",
        )
        run.assert_not_called()

    def test_failed_mutation_does_not_restart_runner_without_https(self) -> None:
        self.paths.unit.parent.mkdir(parents=True)
        self.paths.unit.write_text("[Service]\n", encoding="utf-8")
        with (
            mock.patch.object(self.manager, "_run") as run,
            mock.patch.object(self.manager, "_health", return_value=True),
            mock.patch.object(
                self.manager,
                "_https_health",
                return_value=False,
            ),
        ):
            self.manager._restore_after_failed_mutation(
                server_was_active=True,
                runner_was_active=True,
                was_suspended=False,
            )
        run.assert_called_once_with(
            ["systemctl", "start", "forgejo.service"],
            check=False,
        )

    def test_failed_suspended_mutation_reasserts_suspension(self) -> None:
        with mock.patch.object(
            self.manager,
            "_enforce_suspension",
        ) as enforce:
            self.manager._restore_after_failed_mutation(
                server_was_active=True,
                runner_was_active=True,
                was_suspended=True,
            )
        enforce.assert_called_once_with()

    def test_enforce_suspension_disables_server_and_runner(self) -> None:
        with (
            mock.patch.object(self.manager, "_stop_services") as stop,
            mock.patch.object(
                self.manager,
                "_runner_present",
                return_value=True,
            ),
            mock.patch.object(self.manager, "_run") as run,
        ):
            self.manager._enforce_suspension()
        stop.assert_called_once_with()
        self.assertEqual(
            run.call_args_list,
            [
                mock.call(
                    ["systemctl", "disable", "forgejo.service"],
                    check=False,
                ),
                mock.call(
                    ["systemctl", "disable", "forgejo-runner.service"],
                    check=False,
                ),
            ],
        )

    def test_suspend_records_and_disables_runner_boot_intent(self) -> None:
        self.paths.state_root.mkdir(parents=True)
        marker = {"version": self.manager.version}

        def write_file(
            path: Path,
            content: bytes,
            **_kwargs: object,
        ) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

        with (
            mock.patch.object(
                self.manager,
                "load_marker",
                return_value=marker,
            ),
            mock.patch.object(
                self.manager,
                "_service_active",
                return_value=True,
            ),
            mock.patch.object(
                self.manager,
                "_runner_active",
                return_value=True,
            ),
            mock.patch.object(
                self.manager,
                "_runner_present",
                return_value=True,
            ),
            mock.patch.object(
                self.manager,
                "_service_enabled",
                return_value="enabled",
            ),
            mock.patch.object(
                self.manager,
                "_service_enabled_named",
                return_value="enabled",
            ),
            mock.patch.object(
                self.manager,
                "_stop_services",
                return_value=True,
            ),
            mock.patch.object(self.manager, "_run") as run,
            mock.patch(
                "forgejo.management.atomic_write",
                side_effect=write_file,
            ),
        ):
            self.manager._execute_suspend()
        suspension = json.loads(
            self.paths.suspended.read_text(encoding="utf-8")
        )
        self.assertTrue(suspension["server_was_active"])
        self.assertTrue(suspension["runner_was_active"])
        self.assertEqual(suspension["boot"], "enabled")
        self.assertEqual(suspension["runner_boot"], "enabled")
        self.assertIn(
            mock.call(
                ["systemctl", "disable", "forgejo-runner.service"],
                check=False,
            ),
            run.call_args_list,
        )

    def test_resume_checks_boundaries_and_https_before_runner(self) -> None:
        self.paths.state_root.mkdir(parents=True)
        self.paths.suspended.write_text("{}\n", encoding="utf-8")
        marker = {"version": self.manager.version}
        suspension = {
            "schema_version": 1,
            "product_id": "forgejo",
            "suspended_at": "2026-08-10T00:00:00Z",
            "server_was_active": True,
            "runner_was_active": True,
            "boot": "enabled",
            "runner_boot": "enabled",
        }
        with (
            mock.patch.object(
                self.manager,
                "load_marker",
                return_value=marker,
            ),
            mock.patch.object(
                self.manager,
                "_load_suspension",
                return_value=suspension,
            ),
            mock.patch.object(
                self.manager,
                "verify_checks",
                return_value=[],
            ) as verify,
            mock.patch.object(
                self.manager,
                "_runner_present",
                return_value=True,
            ),
            mock.patch.object(self.manager, "_run") as run,
            mock.patch.object(self.manager, "_wait_healthy") as wait_loopback,
            mock.patch.object(
                self.manager,
                "_wait_https_healthy",
            ) as wait_https,
            mock.patch.object(
                self.manager,
                "_restore_runner",
            ) as restore_runner,
        ):
            self.manager._execute_resume()
        verify.assert_called_once_with(probe=False)
        self.assertIn(
            mock.call(
                ["systemctl", "enable", "forgejo-runner.service"],
                check=True,
            ),
            run.call_args_list,
        )
        wait_loopback.assert_called_once_with()
        wait_https.assert_called_once_with()
        restore_runner.assert_called_once_with(True)
        self.assertFalse(self.paths.suspended.exists())

    def test_uninstall_adopts_legacy_state_before_retaining_it(self) -> None:
        invocation = self.invocation("uninstall")
        marker = {"version": self.manager.version}
        with (
            mock.patch.object(
                self.manager,
                "load_marker",
                side_effect=[None, marker],
            ),
            mock.patch.object(
                self.manager,
                "_legacy_installation_valid",
                return_value=True,
            ),
            mock.patch.object(
                self.manager,
                "_runner_present",
                return_value=False,
            ),
            mock.patch.object(self.manager, "_write_marker") as write_marker,
            mock.patch.object(self.manager, "_ensure_directory"),
            mock.patch.object(self.manager, "_ensure_log_ownership"),
            mock.patch.object(
                self.manager,
                "_stop_services",
                return_value=False,
            ),
            mock.patch.object(self.manager, "_run"),
            mock.patch.object(self.manager, "_remove_caddy_route"),
            mock.patch.object(
                self.manager,
                "_service_active_named",
                return_value=False,
            ),
            mock.patch("forgejo.management.atomic_write"),
        ):
            self.manager._execute_uninstall(invocation)
        write_marker.assert_called_once()

    def test_purge_requires_database_configuration(self) -> None:
        with self.assertRaises(ManagementError) as raised:
            self.manager._drop_database()
        self.assertEqual(
            raised.exception.code,
            "UNSAFE_DATABASE_REMOVAL",
        )

    def test_collision_preflight_includes_installed_entrypoint(self) -> None:
        self.paths.entrypoint.parent.mkdir(parents=True)
        self.paths.entrypoint.write_text("unmanaged\n", encoding="utf-8")
        with (
            mock.patch.object(self.manager, "load_marker", return_value=None),
            mock.patch.object(
                self.manager,
                "_transaction_instance",
                return_value=None,
            ),
            mock.patch.object(
                self.manager,
                "_legacy_installation_valid",
                return_value=False,
            ),
            mock.patch(
                "forgejo.management.pwd.getpwnam",
                side_effect=KeyError,
            ),
        ):
            with self.assertRaises(ManagementError) as raised:
                self.manager._collision_preflight(self.invocation())
        self.assertEqual(raised.exception.code, "UNSAFE_COLLISION")
        self.assertIn(str(self.paths.entrypoint), raised.exception.message)

    def test_configuration_boundary_covers_all_state_paths(self) -> None:
        self.paths.configuration_root.mkdir(parents=True)
        configuration = Configuration(
            "forgejo-admin",
            "forgejo-admin@localhost.localdomain",
            "forgejo",
            "forgejo",
            "1.2.3",
            "enabled",
            "forge.local",
        )
        self.paths.app_ini.write_bytes(
            self.manager._render_app_ini(
                configuration,
                "valid-database-password",
            )
        )
        self.assertTrue(self.manager._configuration_boundary_valid())
        content = self.paths.app_ini.read_text(encoding="utf-8")
        self.paths.app_ini.write_text(
            content.replace(
                "LOCAL_ROOT_URL = http://127.0.0.1:3000/",
                "LOCAL_ROOT_URL = http://0.0.0.0:3000/",
            ),
            encoding="utf-8",
        )
        self.assertFalse(self.manager._configuration_boundary_valid())

    def test_admin_lookup_matches_only_username_column(self) -> None:
        output = subprocess.CompletedProcess(
            ["forgejo"],
            0,
            "1 owner owner@example.invalid true true\n",
            "",
        )
        with mock.patch.object(
            self.manager,
            "_run_as",
            return_value=output,
        ):
            self.assertTrue(self.manager._admin_exists("owner"))
            self.assertFalse(self.manager._admin_exists("true"))

    def test_rollback_rejects_archive_from_another_instance(self) -> None:
        archive = Path(self.temporary.name) / "rollback.tar.gz"
        manifest = {
            "schema_version": 1,
            "product_id": "forgejo",
            "product_version": self.manager.version,
            "instance_id": str(uuid.uuid4()),
            "created_at": "2026-08-10T00:00:00Z",
            "database_name": "forgejo",
            "database_user": "forgejo",
            "binary_version": "1.2.3",
            "boot": "enabled",
            "suspended": False,
        }
        payload = json.dumps(manifest).encode("utf-8")
        with tarfile.open(archive, "w:gz") as bundle:
            member = tarfile.TarInfo("forgejo-backup/manifest.json")
            member.size = len(payload)
            bundle.addfile(member, io.BytesIO(payload))
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        metadata = {
            "schema_version": 1,
            "product_id": "forgejo",
            "from_version": self.manager.version,
            "archive": str(archive),
            "archive_sha256": digest,
            "created_at": "2026-08-10T00:00:00Z",
        }
        current = {
            "instance_id": str(uuid.uuid4()),
        }
        with self.assertRaises(ManagementError) as raised:
            self.manager._validate_rollback_archive(metadata, current)
        self.assertEqual(raised.exception.code, "INVALID_ROLLBACK")


if __name__ == "__main__":
    unittest.main()
