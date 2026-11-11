# -*- coding: utf-8 -*-
"""
Aeropendulo - PC monitor (serial port of the NUCLEO-L476RG).

Shows the rod angle, the reference and the control signal in real time,
sends commands to the firmware and measures overshoot / settling time
after each reference step or "toque" (push).

Usage:
    pip install pyserial matplotlib
    python aeropendulo_app.py              # auto-detect the Nucleo port
    python aeropendulo_app.py COM5         # or give the port
    python aeropendulo_app.py --demo       # simulated rod, no hardware
"""
import csv
import math
import sys
import threading
import time
from collections import deque

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button, TextBox

WINDOW_S = 15.0          # seconds shown on screen
BAND_DEG = 2.0           # settling band (+/- deg)
BAUD = 115200


# ---------------------------------------------------------------------------
# Serial link (real board or simulated rod)
# ---------------------------------------------------------------------------
def open_port(name=None):
    import serial
    from serial.tools import list_ports
    if name is None:
        for p in list_ports.comports():
            if p.vid == 0x0483:            # STMicroelectronics ST-LINK
                name = p.device
                break
    if name is None:
        sys.exit("Nucleo not found. Give the port: python aeropendulo_app.py COM5")
    print("Opening", name)
    return serial.Serial(name, BAUD, timeout=0.1)


class DemoPort:
    """Simulated rod + firmware, same telemetry format (for testing the app)."""

    def __init__(self):
        self.lines = deque()
        self.run = False
        self.ref, self.kp, self.ki, self.kd = 90.0, 0.12, 0.30, 0.010
        self.i_min, self.i_max = -0.4, 0.4
        self.phi, self.w, self.f, self.i = 0.0, 0.0, 0.0, 0.0
        self.push_until = 0.0
        self.t0 = time.time()
        self.last = self.t0
        threading.Thread(target=self._loop, daemon=True).start()

    def write(self, data):
        cmd = data.decode().split()
        if not cmd:
            return
        if cmd[0] == "run":
            self.run, self.i = True, 0.0
        elif cmd[0] == "stop":
            self.run = False
        elif cmd[0] == "ref":
            self.ref = float(cmd[1])
        elif cmd[0] == "pid":
            self.kp, self.ki, self.kd = map(float, cmd[1:4])
        elif cmd[0] == "ilim":
            self.i_min, self.i_max = map(float, cmd[1:3])
        elif cmd[0] == "push":                       # demo only: simulated touch
            self.push_until = time.time() + 0.2
        self.lines.append(f"> {data.decode().strip()}\r\n".encode())

    def readline(self):
        while not self.lines:
            time.sleep(0.005)
        return self.lines.popleft()

    def _loop(self):
        # same model as the anti-windup article, u normalised to +/-1
        m, h, L, J, b, g, tau, fmax = 0.145, 0.069, 0.212, 1.1e-3, 5e-4, 9.81, 0.03, 0.25
        dt, k = 0.005, 0
        while True:
            time.sleep(dt)
            theta = 90 + math.degrees(self.phi)
            u = 0.0
            if self.run:
                e = self.ref - theta
                self.i = min(max(self.i + self.ki * dt * e, self.i_min), self.i_max)
                u = self.kp * e + self.i - self.kd * math.degrees(self.w)
                u = min(max(u, -0.4), 1.0)           # reverse thrust is weaker
                if abs(theta - 90) > 30:
                    self.run = False
            td = -0.024 if time.time() < self.push_until else 0.0
            for _ in range(10):
                acc = (m * g * h * math.sin(self.phi) - b * self.w + L * self.f + td) / J
                self.f += dt / 10 * (u * fmax - self.f) / tau
                self.w += dt / 10 * acc
                self.phi += dt / 10 * self.w
                if abs(self.phi) > math.radians(24):
                    self.phi, self.w = math.copysign(math.radians(24), self.phi), 0.0
            k += 1
            if k % 4 == 0:
                t_ms = int((time.time() - self.t0) * 1000)
                self.lines.append(
                    f"D,{t_ms},{theta:.2f},{self.ref:.2f},{u:.3f},{self.i:.3f},{u:.3f},"
                    f"{theta:.2f},{math.degrees(self.w):.1f}\r\n".encode())


