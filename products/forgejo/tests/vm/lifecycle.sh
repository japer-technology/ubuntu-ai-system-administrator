#!/usr/bin/env bash
set -Eeuo pipefail

[[ "${FORGEJO_DISPOSABLE_VM_TEST:-}" == "1" ]] || {
  echo "FORGEJO_DISPOSABLE_VM_TEST=1 is required." >&2
  exit 64
}
[[ "$(id -u)" == "0" ]] || {
  echo "Run only as root on a disposable supported Ubuntu VM." >&2
  exit 64
}
[[ -r /etc/os-release ]] || exit 69
# shellcheck source=/etc/os-release
. /etc/os-release
[[ "${ID}" == "ubuntu" && "${VERSION_ID}" =~ ^(22\.04|24\.04)$ ]] || {
  echo "This destructive harness supports Ubuntu 22.04/24.04 only." >&2
  exit 69
}
for path in /opt/forgejo /etc/forgejo /var/lib/forgejo \
    /usr/local/bin/forgejo /usr/local/sbin/forgejo-manage; do
  [[ ! -e "${path}" ]] || {
    echo "Refusing a host with pre-existing Forgejo state: ${path}" >&2
    exit 73
  }
done

product_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
fixture="$(mktemp -d)"
http_pid=""

cleanup() {
  set +e
  systemctl disable --now forgejo-runner.service >/dev/null 2>&1
  rm -f /etc/systemd/system/forgejo-runner.service
  rm -rf /var/lib/forgejo-runner
  rm -f /usr/local/bin/forgejo-runner
  id forgejo-runner >/dev/null 2>&1 && userdel forgejo-runner
  systemctl daemon-reload >/dev/null 2>&1
  if [[ -x /usr/local/sbin/forgejo-manage ]]; then
    /usr/local/sbin/forgejo-manage uninstall --yes --purge \
      --confirmation "DELETE FORGEJO STATE" --non-interactive >/dev/null 2>&1
  fi
  [[ -n "${http_pid}" ]] && kill "${http_pid}" >/dev/null 2>&1
  rm -rf "${fixture}" /run/forgejo/tests-enabled
  rm -rf /opt/unrelated-service /etc/unrelated-service
}
trap cleanup EXIT

mkdir -p /run/forgejo /opt/unrelated-service /etc/unrelated-service
install -m 600 /dev/null /run/forgejo/tests-enabled
printf 'sibling-state\n' > /opt/unrelated-service/forgejo-isolation-probe
printf 'sibling-config\n' > /etc/unrelated-service/forgejo-isolation-probe
sibling_before="$(
  sha256sum /opt/unrelated-service/forgejo-isolation-probe \
    /etc/unrelated-service/forgejo-isolation-probe
)"

write_fixture() {
  local version="$1" target="$2" fail_migrate="${3:-0}"
  cat > "${target}" <<PY
#!/usr/bin/env python3
import json
import pathlib
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

VERSION = "${version}"
FAIL_MIGRATE = "${fail_migrate}" == "1"
args = sys.argv[1:]
if args == ["--version"]:
    print(f"Forgejo version {VERSION}+gitea-1")
    raise SystemExit(0)
if args and args[0] == "migrate":
    raise SystemExit(1 if FAIL_MIGRATE else 0)
if args[:3] == ["admin", "user", "list"]:
    marker = pathlib.Path("/var/lib/forgejo/.fixture-admin")
    if marker.exists():
        print("1 forgejo-admin forgejo-admin@localhost.localdomain true")
    raise SystemExit(0)
if args[:3] == ["admin", "user", "create"]:
    pathlib.Path("/var/lib/forgejo/.fixture-admin").touch()
    raise SystemExit(0)
if "generate-runner-token" in args:
    print("fixture-runner-token")
    raise SystemExit(0)
if args and args[0] == "web":
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps({"status": "pass"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *_args):
            pass
    HTTPServer(("127.0.0.1", 3000), Handler).serve_forever()
raise SystemExit(2)
PY
  chmod 755 "${target}"
  sha256sum "${target}" | awk '{print $1}' > "${target}.sha256"
}

architecture="$(uname -m)"
case "${architecture}" in
  x86_64) release_arch=amd64 ;;
  aarch64) release_arch=arm64 ;;
  *) echo "Unsupported test architecture: ${architecture}" >&2; exit 69 ;;
esac
write_fixture 1.2.3 "${fixture}/forgejo-1.2.3-linux-${release_arch}"
write_fixture 1.2.4 "${fixture}/forgejo-1.2.4-linux-${release_arch}"
write_fixture 1.2.5 "${fixture}/forgejo-1.2.5-linux-${release_arch}" 1
printf '{"tag_name":"v1.2.4"}\n' > "${fixture}/latest.json"
python3 -m http.server 18765 --bind 127.0.0.1 \
  --directory "${fixture}" >"${fixture}/http.log" 2>&1 &
