<!-- triggers: docker, dockerd, podman, container, containers, lxd, lxc, compose, kubernetes, kubectl, dockerfile, registry -->
# Skill: containers on Ubuntu

This skill is loaded when the operator mentions Docker, Podman, LXD or
Kubernetes.

Operating rules:

- Inspect before acting. `docker ps`, `docker images`, `docker inspect`,
  `docker system df`, `podman ps` and `kubectl get`/`describe` are
  `read_only` and auto-run. Container problems are usually visible in
  `docker logs <name>` before any change is needed.
- Know which runtime is installed before proposing commands. Ubuntu
  ships `docker.io`, Docker Inc. ships `docker-ce` with
  `containerd.io`, and installing one over the other replaces packages
  and can stop every running container. Check `dpkg -l | grep -E
  'docker|containerd'` and reuse whatever is already there.
- Docker's socket is root-equivalent. Adding a user to the `docker`
  group grants passwordless root on the host in practice — say that
  plainly and let the operator decide; it is a security change, not a
  convenience. Prefer `sudo docker` or rootless Podman.
- `docker run` with `--privileged`, `--net=host`, `--pid=host` or a
  bind mount of `/`, `/var/run/docker.sock` or `/etc` removes the
  isolation the operator is relying on. Do not add those flags to make
  something work without naming what they expose.
- Destructive pruning is destructive. `docker system prune -a`,
  `docker volume prune` and `docker rm -v` delete images and *data*
  volumes; they need the exact confirmation phrase. List what would go
  first (`docker system df -v`, `docker volume ls`) and quote the
  reclaimable size.
- Containers are the usual answer to "where did my disk go" on a
  developer machine: `/var/lib/docker` grows without bound. Measure it
  (`sudo du -sh /var/lib/docker`) before proposing anything more
  drastic than `docker image prune` on dangling images.
- Never pass secrets on a `docker run` command line or bake them into a
  Dockerfile — they land in the audit log, the shell history and the
  image layers. Use an env file with restrictive permissions or the
  runtime's secret mechanism.
- Restarting the Docker daemon stops every container that is not
  configured to restart. Enumerate the running containers and their
  restart policies before proposing `systemctl restart docker`.
- LXD/Incus system containers are closer to VMs: `lxc list`,
  `lxc info`, `lxc config show` describe them, and deleting an instance
  destroys its storage volume. Real hypervisors — KVM, VirtualBox,
  Multipass — are the `virtualization` skill.
- Kubernetes contexts are a footgun. Print `kubectl config
  current-context` and confirm it with the operator before any command
  that mutates cluster state — a "test" namespace on the wrong cluster
  is a production incident.