# ---------------------------------------------------------------------------
# Data and metrics
# ---------------------------------------------------------------------------
class Data:
    def __init__(self):
        self.lock = threading.Lock()
        self.t, self.theta, self.ref, self.u, self.i, self.acc = ([] for _ in range(6))
        self.imu = deque(maxlen=400)          # (t, theta_acc, theta_gyro, theta)
        self.event_t = None                   # last ref step or push
        self.event_ref = None

    def add_d(self, f):
        t = int(f[1]) / 1000.0
        ref = float(f[3])
        with self.lock:
            if self.ref and abs(ref - self.ref[-1]) > 0.01:
                self.mark_event(t, ref)
            self.t.append(t)
            self.theta.append(float(f[2]))
            self.ref.append(ref)
            self.u.append(float(f[4]))
            self.i.append(float(f[5]))
            self.acc.append(float(f[7]))

    def mark_event(self, t=None, ref=None):
        self.event_t = t if t is not None else (self.t[-1] if self.t else 0.0)
        self.event_ref = ref if ref is not None else (self.ref[-1] if self.ref else 90.0)

    def metrics(self):
        """Overshoot and settling time after the last event."""
        if self.event_t is None:
            return "sem evento: mude a referência ou marque um toque"
        idx = [k for k, t in enumerate(self.t) if t >= self.event_t]
        if len(idx) < 10:
            return "medindo..."
        ref = self.event_ref
        y = [self.theta[k] for k in idx]
        tt = [self.t[k] for k in idx]
        dev = max(y, key=lambda v: abs(v - ref))
        out = [k for k, v in enumerate(y) if abs(v - ref) > BAND_DEG]
        if not out:
            ts = "0.00 s"
        elif out[-1] == len(y) - 1:
            ts = "ainda fora da faixa"
        else:
            ts = f"{tt[out[-1]] - self.event_t:.2f} s"
        return (f"ref {ref:.1f}°   desvio máx {dev - ref:+.1f}°   "
                f"acomodação (±{BAND_DEG:.0f}°) {ts}   erro atual {y[-1] - ref:+.2f}°")

    def save_csv(self, name):
        with self.lock, open(name, "w", newline="", encoding="utf-8") as fp:
            w = csv.writer(fp)
            w.writerow(["t_s", "theta_deg", "ref_deg", "u", "I", "theta_acc_deg"])
            w.writerows(zip(self.t, self.theta, self.ref, self.u, self.i, self.acc))
        print("saved", name)


def reader(port, data):
    while True:
        try:
            line = port.readline().decode(errors="ignore").strip()
        except Exception as exc:          # unplugged cable, etc.
            print("serial error:", exc)
            return
        if not line:
            continue
        f = line.split(",")
        try:
            if f[0] == "D" and len(f) >= 9:
                data.add_d(f)
            elif f[0] == "I" and len(f) >= 10:
                with data.lock:
                    data.imu.append((time.time(), float(f[7]), float(f[8]), float(f[9])))
            else:
                print(line)               # console messages from the firmware
        except ValueError:
            print(line)


