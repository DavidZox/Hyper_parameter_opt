"""繪圖：簡報樣式的帕累托前緣圖、單一實驗的收斂曲線。"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# 簡報原圖的配色（由簡報截圖取色）
GEN_STYLES = [("#bdc3c7", "o", 0.5), ("#3498db", "s", 0.5), ("#9b59b6", "^", 0.6)]
FRONT_COLOR = "#e74c3c"
KNEE_COLOR = "#f1c40f"

# 新增比較圖用的配色（經色盲安全檢查）
SERIES = {"nsga2": "#2a78d6", "nsga3": "#eb6834"}
TRUE_FRONT_COLOR = "#898781"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e1e0d9"


def snapshot_generations(n_gen):
    """簡報圖中畫出的中間代數：第 1 代、10% 與 40% 處（N_GEN=50 -> 1/6/21，N_GEN=100 -> 1/11/41）。"""
    return [0, n_gen // 10, int(n_gen * 0.4)]


def plot_pareto_front(history, F_final, knee_idx, title, n_gen, path, gen_s=40, front_s=60, knee_s=200):
    """重現簡報 p.3–9、p.13–19 的帕累托前緣圖。history 為 pymoo 的 res.history。

    版面與原圖相同：figsize=(10, 7)、dpi=100、預設子圖邊界，存檔時以 bbox_inches="tight" 裁切。
    """
    fig, ax = plt.subplots(figsize=(10, 7))
    for g, (color, marker, alpha) in zip(snapshot_generations(n_gen), GEN_STYLES):
        F = history[g].pop.get("F")
        ax.scatter(F[:, 0], F[:, 1], c=color, marker=marker, alpha=alpha, s=gen_s, label=f"Gen {g + 1}")

    order = np.argsort(F_final[:, 0])
    ax.plot(F_final[order, 0], F_final[order, 1], "--", color=FRONT_COLOR, linewidth=2, zorder=4)
    ax.scatter(F_final[:, 0], F_final[:, 1], c=FRONT_COLOR, s=front_s, zorder=5,
               label=f"Gen {n_gen} (Final Pareto Front)")

    kx, ky = F_final[knee_idx]
    ax.scatter(kx, ky, marker="*", s=knee_s, c=KNEE_COLOR, edgecolors="black", linewidths=1, zorder=6,
               label="Knee Point (Best Trade-off)")
    ax.annotate("Knee Point\n(Best Trade-off)", xy=(kx, ky), xytext=(kx + 5, ky + 3),
                arrowprops=dict(facecolor="black", shrink=0.05, width=1.5, headwidth=8),
                fontsize=10, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", fc=KNEE_COLOR, ec="black", alpha=0.8), zorder=7)

    ax.set_title(title, fontsize=14)
    ax.set_xlabel("Execution Time (seconds) [Minimize ->]", fontsize=12)
    ax.set_ylabel("Collision Risk Score [Minimize ->]", fontsize=12)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(fontsize=11)
    fig.savefig(path, dpi=100, bbox_inches="tight")
    plt.close(fig)


def _style_axes(ax):
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#c3c2b7")
    ax.tick_params(colors=INK2, labelsize=9)


def plot_convergence(rows, title, path, color=SERIES["nsga2"]):
    """單一實驗的 HV 比例與 IGD 隨代數變化（兩張子圖，不共用 y 軸）。"""
    gens = [r["gen"] for r in rows]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, key, label in [(axes[0], "hv_ratio", "HV / HV(true front)  [higher is better]"),
                           (axes[1], "igd", "IGD  [lower is better]")]:
        vals = [r[key] for r in rows]
        ax.plot(gens, vals, color=color, linewidth=2, solid_capstyle="round")
        ax.scatter([gens[-1]], [vals[-1]], color=color, s=36, zorder=3, edgecolors="white", linewidths=1.5)
        ax.annotate(f"{vals[-1]:.4f}", (gens[-1], vals[-1]), textcoords="offset points", xytext=(-6, 8),
                    ha="right", fontsize=9, color=INK)
        ax.set_xlabel("Generation", color=INK2)
        ax.set_title(label, fontsize=10, color=INK, loc="left")
        _style_axes(ax)
    axes[1].set_ylim(bottom=0)
    fig.suptitle(title, fontsize=12, color=INK, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
