# MoveIt Pro Fairino Workspace

A MoveIt Pro workspace for the Fairino FR5 robot, including a mock configuration
(`fairino_mock`) and the upstream `frcobot_ros2` hardware driver as a submodule.

For more information, refer to the [MoveIt Pro Documentation](https://docs.picknik.ai/).

## Cloning the workspace

This repository uses **Git LFS** for mesh/3D assets (`.stl`, `.obj`, `.dae`, …)
and a **Git submodule** for the Fairino driver. Both must be set up or the
workspace will not build correctly.

### 1. Install Git LFS (one-time, per machine)

```bash
sudo apt update && sudo apt install -y git-lfs
git lfs install
```

### 2. Clone with submodules

```bash
git clone --recurse-submodules git@github.com:PickNikRobotics/moveit_pro_fairino_ws.git
```

If you already cloned without `--recurse-submodules`, initialize them after the
fact:

```bash
cd moveit_pro_fairino_ws
git submodule update --init --recursive
```

### 3. Pull LFS assets

`git lfs install` makes future clones/pulls fetch LFS files automatically. To
fetch them for an existing checkout (or verify they downloaded):

```bash
git lfs pull
```

> **Tip:** if mesh files show up as small text pointer files instead of real
> binaries, LFS wasn't active at clone time — run `git lfs install` then
> `git lfs pull`.

## Connecting to the FR5 hardware

The Fairino controller ships at the default IP **`192.168.58.2`** (the button-box
/ debug Ethernet port), as documented in the
[FAIRINO Collaborative Robot User Manual — Installation](https://manual.fairino.support/latest/CobotsManual/installation.html).
Put your Ubuntu host PC on the same subnet with a static address.

### 1. Find the Ethernet interface with the robot cable plugged in

```bash
ip -br link
```

Pick the wired interface showing **`UP` / `LOWER_UP`** (carrier present) once the
robot cable is connected — *not* a port reporting `NO-CARRIER`. Set it as a
variable so the next command is copy-paste:

```bash
export ROBOT_IFACE=eno1   # replace with your interface from `ip -br link`
```

### 2. Create and activate a static connection

```bash
sudo nmcli con add type ethernet ifname "$ROBOT_IFACE" con-name fairino \
  ipv4.method manual ipv4.addresses 192.168.58.100/24 \
  && sudo nmcli con up fairino
```

### 3. Verify connectivity

```bash
ping 192.168.58.2
```

A reply means you're on the robot's network and ready to launch the driver.

> **Notes**
> - No gateway is set — this is a direct robot link, not internet access, so your
>   normal Wi-Fi/Ethernet route is left untouched.
> - `192.168.58.100` is arbitrary; any `192.168.58.x` works except `.2` (the robot).
> - `Destination Host Unreachable` usually means the static IP landed on a port
>   with no live cable. Confirm `ROBOT_IFACE` is the interface showing
>   `LOWER_UP`, then rebind: `sudo nmcli con mod fairino connection.interface-name "$ROBOT_IFACE" && sudo nmcli con up fairino`.
> - To remove this connection later: `sudo nmcli con delete fairino`.