http_pid=$!

export FORGEJO_TEST_RELEASE_BASE=http://127.0.0.1:18765
export FORGEJO_VERSION=1.2.3
"${product_root}/scripts/manage.sh" install --yes --non-interactive
"${product_root}/scripts/manage.sh" verify --json \
  | python3 -c 'import json,sys; assert json.load(sys.stdin)["status"] == "ok"'
first_marker="$(sha256sum /var/lib/forgejo/installation.json)"
"${product_root}/scripts/manage.sh" install --yes --non-interactive
second_marker="$(sha256sum /var/lib/forgejo/installation.json)"
[[ "${first_marker}" == "${second_marker}" ]]

"${product_root}/scripts/manage.sh" backup --yes --non-interactive
"${product_root}/scripts/manage.sh" suspend --yes --non-interactive
! systemctl is-active --quiet forgejo.service
"${product_root}/scripts/manage.sh" resume --yes --non-interactive
systemctl is-active --quiet forgejo.service

FORGEJO_VERSION=1.2.4 "${product_root}/scripts/manage.sh" \
  update --yes --non-interactive
/usr/local/bin/forgejo --version | grep -q '1.2.4'
"${product_root}/scripts/manage.sh" rollback --yes --non-interactive
/usr/local/bin/forgejo --version | grep -q '1.2.3'

if FORGEJO_VERSION=1.2.5 "${product_root}/scripts/manage.sh" \
    update --yes --non-interactive; then
  echo "Forgejo update unexpectedly ignored a failed migration." >&2
  exit 1
fi
/usr/local/bin/forgejo --version | grep -q '1.2.5'
"${product_root}/scripts/manage.sh" rollback --yes --non-interactive
/usr/local/bin/forgejo --version | grep -q '1.2.3'

adduser --system --group --home /var/lib/forgejo-runner \
  --shell /usr/sbin/nologin forgejo-runner
install -d -m 750 -o forgejo-runner -g forgejo-runner \
  /var/lib/forgejo-runner
host="$(awk -F' = ' '$1 == "DOMAIN" {print $2; exit}' /etc/forgejo/app.ini)"
cat > "${fixture}/runner-config.yaml" <<EOF
runner:
  envs:
    SSL_CERT_FILE: /etc/ssl/certs/ca-certificates.crt
    NODE_EXTRA_CA_CERTS: /etc/ssl/certs/ca-certificates.crt
container:
  network: host
  privileged: false
  options: >-
    --add-host ${host}:127.0.0.1
    --volume /etc/ssl/certs/ca-certificates.crt:/etc/ssl/certs/ca-certificates.crt:ro
  valid_volumes: []
  docker_host: "-"
EOF
install -m 640 -o root -g forgejo-runner \
  "${fixture}/runner-config.yaml" /var/lib/forgejo-runner/config.yaml
install -m 755 /bin/true /usr/local/bin/forgejo-runner
cat > /etc/systemd/system/forgejo-runner.service <<'EOF'
[Unit]
After=forgejo.service
Wants=forgejo.service
[Service]
ExecStart=/bin/sleep infinity
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now forgejo-runner.service
"${product_root}/scripts/manage.sh" repair --yes --non-interactive
systemctl is-active --quiet forgejo-runner.service
"${product_root}/scripts/manage.sh" verify --json \
  | python3 -c 'import json,sys; assert json.load(sys.stdin)["status"] == "ok"'

if "${product_root}/scripts/manage.sh" uninstall --yes --purge \
    --confirmation "DELETE FORGEJO STATE" --non-interactive; then
  echo "Forgejo uninstall unexpectedly ignored the runner dependency." >&2
  exit 1
fi
systemctl disable --now forgejo-runner.service
rm -f /etc/systemd/system/forgejo-runner.service \
  /usr/local/bin/forgejo-runner
rm -rf /var/lib/forgejo-runner
userdel forgejo-runner
systemctl daemon-reload
"${product_root}/scripts/manage.sh" uninstall --yes --purge \
  --confirmation "DELETE FORGEJO STATE" --non-interactive

[[ ! -e /var/lib/forgejo && ! -e /etc/forgejo ]]
[[ "${sibling_before}" == "$(
  sha256sum /opt/unrelated-service/forgejo-isolation-probe \
    /etc/unrelated-service/forgejo-isolation-probe
)" ]]
echo "Forgejo disposable-VM lifecycle passed."
