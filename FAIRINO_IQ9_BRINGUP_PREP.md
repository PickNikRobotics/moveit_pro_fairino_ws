# Fairino FR5 + MoveIt Pro on IQ9 Dragonwing — Bring-up Prep Brief

Prepared off-hardware (no access to IQ9-02 or the arm yet). Target: configure a Qualcomm
IQ-9075 Dragonwing (aarch64) to drive a Fairino FR5 via the `moveit_pro_fairino_ws`
workspace. Everything below is derived from the cloned workspace + Fairino docs; verify each
`[VERIFY ON HW]` item on the bench.

---

## 0. TL;DR — the three things that will bite

1. **`libfairino.so.2.2.3` is x86-64 ONLY.** The Fairino ros2_control driver dlopens a
   proprietary blob that is x86_64 — it will NOT link/load on the arm64 IQ9. This is the #1
   blocker. Fix path is known (see §3) but needs an aarch64 lib + a version/ABI check.
2. **The enable-chain is NOT visible to ROS.** The driver never calls `RobotEnable`/`Mode`; it
   relies on the operator putting the arm in **Automatic mode + enabled + speed>0 + web-UI
   released**. If not, the driver connects fine but every command is rejected with
   `ServoJ指令下发错误,错误码:99` (error 99) in the drivers log. The only witnesses are that log
   line and the FR web UI — there is no ROS status/enable topic to probe (unlike Fanuc/Kinova).
3. **This arm has a real admittance controller** (`joint_trajectory_admittance_controller`,
   active at startup). Unlike the CRX/Kinova plain-JTC benches, `jtac` / `Execute MTC Solution`
   work natively — the `ConvertMtcSolution + FJT` workaround is NOT needed here.

---

## 1. Hardware / network facts (from workspace README + Fairino manual)

| Item | Value |
|---|---|
| Robot controller default IP | `192.168.58.2` (debug/button-box Ethernet port) |
| Host static IP | `192.168.58.100/24`, **no gateway** (direct robot link) |
| FR web interface | `http://192.168.58.2`, default login `admin` / `123` |
| SDK transport | XML-RPC over TCP to the controller (`RPC(ip)` in the driver) |
| Command | `ServoJ` position stream @ **125 Hz** (8 ms cmdT). Faster → error 14. |
| Joints | `j1..j6`; tip link `wrist3_link`, flange `tool0` (z+0.101, roll π) |
| Controller SW | driver headers target robot SW **V3.8.3** (min V3.7.1 per driver README) |

Network shape matches the IQ9 skill's decided pattern exactly: **WiFi (`wlp1s0`) carries
LAN/internet; the single Ethernet port (`end0`) is the dedicated point-to-point robot link,
static, no gateway.** Never run FR driver traffic over WiFi (jitter trips the JTC/JTAC path
tolerance). Note the FR subnet is `192.168.58.x`, NOT the `192.168.1.x` used for the Kinova/UR
benches — set `end0` to `192.168.58.100/24`.

### Enable-chain prep on the FR web UI (do BEFORE launching the driver)
1. **Automatic mode** (circular-arrows icon → "Click to switch modes" until "Automatic mode";
   or physical key switch to auto). EOA LED color tracks mode.
2. **Enable the robot** (⚡ top-left) so drives leave `Stopped`. Clear any fault (⚠); drag-teach off.
3. **Global speed > 0** (mode panel %). At 0% the arm won't move even in Auto. Set 15–50%.
4. **Close the web UI** — the controller gives motion control to ONE client; the web pendant
   holding control blocks the SDK stream. Close the tab, then start the driver.

Error 99 clears once all four are set. This is the Fairino instance of the generic
"connects but won't initialize / enable-chain" playbook — triage screen-first on the web UI.

---

## 2. Workspace anatomy (`moveit_pro_fairino_ws`)

- `fairino_mock` — mock ros2_control (`mock_components/GenericSystem`). **This is the
  calibration/ladder/dry-run target** — runs on arm64 with no arm, no libfairino needed.
  Holds the SRDF, joint limits, kinematics, controllers, demo objective + demo waypoints.
- `fairino_hw` — `based_on_package: fairino_mock`, flips to the real
  `fairino_hardware/FairinoHardwareInterface` plugin, sets `robot_ip: 192.168.58.2`.
  `robot_driver_persist_launch_file` is intentionally **blank.launch.py** — the driver is an
  **in-process ros2_control system plugin, NOT a separate driver node**. (The `ros2_cmd_server`
  node in `robot_drivers.launch.py` is commented out / unused by the Pro config.)
- `fairino_hw` ships an **intentionally EMPTY waypoints file** so demo poses can't be driven on
  real hardware. **Teach known-safe waypoints in the UI before `Move to Waypoint` works on HW.**
