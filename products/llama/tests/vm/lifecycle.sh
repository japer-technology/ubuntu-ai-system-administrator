#!/usr/bin/env bash
set -Eeuo pipefail

[[ "${LLAMA_DISPOSABLE_VM_TEST:-}" == "1" ]] || {
  echo "Refusing to mutate a host without the disposable-VM test sentinel." >&2
  exit 69
}
[[ "$(id -u)" -eq 0 ]] || {
  echo "Disposable-VM lifecycle tests must run as root." >&2
  exit 69
}

product_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
work="$(mktemp -d /tmp/llama-vm-test.XXXXXX)"
asset_pid=""
sibling_root_created=0
sibling_canary_created=0
sibling_canary="/opt/ai-zombie/llama-isolation-canary"
cleanup() {
  if [[ -n "${asset_pid}" ]]; then
    kill "${asset_pid}" 2>/dev/null || true
    wait "${asset_pid}" 2>/dev/null || true
  fi
  if [[ "${sibling_canary_created}" == "1" ]]; then
    rm -f -- "${sibling_canary}"
  fi
  if [[ "${sibling_root_created}" == "1" ]]; then
    rmdir /opt/ai-zombie /opt 2>/dev/null || true
  fi
  rm -rf -- "${work}"
}
trap cleanup EXIT

for path in /opt/llama.cpp /etc/llama.cpp /var/lib/llama.cpp \
    /var/log/llama.cpp /var/cache/llama.cpp /var/backups/llama.cpp \
    /etc/systemd/system/llama-server.service /etc/logrotate.d/llama \
    /usr/local/sbin/llama-manage /usr/local/bin/llama-manager; do
  [[ ! -e "${path}" && ! -L "${path}" ]] || {
    echo "Refusing to overwrite pre-existing Llama resource: ${path}" >&2
    exit 73
  }
done
id llama-cpp >/dev/null 2>&1 && {
  echo "Refusing to overwrite the pre-existing llama-cpp account." >&2
  exit 73
}
if [[ ! -d /opt/ai-zombie ]]; then
  install -d -m 755 -o root -g root /opt/ai-zombie
  sibling_root_created=1
fi
[[ ! -e "${sibling_canary}" ]] || {
  echo "Refusing to overwrite the sibling-isolation canary." >&2
  exit 73
}
printf 'ubuntu-zombie sibling state\n' > "${sibling_canary}"
sibling_canary_created=1
sibling_digest="$(sha256sum "${sibling_canary}" | awk '{print $1}')"

assets="${work}/assets"
mkdir -p "${assets}" "${work}/runtime-v1/fixture-v1" \
  "${work}/runtime-v2/fixture-v2"
cat > "${work}/llama-server" <<'PY'
#!/usr/bin/env python3
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def argument(name, default):
    try:
        return sys.argv[sys.argv.index(name) + 1]
    except (ValueError, IndexError):
        return default


model = argument("--alias", "fixture-model")
port = int(argument("--port", "8080"))


class Handler(BaseHTTPRequestHandler):
    def reply(self, value):
        payload = json.dumps(value).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/health":
            self.reply(
                {
                    "status": "ok",
                    "ubuntu_zombie_visible": Path(
                        "/opt/ai-zombie/llama-isolation-canary"
                    ).exists(),
                }
            )
        elif self.path == "/v1/models":
            self.reply({"data": [{"id": model, "object": "model"}]})
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        self.reply(
            {
                "choices": [
                    {"message": {"role": "assistant", "content": "OK"}}
                ]
            }
        )

    def log_message(self, _format, *_arguments):
        return


ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
PY
chmod 755 "${work}/llama-server"
for version in v1 v2; do
  root="${work}/runtime-${version}/fixture-${version}"
  install -m 755 "${work}/llama-server" "${root}/llama-server"
  for binary in llama-cli llama-bench; do
    printf '#!/bin/sh\nexit 0\n' > "${root}/${binary}"
    chmod 755 "${root}/${binary}"
  done
  tar -czf "${assets}/runtime-${version}.tar.gz" \
    -C "${work}/runtime-${version}" "fixture-${version}"
done
printf 'fixture model\n' > "${assets}/fixture.gguf"

cp -a "${product_root}" "${work}/product-v1"
cp -a "${product_root}" "${work}/product-v2"
printf '2999.01.01.00.00.00\n' > "${work}/product-v2/VERSION"

