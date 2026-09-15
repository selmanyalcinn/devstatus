# devstatus

`devstatus` is a read-mostly Linux CLI that answers four questions:

1. **What development software is installed on this machine?**
2. **Where does each tool belong in the software stack?**
3. **Which versions / environments / services are active?**
4. **What changed since the last scan?**

It builds a dynamic tree from the real machine rather than a hand-written checklist.

```text
Ubuntu 24.04
├── Languages & Toolchains
│   ├── C & C++
│   │   ├── GCC 13.3
│   │   └── Clang 18.1
│   └── Python
│       ├── Python 3.12.3
│       ├── uv 0.x
│       └── Conda 25.x
├── Databases
│   ├── MongoDB 8.x [running]
│   └── Redis 8.x [running]
├── Messaging & Streaming
│   └── Apache Kafka 4.x
├── Robotics
│   ├── ROS 2 Jazzy
│   └── Gazebo Harmonic
└── Containers
    └── Docker 29.x [running]
```

## What it scans

- APT / dpkg manual packages
- Snap and Flatpak
- local binaries in `/usr/local/bin`, `~/.local/bin`, `~/.cargo/bin`, `~/go/bin`
- manual installs under `/opt`
- systemd services
- Docker Engine, Compose, images and containers
- Python distributions, top-level pip packages, pipx and uv tools
- npm global packages
- Cargo installs and Go-installed binaries
- Conda environments, uv Python installs, NVM Node versions, Rustup toolchains
- ROS distributions and ROS 2 packages
- NVIDIA GPU / driver / reported CUDA-driver capability
- third-party scanner plugins via the `devstatus.scanners` Python entry-point group

## Classification

The bundled knowledge base contains **300+ product signatures** across backend, frontend, databases, messaging, AI/ML, data engineering, robotics, embedded, systems, networking, security, testing, containers, Kubernetes, cloud/DevOps, observability, graphics/game development and developer utilities.

Classification uses, depending on the source:

- package names and descriptions
- binary names
- service names
- Python/npm/Cargo/Go package/module names
- manual install paths
- known version commands
- generic domain keywords

Unknown user-installed software is not discarded. It appears under `Other / Unclassified` and can be corrected without changing source code.

## Install

With `uv`:

```bash
uv tool install .
```

During development:

```bash
uv tool install --editable .
```

Or with pipx:

```bash
pipx install .
```

Verify:

```bash
devstatus --version
devstatus rules stats
```

## Everyday commands

```bash
devstatus                    # scan, render tree, save snapshot
devstatus scan --no-save     # inspect without changing snapshot history
devstatus all                # include noisy baseline unknowns
devstatus new                # changes since last snapshot
devstatus new --raw          # include underlying package/artifact changes
devstatus history
devstatus diff previous latest
```

### Find / explain / filter

```bash
devstatus search kafka
devstatus search robotics
devstatus tag ai
devstatus tag security
devstatus explain mongodb
```

### Correct automatic detection

```bash
devstatus set unclassified:foo version 2.4.1
devstatus set unclassified:foo category "AI & ML > Inference"
devstatus set unclassified:foo name "Foo Runtime"
devstatus set unclassified:foo tags "ai,inference,gpu"
devstatus edit unclassified:foo
```

Return a field to automatic detection:

```bash
devstatus unset unclassified:foo version
```

Hide / unhide:

```bash
devstatus hide unclassified:foo
devstatus unhide unclassified:foo
```

Overrides are stored under:

```text
~/.config/devstatus/overrides.json
```

## Environments and services

```bash
devstatus env
devstatus services
devstatus services --all
devstatus packages
devstatus packages --source apt
devstatus docker
devstatus ports
devstatus disk
```

## Diagnostics

```bash
devstatus doctor
devstatus outdated
```

`doctor` is intentionally non-destructive. It reports issues such as an unreachable Docker daemon, failed systemd services, ROS installed but not sourced, GPU query failures, low root-disk space, broken local-bin symlinks, scanner errors and unknown versions.

`outdated` asks package managers for update information but does not install anything.

## Project awareness

Run inside a repository:

```bash
devstatus project
```

It recognizes Python, Node, Rust, Go, CMake, Meson, Docker/Compose, ROS, Maven, Gradle, Terraform, Kubernetes/Helm, Flutter and PlatformIO, plus common runtime pin files such as `.python-version` and `.nvmrc`.

## Export and compare machines

```bash
devstatus export -f json -o laptop.json
devstatus export -f yaml -o laptop.yaml

devstatus compare laptop.json desktop.json
```

## TUI

```bash
devstatus tui
```

Use `r` to refresh and `q` to quit. Select a tool to inspect category, version source, tags and sources.

## Custom classification rules

See rule statistics:

```bash
devstatus rules stats
```

Create a local rule file:

```bash
devstatus rules init my-rules.yaml
```

Rules live in:

```text
~/.config/devstatus/rules.d/
```

Validate them:

```bash
devstatus rules validate
```

Example:

```yaml
products:
  - id: my-engine
    name: My Engine
    category: [Robotics, Simulation]
    tags: [robotics, simulation]
    packages: [my-engine]
    binaries: [my-engine]
    services: [my-engine.service]
    version_commands:
      - [my-engine, --version]
```

Custom rules are loaded before built-ins.

## Settings

```bash
devstatus config show
devstatus config set probe_unknown_binaries true
devstatus config set history_limit 200
```

The generic unknown-binary version probe tries conventional read-only version flags (`--version`, `version`, `-V`) for executables in user-managed binary directories. Disable it if you do not want unknown executables invoked:

```bash
devstatus config set probe_unknown_binaries false
```

## State layout

```text
~/.config/devstatus/
├── settings.json
├── overrides.json
└── rules.d/

~/.local/state/devstatus/
├── latest.json
└── history/
```

## Design principle

`devstatus` does **not** install, remove, upgrade or restart development software. User overrides and devstatus's own local state/configuration are the only state it intentionally changes.

If automatic version detection cannot determine a trustworthy version, it reports `unknown` instead of inventing one.
