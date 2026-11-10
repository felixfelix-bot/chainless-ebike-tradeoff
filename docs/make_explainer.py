#!/usr/bin/env python3
"""Render the parallel-hybrid explainer figure used in the Signal reply.

Design notes: component callouts are small numbered badges placed in empty
space, with all explanation in a separate legend panel. This avoids leader
lines crossing each other or running over text -- the failure mode of the
first draft, which put long annotations across the wheels.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle
import numpy as np

GREEN = "#1f8a4c"
ORANGE = "#c2410c"
GREY = "#333333"
LIGHT = "#9ca3af"
BLUE = "#1d4ed8"
RED = "#b91c1c"
PURPLE = "#6d28d9"

fig = plt.figure(figsize=(16, 11), dpi=100)
fig.patch.set_facecolor("white")

# ---------------------------------------------------------------- bike panel
ax = fig.add_axes((0.005, 0.405, 0.60, 0.585))
ax.set_xlim(-3.15, 3.15)
ax.set_ylim(-0.32, 3.38)
ax.set_aspect("equal")
ax.axis("off")

R = 1.0
rear = np.array([-2.00, 1.00])
front = np.array([2.00, 1.00])
bb = np.array([-0.10, 0.42])
saddle = np.array([-0.88, 2.02])
head_top = np.array([1.48, 1.98])
head_bot = np.array([1.40, 1.56])

def wheel(c, r, motor=False):
    ax.add_patch(Circle(c, r, fill=False, lw=6, ec=GREY, zorder=2))
    ax.add_patch(Circle(c, r - 0.10, fill=False, lw=1.2, ec=LIGHT, zorder=2))
    for a in np.linspace(0, 2 * np.pi, 17)[:-1]:
        ax.plot([c[0], c[0] + (r - 0.10) * np.cos(a)],
                [c[1], c[1] + (r - 0.10) * np.sin(a)],
                lw=0.7, color=LIGHT, zorder=1)
    if motor:
        ax.add_patch(Circle(c, 0.36, fc="#fed7aa", ec=ORANGE, lw=3.0, zorder=4))
        ax.add_patch(Circle(c, 0.12, fc=GREY, ec=GREY, zorder=5))

wheel(front, R)
wheel(rear, R, motor=True)

for p0, p1 in [(bb, rear), (saddle, rear), (bb, saddle),
               (bb, head_bot), (saddle, head_top), (head_bot, front),
               (head_top, head_bot)]:
    ax.plot([p0[0], p1[0]], [p0[1], p1[1]], lw=7, color=GREY,
            solid_capstyle="round", zorder=3)

ax.add_patch(FancyBboxPatch((saddle[0] - 0.34, saddle[1] + 0.03), 0.62, 0.13,
                            boxstyle="round,pad=0.03", fc=GREY, ec=GREY, zorder=5))
ax.plot([head_top[0], head_top[0] + 0.05], [head_top[1], head_top[1] + 0.13],
        lw=5, color=GREY, zorder=4)
ax.plot([head_top[0] - 0.20, head_top[0] + 0.30], [head_top[1] + 0.15] * 2,
        lw=6, color=GREY, solid_capstyle="round", zorder=5)

# crank
ax.add_patch(Circle(bb, 0.30, fc="white", ec=GREY, lw=3.2, zorder=5))
ax.add_patch(Circle(bb, 0.06, fc=GREY, zorder=6))
for ang in (0.9, 0.9 + np.pi):
    end = bb + 0.46 * np.array([np.cos(ang), np.sin(ang)])
    ax.plot([bb[0], end[0]], [bb[1], end[1]], lw=4, color=GREY,
            solid_capstyle="round", zorder=6)
    ax.plot([end[0] - 0.11, end[0] + 0.11], [end[1], end[1]], lw=6, color=GREY,
            solid_capstyle="round", zorder=7)

# chain
cr_r, cog_r = 0.30, 0.14
ax.plot([bb[0], rear[0]], [bb[1] + cr_r, rear[1] + cog_r], lw=3.2, color=GREEN, zorder=4)
ax.plot([bb[0], rear[0]], [bb[1] - cr_r, rear[1] - cog_r], lw=3.2, color=GREEN, zorder=4)
ax.add_patch(Circle(rear, cog_r, fc="none", ec=GREEN, lw=3.2, zorder=6))

# battery
d = head_bot - bb
ang = np.degrees(np.arctan2(d[1], d[0]))
centre = bb + 0.52 * d
bw, bh = 0.90, 0.32
ax.add_patch(Rectangle((centre[0] - bw / 2, centre[1] - bh / 2), bw, bh,
                       angle=ang, rotation_point=(centre[0], centre[1]),
                       fc="#dbeafe", ec=BLUE, lw=2.8, zorder=7))
ax.text(centre[0], centre[1], "BATTERY", ha="center", va="center",
        fontsize=10.5, fontweight="bold", color=BLUE, rotation=ang, zorder=8)

# controller
ctrl = np.array([0.30, 1.12])
ax.add_patch(FancyBboxPatch((ctrl[0] - 0.29, ctrl[1] - 0.16), 0.58, 0.32,
                            boxstyle="round,pad=0.02", fc="#ffedd5", ec=ORANGE,
                            lw=2.8, zorder=7))
ax.text(ctrl[0], ctrl[1], "CTRL", ha="center", va="center",
        fontsize=10, fontweight="bold", color="#7c2d12", zorder=8)

# torque sensor ring
ax.add_patch(Circle(bb, 0.46, fill=False, ec=PURPLE, lw=2.4, ls=(0, (3, 2)), zorder=6))

# --- power flow arrows (short, local, no text crossing)
def arrow(p0, p1, colour, lw=3.0, rad=0.0):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=24,
                                 lw=lw, color=colour, zorder=9,
                                 connectionstyle=f"arc3,rad={rad}"))

arrow((-0.10, 2.52), (-0.10, 1.18), GREEN, lw=3.4)
arrow((0.12, 0.80), (rear[0] + 0.24, rear[1] + 0.30), GREEN, rad=-0.20, lw=3.4)
arrow((centre[0] - 0.05, centre[1] - 0.30), (ctrl[0] + 0.14, ctrl[1] + 0.20), ORANGE, lw=3.0)
arrow((ctrl[0] - 0.32, ctrl[1] - 0.10), (rear[0] + 0.42, rear[1] - 0.06), ORANGE, rad=0.14, lw=3.0)

ax.text(-0.10, 2.86, "YOUR LEGS", fontsize=13.5, fontweight="bold",
        color=GREEN, ha="center", va="center")
ax.text(-0.10, 3.13, "your power, any cadence you like", fontsize=11,
        color=GREY, ha="center", va="center")

# --- numbered badges
def badge(x, y, n, colour):
    ax.add_patch(Circle((x, y), 0.145, fc=colour, ec="white", lw=2.0,
                        zorder=12, clip_on=False))
    ax.text(x, y - 0.005, str(n), fontsize=11.5, fontweight="bold", color="white",
            ha="center", va="center", zorder=13)

badge(-0.72, 0.10, 1, GREY)
badge(-0.62, 0.63, 2, GREEN)
badge(0.40, 0.10, 3, PURPLE)
badge(1.05, 1.38, 4, BLUE)
badge(0.66, 1.12, 5, ORANGE)
badge(-1.52, 1.45, 6, ORANGE)

# ------------------------------------------------------------- legend panel
axl = fig.add_axes((0.615, 0.405, 0.375, 0.585))
axl.set_xlim(0, 1)
axl.set_ylim(0, 1)
axl.axis("off")

axl.text(0.0, 0.985, "THE PARTS, AND WHAT EACH DOES", fontsize=14,
         fontweight="bold", color=GREY, ha="left", va="top")

entries = [
    (1, GREY, "Cranks and pedals",
     "Where you push. Nothing downstream is geared\nto the wheel, so you pick your own cadence."),
    (2, GREEN, "Chain",
     "Still there, still mechanical. It now carries ONLY\nyour leg power, at about 96%. That is the point."),
    (3, PURPLE, "Torque sensor",
     "At the bottom bracket. Measures how hard you\npush, so the motor knows how much to add."),
    (4, BLUE, "Battery  (480 Wh LiFePO4, 2.7 kg)",
     "Holds its voltage flat as it empties, unlike a\ncapacitor bank. Recharged by mains and by regen."),
    (5, ORANGE, "Controller",
     "The motor's brain: battery DC <-> 3-phase AC,\nand back again when the motor is generating."),
    (6, ORANGE, "Direct-drive hub motor",
     "Built into the rear hub. Drives you; backwards it\nis a generator, which is what regen braking is."),
]

y = 0.905
for n, colour, name, desc in entries:
    axl.add_patch(Circle((0.045, y - 0.012), 0.032, fc=colour, ec="white",
                         lw=1.6, zorder=5, clip_on=False))
    axl.text(0.045, y - 0.017, str(n), fontsize=11, fontweight="bold",
             color="white", ha="center", va="center", zorder=6)
    axl.text(0.100, y, name, fontsize=12.5, fontweight="bold", color=colour,
             ha="left", va="top")
    axl.text(0.100, y - 0.046, desc, fontsize=10.2, color=GREY,
             ha="left", va="top", linespacing=1.42)
    y -= 0.128

axl.text(0.0, 0.018,
         "Parallel hybrid: your legs and the motor both drive the wheel,\n"
         "side by side. Neither has to pass through the other.",
         fontsize=10.8, color=BLUE, ha="left", va="bottom",
         fontweight="bold", linespacing=1.5)

# ------------------------------------------------------- efficiency panel
ax2 = fig.add_axes((0.045, 0.045, 0.585, 0.295))
labels = [
    "Chain only (your legs)",
    "PARALLEL  your legs -> wheel",
    "PARALLEL  battery -> wheel",
    "SERIES  everything in line",
    "Car alternator series",
]
vals = [96.1, 96.1, 80.0, 61.3, 39.2]
cols = [GREEN, GREEN, ORANGE, RED, RED]
ypos = np.arange(len(vals))[::-1]

ax2.barh(ypos, vals, color=cols, height=0.60, alpha=0.92)
for yi, v, c in zip(ypos, vals, cols):
    ax2.text(v + 1.4, yi, f"{v:.1f}%", va="center", ha="left",
             fontsize=13, fontweight="bold", color=c)

ax2.set_yticks(ypos)
ax2.set_yticklabels(labels, fontsize=10.8)
ax2.set_xlim(0, 108)
ax2.set_xlabel("efficiency, pedals (or battery) to road", fontsize=11)
ax2.axvline(96.1, color=GREY, ls=":", lw=1.4, alpha=0.55)
ax2.grid(axis="x", alpha=0.25, lw=0.8)
ax2.set_axisbelow(True)
for s in ("top", "right"):
    ax2.spines[s].set_visible(False)
ax2.set_title("Why parallel escapes the tax: the two paths are not in series",
              fontsize=13.5, fontweight="bold", loc="left", pad=10)

fig.text(0.660, 0.300, "Blended, if the motor supplies\nhalf the wheel power:",
         fontsize=11, color=GREY, ha="left", va="top")
fig.text(0.660, 0.232, "0.5/0.961 + 0.5/0.80", fontsize=12.5, fontweight="bold",
         color=GREY, ha="left", va="top", family="monospace")
fig.text(0.660, 0.186, "= 1.145", fontsize=12.5, fontweight="bold",
         color=GREY, ha="left", va="top", family="monospace")
fig.text(0.660, 0.128, "->  87% blended, not 61%", fontsize=13.5,
         fontweight="bold", color=BLUE, ha="left", va="top")
fig.text(0.660, 0.062,
         "Your watts keep the chain's 96%.\nOnly the battery's watts pay the\nmotor losses. Neither pays a generator.",
         fontsize=10.2, color=GREY, ha="left", va="top", linespacing=1.5)

out = "/home/c08r4d0r/repos/chainless-ebike-tradeoff/docs/parallel-hybrid-explainer.png"
fig.savefig(out, dpi=100, facecolor="white", bbox_inches="tight", pad_inches=0.22)
print("wrote", out)
