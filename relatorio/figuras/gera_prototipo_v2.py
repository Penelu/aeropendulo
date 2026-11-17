"""Concept drawing of the next prototype (v2): light PLA rod with only the IMU
and the fan; Nucleo, driver and supply off the rod, linked by a thin wire.

    python relatorio/figuras/gera_prototipo_v2.py   ->  relatorio/figuras/prototipo_v2.png
"""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Arc, FancyArrowPatch, Circle, Rectangle, Polygon
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prototipo_v2.png')
TILT = np.radians(-8)            # rod tilt in the y-z plane (phi < 0: theta < 90 deg)
ROD_H, FAN_H, IMU_H = 0.24, 0.215, 0.035   # heights along the rod (m)
PLA, FAN, IMU, DARK = '#d9d4c7', '#3a9d5d', '#2f5fb3', '#333333'


def tilt(p):
    """Rotate points (N x 3) about the pivot axis (x) by TILT."""
    c, s = np.cos(TILT), np.sin(TILT)
    r = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    return p @ r.T


def box(c, size):
    """Faces of an axis-aligned box centred at c (in rod coordinates)."""
    dx, dy, dz = np.array(size) / 2
    v = np.array([[x, y, z] for x in (-dx, dx) for y in (-dy, dy) for z in (-dz, dz)]) + c
    idx = [[0, 1, 3, 2], [4, 5, 7, 6], [0, 1, 5, 4], [2, 3, 7, 6], [0, 2, 6, 4], [1, 3, 7, 5]]
    return [v[i] for i in idx]


def add(ax, faces, color, alpha=1.0, rod=True):
    faces = [tilt(f) if rod else f for f in faces]
    ax.add_collection3d(Poly3DCollection(faces, facecolor=color, edgecolor='k',
                                         linewidth=0.3, alpha=alpha))


def view_3d(ax):
    # floor
    g = np.linspace(-0.12, 0.32, 12)
    for v in g:
        ax.plot([v, v], [-0.12, 0.12], [0, 0], color='#dddddd', lw=0.5)
    for v in np.linspace(-0.12, 0.12, 7):
        ax.plot([-0.12, 0.32], [v, v], [0, 0], color='#dddddd', lw=0.5)
    # base crossbar and the two rounded feet (pivot axis = x)
    add(ax, box([0, 0, -0.004], [0.13, 0.02, 0.008]), DARK, rod=False)
    u, w = np.mgrid[0:2 * np.pi:16j, 0:np.pi:8j]
    for x in (-0.05, 0.05):
        ax.plot_surface(x + 0.008 * np.cos(u) * np.sin(w), 0.008 * np.sin(u) * np.sin(w),
                        0.006 + 0.008 * np.cos(w), color='#888888', linewidth=0)
    # rod
    add(ax, box([0, 0, ROD_H / 2 + 0.006], [0.014, 0.006, ROD_H]), PLA)
    # IMU near the pivot
    add(ax, box([0, 0.006, IMU_H], [0.022, 0.004, 0.016]), IMU)
    # fan: duct ring + three blades, axis along y (thrust in the swing plane)
    t = np.linspace(0, 2 * np.pi, 40)
    r = 0.0375
    for y in (0.004, 0.018):
        ring = np.c_[r * np.cos(t), np.full_like(t, y), FAN_H + r * np.sin(t)]
        ring = tilt(ring)
        ax.plot(ring[:, 0], ring[:, 1], ring[:, 2], color=FAN, lw=2.2)
    for k in range(3):
        a = k * 2 * np.pi / 3
        blade = np.array([[0, 0.011, FAN_H],
                          [0.033 * np.cos(a - 0.25), 0.009, FAN_H + 0.033 * np.sin(a - 0.25)],
                          [0.033 * np.cos(a + 0.25), 0.013, FAN_H + 0.033 * np.sin(a + 0.25)]])
        add(ax, [blade], '#7a7a7a')
    add(ax, box([0, 0.011, FAN_H], [0.012, 0.012, 0.012]), DARK)
    # thin wire: fan and IMU down the rod, leaves at pivot height along the pivot axis
    wire = tilt(np.array([[0.006, -0.004, FAN_H], [0.006, -0.004, IMU_H], [0.006, -0.004, 0.012]]))
    ax.plot(wire[:, 0], wire[:, 1], wire[:, 2], color='#c0392b', lw=1.2)
    x = np.linspace(0.006, 0.22, 30)
    ax.plot(x, np.full_like(x, wire[-1, 1]), 0.012 - 0.010 * np.sin(np.pi * (x - 0.006) / 0.214) ** 2,
            color='#c0392b', lw=1.2)
    # external box: Nucleo + driver + supply
    add(ax, box([0.255, 0, 0.02], [0.07, 0.05, 0.04]), '#1f1f1f', rod=False)
    ax.text(0.255, 0, 0.065, 'Nucleo + driver\n+ fonte (fora da haste)', ha='center', fontsize=7)
    ax.text(0.04, -0.02, IMU_H + 0.01, 'IMU', color=IMU, fontsize=8, fontweight='bold')
    ax.text(0.04, 0.0, FAN_H + 0.05, 'ventilador', color=FAN, fontsize=8, fontweight='bold')
    ax.text(0.12, 0.03, 0.002, 'fio fino', color='#c0392b', fontsize=7)
    ax.text(-0.02, 0.0, 0.12, 'haste leve\n(PLA ou peças\ntipo Lego)', fontsize=7, ha='right')

    ax.set_xlim(-0.12, 0.32); ax.set_ylim(-0.12, 0.12); ax.set_zlim(0, 0.27)
    ax.set_box_aspect((0.44, 0.24, 0.27))
    ax.view_init(elev=18, azim=-58)
    ax.set_axis_off()
    ax.set_title('(a) vista 3D', fontsize=10)


