#!/usr/bin/env bash
set -Eeuo pipefail

[[ "${IMAGINARY_FRIEND_DISPOSABLE_VM_TEST:-}" == "1" ]] || {
  echo "Refusing to mutate a host without the disposable-VM test sentinel." >&2
  exit 69
}
[[ "$(id -u)" -eq 0 ]] || {
  echo "Disposable-VM lifecycle tests must run as root." >&2
  exit 69
}

product_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
manage="${product_root}/scripts/manage.sh"
owner="${IMAGINARY_FRIEND_TEST_OWNER:-}"
[[ -n "${owner}" && "${owner}" != "root" ]] || {
  echo "The VM test owner must name a non-root account." >&2
  exit 64
}
id "${owner}" >/dev/null 2>&1 || {
  echo "The VM test owner does not exist." >&2
  exit 64
}

work="$(mktemp -d /tmp/imaginary-friend-vm-test.XXXXXX)"
fixture_pid=""
cleanup() {
  if [[ -n "${fixture_pid}" ]]; then
    kill "${fixture_pid}" 2>/dev/null || true
    wait "${fixture_pid}" 2>/dev/null || true
  fi
  rm -rf -- "${work}"
}
trap cleanup EXIT

credential_file="${work}/owner-credential"
printf '%s\n' "disposable-vm-owner-password" > "${credential_file}"
chmod 600 "${credential_file}"

set +e
FRIEND_NONINTERACTIVE=1 "${manage}" install --dry-run --json \
  > "${work}/missing-input.json"
missing_input_status=$?
set -e
[[ "${missing_input_status}" -eq 64 ]]

PYTHONPATH="${product_root}/payload/agent" \
  python3 "${product_root}/tests/fixtures/openai_fixture.py" --port 18080 &
fixture_pid=$!
fixture_ready=0
for _ in {1..100}; do
  if python3 - <<'PY'
import http.client

connection = http.client.HTTPConnection("127.0.0.1", 18080, timeout=1)
try:
    connection.request("GET", "/v1/models")
    raise SystemExit(0 if connection.getresponse().status == 200 else 1)
except OSError:
    raise SystemExit(1)
finally:
    connection.close()
PY
  then
    fixture_ready=1
    break
  fi
  sleep 0.05
done
[[ "${fixture_ready}" -eq 1 ]]
kill -0 "${fixture_pid}"

export FRIEND_NONINTERACTIVE=1
export FRIEND_OWNER_USER="${owner}"
export FRIEND_OWNER_PASSWORD_FILE="${credential_file}"
export FRIEND_MODEL_BASE_URL="http://127.0.0.1:18080/v1"
export FRIEND_MODEL="fixture-friend"

assert_response() {
  local path="$1"
  local operation="$2"
  local expected_status="$3"
  python3 - "${path}" "${operation}" "${expected_status}" <<'PY'
import json
import sys
from pathlib import Path

value = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert value["schema_version"] == 1, value
assert value["product_id"] == "imaginary-friend", value
assert value["operation"] == sys.argv[2], value
assert value["status"] == sys.argv[3], value
assert isinstance(value["correlation_id"], str), value
PY
}

"${manage}" install --dry-run --json > "${work}/install-plan.json"
assert_response "${work}/install-plan.json" install ok
[[ ! -e /run/lock/imaginary-friend.lock ]]

"${manage}" install --yes --json > "${work}/install.json"
assert_response "${work}/install.json" install ok
"${manage}" verify --json > "${work}/verify.json"
assert_response "${work}/verify.json" verify ok
[[ "$(stat -c '%U:%G:%a' /etc/imaginary-friend/session.key)" == "root:friend:640" ]]
[[ "$(stat -c '%U:%G:%a' /var/lib/imaginary-friend/friend.db)" == "friend:friend:600" ]]
[[ "$(id -nG friend | tr ' ' '\n' | sort | paste -sd ' ' -)" == "friend friend-share" ]]
runuser -u friend -- test ! -w /etc/imaginary-friend/policy.json
runuser -u friend -- test ! -w /opt/imaginary-friend/agent/friend/server.py
set +e
runuser -u friend -- /usr/local/sbin/friend-manage suspend --yes --json \
  > "${work}/service-account-manage.json"
service_account_status=$?
set -e
[[ "${service_account_status}" -eq 73 ]]
! grep -Fq "disposable-vm-owner-password" /var/log/imaginary-friend/audit.log

unset FRIEND_OWNER_PASSWORD_FILE
"${manage}" install --yes --json > "${work}/reinstall.json"
assert_response "${work}/reinstall.json" install ok