write_catalogues() {
  local root="$1" release="$2" archive="$3"
  local runtime_digest model_digest model_size
  runtime_digest="$(sha256sum "${assets}/${archive}" | awk '{print $1}')"
  model_digest="$(sha256sum "${assets}/fixture.gguf" | awk '{print $1}')"
  model_size="$(stat -c %s "${assets}/fixture.gguf")"
  python3 - "${root}" "${release}" "${archive}" "${runtime_digest}" \
    "${model_digest}" "${model_size}" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
release, archive, runtime_digest, model_digest, model_size = sys.argv[2:]
base_url = "http://127.0.0.1:18081"
asset = {
    "url": f"{base_url}/{archive}",
    "sha256": runtime_digest,
    "archive_root": release,
}
(root / "payload/etc/llama-builds.json").write_text(
    json.dumps(
        {
            "schema_version": 1,
            "release": release,
            "commit": "1111111111111111111111111111111111111111",
            "assets": {"amd64": asset, "arm64": asset},
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
(root / "payload/etc/llama-models.json").write_text(
    json.dumps(
        {
            "schema_version": 1,
            "models": [
                {
                    "id": "fixture-model",
                    "name": "Fixture model",
                    "filename": "fixture.gguf",
                    "url": f"{base_url}/fixture.gguf",
                    "sha256": model_digest,
                    "size_bytes": int(model_size),
                    "license": "Apache-2.0",
                    "context_size": 2048,
                }
            ],
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
PY
}
write_catalogues "${work}/product-v1" fixture-v1 runtime-v1.tar.gz
write_catalogues "${work}/product-v2" fixture-v2 runtime-v2.tar.gz

python3 -m http.server 18081 --bind 127.0.0.1 --directory "${assets}" \
  >"${work}/asset-server.log" 2>&1 &
asset_pid=$!
for _ in {1..100}; do
  curl -fsS "http://127.0.0.1:18081/fixture.gguf" >/dev/null 2>&1 && break
  sleep 0.05
done
curl -fsS "http://127.0.0.1:18081/fixture.gguf" >/dev/null
kill -0 "${asset_pid}"

export LLAMA_DISPOSABLE_VM_TEST=1
export LLAMA_NONINTERACTIVE=1
export LLAMA_MODEL_ID=fixture-model
export LLAMA_CONTEXT_SIZE=1024
export LLAMA_CPU_THREADS=1
export LLAMA_BOOT=enabled
manage_v1="${work}/product-v1/scripts/manage.sh"
manage_v2="${work}/product-v2/scripts/manage.sh"

assert_response() {
  local path="$1" operation="$2" expected_status="$3"
  python3 - "${path}" "${operation}" "${expected_status}" <<'PY'
import json
import sys
from pathlib import Path

value = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert value["schema_version"] == 1, value
assert value["product_id"] == "llama", value
assert value["operation"] == sys.argv[2], value
assert value["status"] == sys.argv[3], value
assert isinstance(value["correlation_id"], str), value
PY
}

"${manage_v1}" install --dry-run --json > "${work}/install-plan.json"
assert_response "${work}/install-plan.json" install ok
[[ ! -e /run/lock/llama.lock ]]
set +e
"${manage_v1}" install --non-interactive --json > "${work}/confirmation.json"
confirmation_status=$?
set -e
[[ "${confirmation_status}" -eq 64 ]]

"${manage_v1}" install --yes --json > "${work}/install.json"
assert_response "${work}/install.json" install ok
"${manage_v1}" verify --json > "${work}/verify.json"
assert_response "${work}/verify.json" verify ok
[[ "$(stat -c '%U:%G:%a' /var/lib/llama.cpp/models/fixture.gguf)" \
  == "llama-cpp:llama-cpp:640" ]]
[[ "$(stat -c '%U:%G:%a' /var/log/llama.cpp)" \
  == "root:llama-cpp:750" ]]
[[ "$(stat -c '%U:%G:%a' /var/log/llama.cpp/product-ownership)" \
  == "root:root:600" ]]
[[ "$(systemctl show llama-server.service --property=MainPID --value)" != "0" ]]
llama-manager test
python3 - <<'PY'
import json
import urllib.request

with urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=5) as response:
    value = json.load(response)
assert value["ubuntu_zombie_visible"] is False, value
PY

"${manage_v1}" doctor --json > "${work}/doctor.json"
assert_response "${work}/doctor.json" doctor ok
"${manage_v1}" repair --yes --json > "${work}/repair.json"
assert_response "${work}/repair.json" repair ok
python3 - "${work}/repair.json" <<'PY'
import json
import sys
from pathlib import Path

assert json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["changed"] is False
PY

LLAMA_BOOT=disabled \
  "${manage_v1}" repair --yes --json > "${work}/disable.json"
assert_response "${work}/disable.json" repair ok
if systemctl is-active --quiet llama-server.service; then
  echo "Disabled Llama service remained active." >&2
  exit 1
fi
if systemctl is-enabled --quiet llama-server.service; then
  echo "Disabled Llama service remained enabled." >&2
  exit 1
fi
if curl -fsS --max-time 2 http://127.0.0.1:8080/health >/dev/null 2>&1; then
  echo "Disabled Llama service still owns its loopback listener." >&2
  exit 1
fi
LLAMA_BOOT=enabled \
  "${manage_v1}" repair --yes --json > "${work}/enable.json"
assert_response "${work}/enable.json" repair ok
systemctl is-active --quiet llama-server.service
systemctl is-enabled --quiet llama-server.service
llama-manager test

"${manage_v1}" install --yes --json > "${work}/reinstall.json"
assert_response "${work}/reinstall.json" install ok
python3 - "${work}/reinstall.json" <<'PY'
import json
import sys
from pathlib import Path

assert json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["changed"] is False
PY

"${manage_v1}" suspend --yes --json > "${work}/suspend.json"
assert_response "${work}/suspend.json" suspend ok
! systemctl is-active --quiet llama-server.service
"${manage_v1}" resume --yes --json > "${work}/resume.json"
assert_response "${work}/resume.json" resume ok
"${manage_v1}" resume --yes --json > "${work}/second-resume.json"
python3 - "${work}/second-resume.json" <<'PY'
import json
import sys
from pathlib import Path

assert json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["changed"] is False
PY

backup_root="/var/backups/llama-vm-test"
install -d -m 700 -o root -g root "${backup_root}"
LLAMA_BACKUP_DESTINATION="${backup_root}" \
  "${manage_v1}" backup --yes --json > "${work}/backup.json"
assert_response "${work}/backup.json" backup ok
find "${backup_root}" -maxdepth 1 -type f -name 'llama-backup-*.tar.gz' \
  -perm 0600 | grep -q .

old_pid="$(systemctl show llama-server.service --property=MainPID --value)"
"${manage_v2}" update --yes --json > "${work}/update.json"
assert_response "${work}/update.json" update ok
new_pid="$(systemctl show llama-server.service --property=MainPID --value)"
[[ "${new_pid}" != "0" && "${new_pid}" != "${old_pid}" ]]
"${manage_v2}" verify --json > "${work}/updated-verify.json"
assert_response "${work}/updated-verify.json" verify ok

"${manage_v2}" rollback --yes --json > "${work}/rollback.json"
assert_response "${work}/rollback.json" rollback ok
/usr/local/sbin/llama-manage verify --json > "${work}/rollback-verify.json"
assert_response "${work}/rollback-verify.json" verify ok

"${manage_v1}" uninstall --yes --json > "${work}/retain.json"
assert_response "${work}/retain.json" uninstall ok
[[ ! -e /opt/llama.cpp && ! -e /etc/llama.cpp ]]
[[ -f /var/lib/llama.cpp/models/fixture.gguf ]]
"${manage_v1}" status --json > "${work}/retained-status.json"
assert_response "${work}/retained-status.json" status degraded

"${manage_v1}" install --yes --json > "${work}/recovered-install.json"
assert_response "${work}/recovered-install.json" install ok
set +e
"${manage_v1}" uninstall --purge --yes --json > "${work}/blocked-purge.json"
blocked_purge_status=$?
set -e
[[ "${blocked_purge_status}" -eq 64 ]]
"${manage_v1}" uninstall --purge \
  --confirmation 'DELETE LLAMA STATE' --yes --json > "${work}/purge.json"
assert_response "${work}/purge.json" uninstall ok
[[ ! -e /opt/llama.cpp && ! -e /etc/llama.cpp ]]
[[ ! -e /var/lib/llama.cpp && ! -e /var/cache/llama.cpp ]]
[[ ! -e /usr/local/sbin/llama-manage && ! -e /usr/local/bin/llama-manager ]]
[[ ! -e /etc/systemd/system/llama-server.service ]]
[[ ! -e /etc/logrotate.d/llama ]]
! id llama-cpp >/dev/null 2>&1
[[ -f /var/log/llama.cpp/audit.log ]]

# Retained audit evidence must not block a later clean installation.
"${manage_v1}" install --yes --json > "${work}/post-purge-install.json"
assert_response "${work}/post-purge-install.json" install ok
"${manage_v1}" uninstall --purge \
  --confirmation 'DELETE LLAMA STATE' --yes --json > "${work}/final-purge.json"
assert_response "${work}/final-purge.json" uninstall ok
[[ "$(sha256sum "${sibling_canary}" | awk '{print $1}')" == "${sibling_digest}" ]]
rm -rf -- "${backup_root}" /var/backups/llama.cpp