- Driver submodule: `src/external_dependencies/frcobot_ros2` (PickNik fork, pinned SDK **2.2.3**).
  Real vendor upstream is `FAIR-INNOVATION/frcobot_ros2` (SDK currently 3.9.8).

### Controllers (`fairino_mock/config/control/ros2_controllers.yaml`)
- `update_rate: 125` Hz (matches driver's 8 ms ServoJ; do not raise).
- Active at startup: `joint_state_broadcaster`, `joint_trajectory_admittance_controller`.
- Inactive: `velocity_force_controller`, `joint_velocity_controller`, `joint_trajectory_controller`.
- JTC and JTAC **share the position command interface — only one active at a time.** Stock JTC
  is loaded inactive purely to compare path-tracking error against the admittance controller.

### Driver behavior (from `fairino_hardware_interface.cpp`)
- `on_activate`: `RPC(ip)` connect (200 ms settle) → `GetActualJointPosDegree` → sync
  command=state. **Fails activation** (returns ERROR) if RPC fails ("SDK连接失败/check port")
  or initial joint read fails ("读取初始关节角度错误"). A failed RPC = wrong IP / port busy /
  another client connected.
- `read`: `GetActualJointPosDegree`. `write`: `ServoJ` @ 8 ms.
- Does **not** call `RobotEnable`/`Mode` — enable-chain is operator responsibility (see §1).
- `on_deactivate`: `StopMotion` + `CloseRPC`.

---

## 3. THE arm64 blocker + fix path (do this first on hardware day)

`libfairino.so.2.2.3` in the PickNik submodule is `ELF x86-64`. On arm64:
`/usr/bin/ld: ... libfairino.so: error adding symbols: file in wrong format`.

**Known-good fix** (vendor issue FAIR-INNOVATION/frcobot_ros2 #21, confirmed working on
Raspberry Pi + Jetson): the separate repo **`FAIR-INNOVATION/fairino-cpp-sdk`** ships
precompiled aarch64 libs under `linux/libfairino/lib/` as `arm3399.zip / arm3568.zip /
arm3588.zip` (+ `x86.zip`). These are Rockchip board names but the ELFs are generic aarch64 —
one of them should load on the QCS9075.

**Procedure to prep (do on the IQ9):**
1. `git clone https://github.com/FAIR-INNOVATION/fairino-cpp-sdk`
2. Unzip an arm variant, `file` the `.so` → confirm `ELF 64-bit LSB ... aarch64`.
3. Replace the libs in `frcobot_ros2/fairino_hardware/libfairino/lib/`
   (CMake links `libfairino.so.2.2.3` + `.so.2` + `.so` symlinks; keep the same soname chain).
4. `moveit_pro build all` (NOT `build user_workspace` — a new/changed native lib needs the
   Docker image's rosdep pass; ~16 min on the EVK).
5. Verify the symbol landed: `nm -D <installed libfairino> | head` and that
   `FairinoHardwareInterface` loads in the drivers log.

**VERSION GAP — CHECKED 2026-08-23, VERDICT: CLEAN SWAP.** The cpp-sdk aarch64 lib is
`libfairino.so.2.3.8`; the PickNik submodule bundles `libfairino.so.2.2.3`. Compared them
directly (cpp-sdk `linux/libfairino/` cloned to `~/workspace/fairino-cpp-sdk`):
  - **Same ABI major:** both carry soname `libfairino.so.2` → same major version line, drop-in.
  - **Struct layouts identical:** `JointPos`, `DescPose`, `ExaxisPos` (the types the driver
    passes by pointer) are byte-for-byte the same — only constructor bodies/comments differ.
  - **All called functions present with matching signatures:** `RPC`, `CloseRPC`, `Mode`,
    `GetActualJointPosDegree`, `ServoJ`, `StopMotion`, `RobotEnable`. The **only** change is
    `ServoJ` gained a trailing **defaulted** arg (`int comType = 0`) → source-compatible, the
    driver's existing call still compiles unchanged.
  - Headers are CRLF in the SDK (grep with `tr -d '\r'`).
  Conclusion: swap the aarch64 `.so.2.3.8` into `fairino_hardware/libfairino/lib/`, keep the
  `.so` → `.so.2` → `.so.2.3.8` symlink chain, update the CMake filename ref if it pins
  `2.2.3`, then `moveit_pro build all`. No header bump or PickNik-fork rebuild needed.
  (Three arm zips exist — arm3399/3568/3588, Rockchip board names but generic aarch64 ELFs;
  any should load on the QCS9075. Pick one on the bench and confirm the drivers log shows the
  plugin loaded.)

Everything else (`mock` config, MoveIt config, objectives) is arch-independent and builds fine
on arm64 (confirmed pattern: ur_ws built natively on this EVK).

---

## 4. Bring-up ladder mapped to Fairino (what to check, in order)

Reusing the 9-rung ladder. Fairino-specific notes per rung:

- **Rung -1 (static lint):** joint names `j1..j6`, group `manipulator`, tip `wrist3_link`.
- **Rung 0 (containers/config):** confirm active config is `fairino_hw` (or `fairino_mock` for
  dry runs). `docker exec ...drivers env | grep MOVEIT_CONFIG_PACKAGE`.
- **Rung 1 (network):** `end0` UP + carrier, `192.168.58.100/24`; `ping 192.168.58.2` replies
  with a foreign MAC (`ip neigh`). Port check: XML-RPC TCP to the controller open.
- **Rung 2 (driver alive):** the in-process plugin activates. FAIL signatures in drivers log:
  `SDK连接失败` (RPC failed — wrong IP / port busy / another client) or
  `读取初始关节角度错误` (initial joint read failed). NOTE: because it's in-process, a driver
  "crash" = ros2_control_node down, same class as the Fanuc/Kinova exit-on-disconnect bug —
  watch for it if the controller reboots mid-session.
- **Rungs 3-5 (interfaces / controllers / joint_states):** `joint_state_broadcaster` +
  `joint_trajectory_admittance_controller` active by design. `/joint_states` at ~125 Hz.
- **Rung 6 (enable-chain / vendor status):** ⚠ **BLIND SPOT** — no ROS status topic exists.
  The only inhibit witness is the `error 99` log line on write + the FR web UI. Add a log-grep
  for `错误码:99` / `error code 99` to the rung-6 check. Screen-first triage on `http://192.168.58.2`.
- **Rung 7 (action plumbing):** arm controller action server is
  `/joint_trajectory_admittance_controller/follow_joint_trajectory` (NOT the plain JTC name the
  ladder defaults to). Pass `--arm-controller joint_trajectory_admittance_controller`, or
  activate the inactive `joint_trajectory_controller` for a plain-JTC twitch (remember they share
  the command interface — deactivate JTAC first).
- **Rung 8 (motion twitch):** approval-gated, one joint, encoder+camera verified per hard rule 1.
  The gated tree must `SwitchController` the arm controller active first (JTAC is active at
  startup here, so likely fine — [VERIFY ON HW]). Start global speed low (15%) on the pendant.

---

## 5. Motion-execution pattern (differs from prior benches — good news)

This arm HAS `joint_trajectory_admittance_controller`, so the shipped
`Move to Waypoint` / `Cycle Between Waypoints` objectives run natively with
`execution_pipeline="jtac"` and `controller_action_server=
/joint_trajectory_admittance_controller/follow_joint_trajectory`. **No `ConvertMtcSolution +
ExecuteFollowJointTrajectory` bridge needed** (that was a plain-JTC-arm workaround). If you ever
switch to the plain JTC for tolerance comparison, deactivate JTAC first (shared command interface).

---

## 6. IQ9 Dragonwing target notes (from qualcomm-dragonwing-evk skill)

- Board is aarch64, Ubuntu 24.04 server, passwordless sudo for `ubuntu`; Docker via
  get.docker.com; MoveIt Pro deb is arch-`any` — match the laptop's Pro version + reuse the
  license key.
- IQ9-02 is **NOT on tailscale** (by design) and not reachable from here now. On the bench:
  serial console is the rescue path (FT4232H quad UART, console usually on ttyUSB1); join WiFi
  via `nmcli`; then SSH.
- Moving the workspace onto the board: `rsync -az --exclude=build --exclude=install
  --exclude=log <ws>/ ubuntu@<board>:<ws>/` (carries submodule files + uncommitted edits; board
  rebuilds natively). **After the arm64 libfairino swap, this is how the fixed workspace goes over.**
- Web UI on headless board: `DISPLAY=:99 moveit_pro run -c fairino_hw --no-browser -y` inside
  tmux; serves at `http://<board-ip>/`.
- Set the active workspace in `~/.config/moveit_pro/moveit_pro_config.9.yaml`
  (`MOVEIT_HOST_USER_WORKSPACE` + `MOVEIT_CONFIG_PACKAGE`) — a copied laptop config carries the
  laptop's path and will silently no-op the build.

---

## 7. Open questions for the user / to resolve on hardware

1. Which aarch64 libfairino to use, given the 2.2.3-vs-3.9.x version gap (see §3 options)?
2. Confirm the arm is an **FR5** (workspace is FR5-only; driver has configs for FR3/5/10/16/20/30
   if it's a different model).
3. Confirm robot controller software version ≥ V3.7.1 (driver min) — ideally V3.8.3 to match headers.
4. Is IQ9-02 already flashed + Docker + Pro installed, or does that bring-up come first?
5. Robot's real IP if not the `192.168.58.2` default (some cells re-IP the controller).
