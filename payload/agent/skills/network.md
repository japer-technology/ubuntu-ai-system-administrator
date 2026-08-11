<!-- triggers: network, networking, dns, nameserver, resolv, resolvectl, netplan, nmcli, wifi, wi-fi, ethernet, route, routing, firewall, ufw, iptables, port, ports, listening -->
# Skill: networking, DNS and firewalling

This skill is loaded when the operator mentions the network, DNS,
routing, wireless, firewalling or listening ports.

Operating rules:

- Start with `net.status`. It is `read_only`, runs automatically, and
  wraps `ip -brief addr` plus `ss -ltn`; pass `target: "ip"` when only
  the addresses matter. Reach for `shell.run` only for what it does not
  cover.
- Other safe inspections that stay `read_only`: `ip route show`,
  `resolvectl status`, `resolvectl query <name>`,
  `nmcli device status`, `nmcli connection show`, `networkctl status`,
  `ping`, `dig`, `traceroute`, `mtr`.
- Mutation is `network_change` and always waits for approval. That
  covers `ufw`, `iptables`, `nft`, `ip … add/del/set`, `nmcli` beyond
  its status subcommands, `netplan apply|set|try`, `resolvectl dns`,
  wireless changes, VPN tools, and any write into `/etc/netplan/`,
  `/etc/resolv.conf`, `/etc/hosts` or `/etc/NetworkManager/`.
- Separate the layers before changing anything: link up, address
  assigned, route present, DNS resolving, target reachable. Say which
  layer failed. Most "the internet is broken" reports are DNS, and DNS
  is fixed differently from routing.
- `/etc/resolv.conf` on Ubuntu is a symlink into `systemd-resolved`
  state. Editing it directly is almost always wrong and almost always
  reverted on the next reconnect; change the connection or the netplan
  configuration instead.
- Warn about self-inflicted loss of access. Applying a netplan change,
  restarting `NetworkManager` or enabling a default-deny firewall can
  drop the operator's own remote session. Say so before asking for
  approval.
- Never open an inbound port to the network. Ubuntu Zombie's only
  access surface is the loopback chat service; adding SSH, VNC, a
  tunnel or a port-forward is a change of the product's threat model,
  not a troubleshooting step. If the operator wants remote access,
  explain the trade-off and let them decide explicitly.
- When reporting listening sockets, distinguish `127.0.0.1`/`::1` from
  `0.0.0.0`/`::`. Only the latter is exposed beyond the machine, and
  that distinction is usually the whole answer.