def view_side(ax):
    """Swing plane (y-z): angle, thrust in both directions, heights."""
    c, s = np.cos(TILT), np.sin(TILT)
    top = np.array([-s, c])                       # rod direction in (y, z)
    ax.add_patch(Rectangle((-0.09, -0.012), 0.18, 0.012, color='#eeeeee'))
    ax.plot([-0.09, 0.09], [0, 0], color='k', lw=1)
    ax.add_patch(Circle((0, 0.008), 0.008, color='#888888'))
    rod = np.array([[0, 0.008], (0.008 * np.array([0, 1]) + ROD_H * top)])
    ax.plot(rod[:, 0], rod[:, 1], color='#b8b0a0', lw=6, solid_capstyle='butt')
    n = np.array([c, s])                          # normal to the rod, pointing away from vertical
    imu = IMU_H * top + 0.006 * n
    ax.add_patch(Polygon([imu + a * 0.008 * top + b * 0.003 * n for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))],
                         color=IMU))
    ax.text(*(imu + 0.012 * n), 'IMU', fontsize=7, color=IMU, va='center')
    fan = FAN_H * top
    ends = np.array([fan - 0.0375 * top, fan + 0.0375 * top]) - 0.004 * n
    ax.plot(ends[:, 0], ends[:, 1], color=FAN, lw=4)  # fan disc seen edge-on
    cg = 0.07 * top
    ax.plot(*cg, 'ko', ms=4)
    ax.annotate('CG', cg, xytext=(-0.06, cg[1] + 0.015), fontsize=8, arrowprops=dict(arrowstyle='-', lw=0.5))
    # thrust both ways: strong (back to vertical) and weak reverse
    ax.add_patch(FancyArrowPatch(fan, fan - 0.075 * n, arrowstyle='-|>', mutation_scale=12, color='#c0392b', lw=2))
    ax.add_patch(FancyArrowPatch(fan, fan + 0.035 * n, arrowstyle='-|>', mutation_scale=10, color='#e67e22', lw=1.6))
    ax.text(*(fan - 0.13 * n + [0, 0.012]), '$F>0$\n(sentido forte)', fontsize=7, color='#c0392b')
    ax.text(*(fan + 0.04 * n + [0, 0.012]), '$F<0$\n(reverso)', fontsize=7, color='#e67e22')
    # gravity at the CG, vertical, angles
    ax.add_patch(FancyArrowPatch(cg, cg - [0, 0.03], arrowstyle='-|>', mutation_scale=10, color='k', lw=1))
    ax.text(cg[0] + 0.006, cg[1] - 0.03, '$mg$', fontsize=8)
    ax.plot([0, 0], [0.008, 0.27], 'k--', lw=0.6)
    ax.add_patch(Arc((0, 0.008), 0.30, 0.30, theta1=90 + np.degrees(TILT), theta2=90, lw=1))
    ax.text(0.008, 0.17, r'$\phi$', fontsize=9)
    ax.add_patch(Arc((0, 0.008), 0.11, 0.11, theta1=0, theta2=90 + np.degrees(TILT), lw=1))
    ax.text(0.045, 0.035, r'$\theta$', fontsize=9)
    # heights
    for hgt, lbl in ((FAN_H, '$L$'), (0.07, '$h$')):
        ax.annotate('', xy=(0.10, 0.008 + hgt), xytext=(0.10, 0.008),
                    arrowprops=dict(arrowstyle='<->', lw=0.7))
        ax.text(0.105, 0.008 + hgt / 2, lbl, fontsize=8)
    ax.text(0.0, -0.035, 'pivô (eixo dos apoios)', ha='center', fontsize=7)
    ax.set_xlim(-0.14, 0.14); ax.set_ylim(-0.045, 0.28)
    ax.set_aspect('equal'); ax.axis('off')
    ax.set_title('(b) plano de tombamento', fontsize=10)


fig = plt.figure(figsize=(9.5, 4.6), dpi=200)
view_3d(fig.add_subplot(1, 2, 1, projection='3d'))
view_side(fig.add_subplot(1, 2, 2))
fig.tight_layout()
fig.savefig(OUT, bbox_inches='tight')
print('salvo em', OUT)
