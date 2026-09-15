# Architecture

The runtime pipeline is deliberately simple:

```text
scanners -> artifacts -> product correlation/classifier -> user overrides -> inventory -> render/export/snapshot
```

## Scanners

Each scanner returns normalized `Artifact` records. Built-ins cover APT, Snap, Flatpak, local/manual installs, systemd, Docker, language ecosystems, runtime managers, ROS and NVIDIA. Third-party Python packages may register scanner callables under the `devstatus.scanners` entry-point group.

## Classification

`devstatus/rules/catalog_*.yaml` rule packs hold concrete product signatures. `generic.yaml` provides conservative domain fallbacks. Local rules in `~/.config/devstatus/rules.d/*.yaml` load before built-ins.

Product correlation merges multiple signals into one `Tool`, e.g. an APT package, CLI binary and systemd service can all represent Redis.

## Versions

Known products prefer an explicit product version command, then package-manager / manifest metadata. User-managed unknown binaries may be probed with conventional version flags if `probe_unknown_binaries` is enabled. If a trustworthy version cannot be found, the value remains `unknown`.

User version overrides always win.

## Baseline noise

Stock Ubuntu can contain hundreds of manually-marked packages. Known products and strong generic matches appear immediately, but unclassified baseline APT noise is hidden by default. APT history is used to retain explicitly installed user packages. Newly added unknown packages appear automatically. `devstatus all` shows everything.

## State

Snapshots live under `~/.local/state/devstatus/`. Only devstatus configuration / state is modified; discovered development software is never installed, removed, upgraded or restarted by devstatus.