"${manage}" suspend --yes --json > "${work}/suspend.json"
assert_response "${work}/suspend.json" suspend ok
"${manage}" status --json > "${work}/suspended-status.json"
assert_response "${work}/suspended-status.json" status ok
"${manage}" install --yes --json > "${work}/suspended-reinstall.json"
assert_response "${work}/suspended-reinstall.json" install ok
"${manage}" status --json > "${work}/reinstalled-suspended-status.json"
assert_response "${work}/reinstalled-suspended-status.json" status ok
python3 - "${work}/reinstalled-suspended-status.json" <<'PY'
import json
import sys
from pathlib import Path

value = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert value["details"]["imaginary_friend"]["lifecycle"] == "suspended", value
assert any(
    check["id"] == "suspension" and check["status"] == "warn"
    for check in value["checks"]
), value
PY
! systemctl is-active --quiet imaginary-friend-chat.service
"${manage}" resume --yes --json > "${work}/resume.json"
assert_response "${work}/resume.json" resume ok

backup_root="/var/backups/imaginary-friend-vm-test"
install -d -m 0700 -o root -g root "${backup_root}"
backup_request="${work}/backup-request.json"
correlation="$(python3 -c 'import uuid; print(uuid.uuid4())')"
python3 - "${backup_request}" "${correlation}" "${backup_root}" <<'PY'
import json
import sys
from pathlib import Path

Path(sys.argv[1]).write_text(
    json.dumps(
        {
            "schema_version": 1,
            "product_id": "imaginary-friend",
            "operation": "backup",
            "correlation_id": sys.argv[2],
            "requested_by": "operator",
            "inputs": {"backup_destination": sys.argv[3]},
            "confirmation": None,
        }
    ),
    encoding="utf-8",
)
PY
chmod 600 "${backup_request}"
"${manage}" backup --request-file "${backup_request}" --yes --json \
  > "${work}/backup.json"
assert_response "${work}/backup.json" backup ok
find "${backup_root}" -maxdepth 1 -type f \
  -name 'imaginary-friend-backup-*.tar.gz' -perm 0600 | grep -q .

"${manage}" rollback --yes --json > "${work}/rollback.json"
assert_response "${work}/rollback.json" rollback ok
"${manage}" verify --json > "${work}/post-rollback-verify.json"
assert_response "${work}/post-rollback-verify.json" verify ok

retain_request="${work}/retain-request.json"
correlation="$(python3 -c 'import uuid; print(uuid.uuid4())')"
python3 - "${retain_request}" "${correlation}" <<'PY'
import json
import sys
from pathlib import Path

Path(sys.argv[1]).write_text(
    json.dumps(
        {
            "schema_version": 1,
            "product_id": "imaginary-friend",
            "operation": "uninstall",
            "correlation_id": sys.argv[2],
            "requested_by": "operator",
            "inputs": {},
            "retain_state": True,
            "confirmation": None,
        }
    ),
    encoding="utf-8",
)
PY
chmod 600 "${retain_request}"
"${manage}" uninstall --request-file "${retain_request}" --yes --json \
  > "${work}/retain.json"
assert_response "${work}/retain.json" uninstall ok
"${manage}" status --json > "${work}/retained-status.json"
assert_response "${work}/retained-status.json" status degraded

"${manage}" install --yes --json > "${work}/recovered-install.json"
assert_response "${work}/recovered-install.json" install ok
printf '%s\n' "workspace survives removal" \
  > /srv/imaginary-friend/workspace/uninstall-canary.txt

delete_request="${work}/delete-request.json"
correlation="$(python3 -c 'import uuid; print(uuid.uuid4())')"
python3 - "${delete_request}" "${correlation}" <<'PY'
import json
import sys
from pathlib import Path

Path(sys.argv[1]).write_text(
    json.dumps(
        {
            "schema_version": 1,
            "product_id": "imaginary-friend",
            "operation": "uninstall",
            "correlation_id": sys.argv[2],
            "requested_by": "operator",
            "inputs": {},
            "retain_state": False,
            "confirmation": "DELETE IMAGINARY FRIEND STATE",
        }
    ),
    encoding="utf-8",
)
PY
chmod 600 "${delete_request}"
"${manage}" uninstall --request-file "${delete_request}" --yes --json \
  > "${work}/delete.json"
assert_response "${work}/delete.json" uninstall ok

[[ ! -e /opt/imaginary-friend ]]
[[ ! -e /etc/imaginary-friend ]]
[[ ! -e /var/lib/imaginary-friend ]]
[[ ! -e /etc/systemd/system/imaginary-friend-chat.service ]]
[[ -f /srv/imaginary-friend/workspace/uninstall-canary.txt ]]