# ---------------------------------------------------------------------------
# Window
# ---------------------------------------------------------------------------
def main():
    demo = "--demo" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    port = DemoPort() if demo else open_port(args[0] if args else None)
    data = Data()
    threading.Thread(target=reader, args=(port, data), daemon=True).start()

    def send(cmd):
        port.write((cmd.strip() + "\n").encode())

    fig = plt.figure(figsize=(11, 7))
    fig.canvas.manager.set_window_title("Aeropêndulo - monitor")
    ax1 = fig.add_axes([0.07, 0.50, 0.90, 0.40])
    ax2 = fig.add_axes([0.07, 0.24, 0.90, 0.20], sharex=ax1)
    l_th, = ax1.plot([], [], lw=1.6, label="θ (filtro)")
    l_acc, = ax1.plot([], [], lw=0.8, alpha=0.5, label="θ acelerômetro")
    l_ref, = ax1.plot([], [], "k--", lw=1, label="referência")
    l_u, = ax2.plot([], [], lw=1.2, label="u (comando)")
    l_i, = ax2.plot([], [], lw=1.2, label="I (integral)")
    ax1.set_ylabel("ângulo (graus)")
    ax2.set_ylabel("comando")
    ax2.set_xlabel("tempo (s)")
    ax1.legend(loc="upper left", fontsize=8)
    ax2.legend(loc="upper left", fontsize=8)
    ax1.grid(alpha=0.3)
    ax2.grid(alpha=0.3)
    ax2.set_ylim(-1.1, 1.1)
    info = fig.text(0.07, 0.94, "", fontsize=10)

    # controls
    widgets = []

    def button(x, label, action):
        b = Button(fig.add_axes([x, 0.04, 0.085, 0.05]), label)
        b.on_clicked(lambda _e: action())
        widgets.append(b)

    def step(delta):
        r = (data.ref[-1] if data.ref else 90.0) + delta
        send(f"ref {r:.1f}")

    def touch():
        data.mark_event()
        if demo:
            send("push")

    button(0.07, "Run", lambda: send("run"))
    button(0.165, "Stop", lambda: send("stop"))
    button(0.26, "Ref -10°", lambda: step(-10))
    button(0.355, "Ref 90°", lambda: send("ref 90"))
    button(0.45, "Ref +10°", lambda: step(+10))
    button(0.545, "Toque", touch)
    button(0.64, "Salvar CSV", lambda: data.save_csv(time.strftime("ensaio_%Y%m%d_%H%M%S.csv")))
    tb = TextBox(fig.add_axes([0.07, 0.11, 0.6, 0.05]), "cmd ", initial="")
    tb.on_submit(lambda text: (send(text), tb.set_val("")) if text.strip() else None)
    widgets.append(tb)
    fig.text(0.69, 0.125, "ex.: pid 0.03 0.05 0.004 | ilim -0.3 0.3 | imu | status",
             fontsize=8, color="0.4")

    def update(_frame):
        with data.lock:
            if data.imu and (not data.t or data.imu[-1][0] > time.time() - 1):
                # IMU test mode: compare accelerometer, gyro and filter
                t0 = data.imu[0][0]
                tt = [s[0] - t0 for s in data.imu]
                l_th.set_data(tt, [s[3] for s in data.imu])
                l_acc.set_data(tt, [s[1] for s in data.imu])
                l_ref.set_data(tt, [s[2] for s in data.imu])
                l_ref.set_label("θ giroscópio (integrado)")
                ax1.legend(loc="upper left", fontsize=8)
                ax1.set_xlim(max(0, tt[-1] - WINDOW_S), max(WINDOW_S, tt[-1]))
                ax1.relim()
                ax1.autoscale_view(scalex=False)
                info.set_text("Teste IMU: as três curvas devem coincidir ao inclinar a haste")
                return
            if not data.t:
                return
            if l_ref.get_label() != "referência":
                l_ref.set_label("referência")
                ax1.legend(loc="upper left", fontsize=8)
            tmax = data.t[-1]
            k0 = next((k for k, t in enumerate(data.t) if t >= tmax - WINDOW_S), 0)
            tt = data.t[k0:]
            l_th.set_data(tt, data.theta[k0:])
            l_acc.set_data(tt, data.acc[k0:])
            l_ref.set_data(tt, data.ref[k0:])
            l_u.set_data(tt, data.u[k0:])
            l_i.set_data(tt, data.i[k0:])
            ax1.set_xlim(tmax - WINDOW_S, tmax)
            lo = min(min(data.theta[k0:]), min(data.ref[k0:])) - 3
            hi = max(max(data.theta[k0:]), max(data.ref[k0:])) + 3
            ax1.set_ylim(lo, hi)
            info.set_text(data.metrics())

    _anim = FuncAnimation(fig, update, interval=100, cache_frame_data=False)
    plt.show()


if __name__ == "__main__":
    main()
