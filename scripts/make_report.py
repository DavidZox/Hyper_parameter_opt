"""彙整 14 組實驗：results/summary.{csv,md} 與 results/figures/ 的比較圖。

需先執行 scripts/run_experiment.py --all。
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, NullFormatter

from amr_moo import ALGO_TITLES, VAR_NAMES, knee_point_index
from amr_moo.metrics import HV_TRUE
from amr_moo.plotting import GRID, INK, INK2, SERIES, TRUE_FRONT_COLOR, _style_axes
from amr_moo.true_front import IDEAL, NADIR, true_front

RESULTS = ROOT / "results"
FIG = RESULTS / "figures"
PLAIN = FuncFormatter(lambda v, _: f"{v:g}")


def load():
    cfg = yaml.safe_load(open(ROOT / "configs" / "experiments.yaml", encoding="utf-8"))
    data = {}
    for algo in cfg["algorithms"]:
        for name in cfg["experiments"]:
            d = RESULTS / algo / name
            if not (d / "summary.json").exists():
                sys.exit(f"缺少 {d}/summary.json，請先執行 python scripts/run_experiment.py --all")
            sols = list(csv.DictReader(open(d / "pareto_solutions.csv", encoding="utf-8")))
            gens = list(csv.DictReader(open(d / "generation_metrics.csv", encoding="utf-8")))
            data[algo, name] = {
                "summary": json.load(open(d / "summary.json", encoding="utf-8")),
                "X": np.array([[float(r[v]) for v in VAR_NAMES] for r in sols]),
                "F": np.array([[float(r["exec_time"]), float(r["collision_risk"])] for r in sols]),
                "gen": np.array([int(r["gen"]) for r in gens]),
                "igd": np.array([float(r["igd"]) for r in gens]),
            }
    return cfg, data


PARAM_LABELS = {"pop_size": "POP_SIZE", "n_gen": "N_GEN", "crossover_prob": "p_c", "eta_c": "η_c",
                "mutation_prob": "p_m", "mutation_prob_var": "p_m,var", "eta_m": "η_m",
                "n_partitions": "n_partitions", "seed": "seed"}


def short_label(name, spec):
    """圖中用的英文標籤，由與預設值不同的參數組成，例如 'e4 · η_c=1000'。"""
    changed = [f"{PARAM_LABELS[k]}={v:g}" for k, v in (spec or {}).items() if k in PARAM_LABELS]
    return f"{name.split('_')[0]} · {', '.join(changed) or 'baseline'}"


def log_axes(ax):
    ax.set_xscale("log")
    ax.set_yscale("log")
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_formatter(PLAIN)
        axis.set_minor_formatter(NullFormatter())
    ax.set_xticks([40, 60, 100, 200, 300])
    ax.set_yticks([0.7, 1, 2, 5, 10, 20, 50])


def fig_fronts(cfg, data, Ft):
    names = list(cfg["experiments"])
    fig, axes = plt.subplots(2, 4, figsize=(16, 7.6), sharex=True, sharey=True)
    for ax, name in zip(axes.flat, names):
        ax.plot(Ft[:, 0], Ft[:, 1], color=TRUE_FRONT_COLOR, linewidth=1.5, zorder=1)
        for algo in cfg["algorithms"]:
            F = data[algo, name]["F"]
            k = data[algo, name]["summary"]["knee"]["idx"]
            ax.scatter(F[:, 0], F[:, 1], s=20, color=SERIES[algo], edgecolors="white", linewidths=0.5, zorder=3)
            ax.scatter(F[k, 0], F[k, 1], s=150, marker="*", color=SERIES[algo], edgecolors=INK,
                       linewidths=0.8, zorder=4)
        log_axes(ax)
        _style_axes(ax)
        ax.set_title(short_label(name, cfg["experiments"][name]), fontsize=10, color=INK, loc="left")
    leg_ax = axes.flat[-1]
    leg_ax.axis("off")
    handles = [Line2D([], [], color=TRUE_FRONT_COLOR, linewidth=1.5, label="True Pareto front (analytic)")]
    for algo in cfg["algorithms"]:
        handles.append(Line2D([], [], marker="o", linestyle="", color=SERIES[algo], markersize=6,
                              label=f"{ALGO_TITLES[algo]} final solutions"))
        handles.append(Line2D([], [], marker="*", linestyle="", color=SERIES[algo], markeredgecolor=INK,
                              markersize=12, label=f"{ALGO_TITLES[algo]} knee point"))
    leg_ax.legend(handles=handles, loc="center left", frameon=False, fontsize=10)
    axes[0, 3].tick_params(labelbottom=True)
    for ax in list(axes[1, :3]) + [axes[0, 3]]:
        ax.set_xlabel("Execution Time (s, log scale)", color=INK2)
    for ax in axes[:, 0]:
        ax.set_ylabel("Collision Risk (log scale)", color=INK2)
    fig.suptitle("Final Pareto fronts of the 7 GA settings vs. the analytic true front", fontsize=13,
                 color=INK, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(FIG / "fronts_by_setting.png", dpi=130)
    plt.close(fig)


def fig_metrics(cfg, data):
    names = list(cfg["experiments"])
    y = np.arange(len(names))[::-1]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), sharey=True)
    panels = [("hv_ratio", "HV / HV(true front)   higher is better"), ("igd", "IGD   lower is better")]
    for ax, (key, title) in zip(axes, panels):
        vals = {algo: np.array([data[algo, n]["summary"]["metrics"][key] for n in names])
                for algo in cfg["algorithms"]}
        ax.hlines(y, np.minimum(*vals.values()), np.maximum(*vals.values()), color=GRID, linewidth=2, zorder=1)
        for algo in cfg["algorithms"]:
            ax.scatter(vals[algo], y, s=64, color=SERIES[algo], edgecolors="white", linewidths=1.5, zorder=3,
                       label=ALGO_TITLES[algo])
        ax.set_title(title, fontsize=11, color=INK, loc="left")
        _style_axes(ax)
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(y, [short_label(n, cfg["experiments"][n]) for n in names], fontsize=10)
    axes[0].xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.3f}"))
    axes[1].set_xlim(left=0)
    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", ncol=2, frameon=False, fontsize=10)
    fig.suptitle("Quality of the returned solution set (normalized by the analytic front)", fontsize=12,
                 color=INK, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(FIG / "metrics_comparison.png", dpi=130)
    plt.close(fig)


def fig_knees(cfg, data, Ft):
    names = list(cfg["experiments"])
    k_true = knee_point_index(Ft)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.4), sharex=True, sharey=True)
    for ax, key, title in [(axes[0], "knee", "Knee as in the slides (normalized by each front's own min/max)"),
                           (axes[1], "knee_fixed_norm", "Knee with fixed normalization (analytic ideal / nadir)")]:
        ax.plot(Ft[:, 0], Ft[:, 1], color=TRUE_FRONT_COLOR, linewidth=1.5, zorder=1)
        for algo in cfg["algorithms"]:
            pts = np.array([[data[algo, n]["summary"][key]["exec_time"], data[algo, n]["summary"][key]["collision_risk"]]
                            for n in names])
            ax.scatter(pts[:, 0], pts[:, 1], s=64, color=SERIES[algo], edgecolors="white", linewidths=1.5, zorder=3,
                       label=f"{ALGO_TITLES[algo]} (7 settings)")
            if key == "knee":
                dy, va = (7, "bottom") if algo == "nsga2" else (-7, "top")
                for n, (px, py) in zip(names, pts):
                    ax.annotate(n.split("_")[0], (px, py), textcoords="offset points", xytext=(0, dy),
                                ha="center", va=va, fontsize=8, color=INK2, zorder=5)
        ax.scatter(*Ft[k_true], s=220, marker="*", color=INK, edgecolors="white", linewidths=1, zorder=4,
                   label=f"True knee ({Ft[k_true, 0]:.2f} s, {Ft[k_true, 1]:.2f})")
        ax.set_xlim(38, 95)
        ax.set_ylim(1.0, 3.3)
        ax.set_title(title, fontsize=10.5, color=INK, loc="left")
        ax.set_xlabel("Execution Time (s)", color=INK2)
        _style_axes(ax)
    axes[0].set_ylabel("Collision Risk", color=INK2)
    axes[0].legend(loc="upper right", frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "knee_points.png", dpi=130)
    plt.close(fig)


def fig_convergence(cfg, data):
    names = list(cfg["experiments"])
    fig, axes = plt.subplots(2, 4, figsize=(16, 6.8), sharey=True)
    for ax, name in zip(axes.flat, names):
        for algo in cfg["algorithms"]:
            d = data[algo, name]
            ax.plot(d["gen"], d["igd"], color=SERIES[algo], linewidth=2, solid_capstyle="round")
        ax.set_title(short_label(name, cfg["experiments"][name]), fontsize=10, color=INK, loc="left")
        ax.set_xlabel("Generation", color=INK2)
        _style_axes(ax)
    for ax in axes[:, 0]:
        ax.set_ylabel("IGD (lower is better)", color=INK2)
    axes.flat[0].set_ylim(bottom=0)
    leg_ax = axes.flat[-1]
    leg_ax.axis("off")
    leg_ax.legend(handles=[Line2D([], [], color=SERIES[a], linewidth=2, label=ALGO_TITLES[a]) for a in cfg["algorithms"]],
                  loc="center left", frameon=False, fontsize=11)
    fig.suptitle("IGD of the returned solution set per generation", fontsize=13, color=INK, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(FIG / "convergence_igd.png", dpi=130)
    plt.close(fig)


def fig_pareto_set(cfg, data, Xt, Ft, name="e1_baseline"):
    labels = {"v_max": "v_max (m/s)", "a_max": "a_max (m/s²)", "w_safety": "w_safety",
              "k_steer": "k_steer", "q_r_ratio": "q_r_ratio"}
    fig, axes = plt.subplots(1, 5, figsize=(18, 3.9), sharex=True)
    for j, (ax, var) in enumerate(zip(axes, VAR_NAMES)):
        ax.plot(Ft[:, 0], Xt[:, j], color=TRUE_FRONT_COLOR, linewidth=1.5, zorder=1)
        for algo in cfg["algorithms"]:
            d = data[algo, name]
            ax.scatter(d["F"][:, 0], d["X"][:, j], s=20, color=SERIES[algo], edgecolors="white", linewidths=0.5,
                       zorder=3)
        ax.set_xscale("log")
        ax.xaxis.set_major_formatter(PLAIN)
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.set_xticks([40, 100, 300])
        ax.set_title(labels[var], fontsize=10.5, color=INK, loc="left")
        ax.set_xlabel("Execution Time (s, log)", color=INK2)
        _style_axes(ax)
    handles = [Line2D([], [], color=TRUE_FRONT_COLOR, linewidth=1.5, label="Analytic Pareto set")] + [
        Line2D([], [], marker="o", linestyle="", color=SERIES[a], markersize=6, label=ALGO_TITLES[a])
        for a in cfg["algorithms"]]
    fig.legend(handles=handles, loc="upper right", ncol=3, frameon=False, fontsize=10)
    fig.suptitle(f"Hyper-parameter values along the Pareto front ({name})", fontsize=12, color=INK, x=0.01,
                 ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(FIG / f"pareto_set_{name}.png", dpi=130)
    plt.close(fig)


def write_tables(cfg, data, Xt, Ft):
    k_true = knee_point_index(Ft)
    rows = []
    for algo in cfg["algorithms"]:
        for name in cfg["experiments"]:
            s = data[algo, name]["summary"]
            p, m, k, kf = s["params"], s["metrics"], s["knee"], s["knee_fixed_norm"]
            rows.append({
                "algo": algo, "exp": name, "pop_size": p["pop_size"], "n_gen": p["n_gen"],
                "eta_c": p["eta_c"], "eta_m": p["eta_m"], "seed": p["seed"],
                **{f"knee_{v}": round(k[v], 4) for v in VAR_NAMES},
                "knee_exec_time": round(k["exec_time"], 4), "knee_risk": round(k["collision_risk"], 4),
                "knee_fixed_exec_time": round(kf["exec_time"], 4), "knee_fixed_risk": round(kf["collision_risk"], 4),
                "n_solutions": m["n_solutions"], "hv_ratio": round(m["hv_ratio"], 6), "igd": round(m["igd"], 6),
                "time_min": round(m["time_min"], 3), "time_max": round(m["time_max"], 3),
                "risk_min": round(m["risk_min"], 4), "risk_max": round(m["risk_max"], 4),
                "n_eval": s["n_eval"], "runtime_sec": s["runtime_sec"],
            })
    with open(RESULTS / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    v = data[cfg["algorithms"][0], next(iter(cfg["experiments"]))]["summary"]["versions"]
    md = ["# 實驗彙整", "",
          f"環境：Python {v['python']}、pymoo {v['pymoo']}、numpy {v['numpy']}、matplotlib {v['matplotlib']}；"
          "所有實驗 seed=42。", "",
          "## 1. 膝點（簡報的方法：以各自前緣的 min/max 正規化，取距離原點最近者）", "",
          "| 演算法 | 實驗 | v_max | a_max | w_safety | k_steer | q_r_ratio | 執行時間 (s) | 碰撞風險 |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {ALGO_TITLES[r['algo']]} | {r['exp']} | {r['knee_v_max']:.2f} | {r['knee_a_max']:.2f} | "
                  f"{r['knee_w_safety']:.2f} | {r['knee_k_steer']:.2f} | {r['knee_q_r_ratio']:.1f} | "
                  f"{r['knee_exec_time']:.2f} | {r['knee_risk']:.2f} |")
    md += ["", "## 2. 解集合品質（以理論前緣正規化）", "",
           f"理論前緣：ideal = ({IDEAL[0]:.2f}, {IDEAL[1]:.4f})、nadir = ({NADIR[0]:.2f}, {NADIR[1]:.2f})，"
           f"HV 參考點 (1.1, 1.1)，理論 HV = {HV_TRUE:.4f}。", "",
           "| 演算法 | 實驗 | 解的個數 | HV 比例 ↑ | IGD ↓ | 時間範圍 (s) | 風險範圍 | 評估次數 | 執行秒數 |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {ALGO_TITLES[r['algo']]} | {r['exp']} | {r['n_solutions']} | {r['hv_ratio']:.4f} | "
                  f"{r['igd']:.4f} | {r['time_min']:.2f} – {r['time_max']:.2f} | "
                  f"{r['risk_min']:.2f} – {r['risk_max']:.2f} | {r['n_eval']} | {r['runtime_sec']:.2f} |")
    md += ["", "## 3. 膝點：簡報方法 vs 固定正規化", "",
           f"理論前緣的膝點（固定正規化）：v_max={Xt[k_true, 0]:.2f}, a_max={Xt[k_true, 1]:.2f}, "
           f"w_safety={Xt[k_true, 2]:.2f}, k_steer={Xt[k_true, 3]:.2f}, q_r_ratio={Xt[k_true, 4]:.0f} → "
           f"時間 {Ft[k_true, 0]:.2f} s、風險 {Ft[k_true, 1]:.2f}。", "",
           "| 演算法 | 實驗 | 前緣最高風險 | 簡報方法 (時間, 風險) | 固定正規化 (時間, 風險) |", "|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {ALGO_TITLES[r['algo']]} | {r['exp']} | {r['risk_max']:.2f} | "
                  f"({r['knee_exec_time']:.2f}, {r['knee_risk']:.2f}) | "
                  f"({r['knee_fixed_exec_time']:.2f}, {r['knee_fixed_risk']:.2f}) |")
    (RESULTS / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return rows


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    cfg, data = load()
    Xt, Ft = true_front()
    write_tables(cfg, data, Xt, Ft)
    fig_fronts(cfg, data, Ft)
    fig_metrics(cfg, data)
    fig_knees(cfg, data, Ft)
    fig_convergence(cfg, data)
    fig_pareto_set(cfg, data, Xt, Ft)
    print("-> results/summary.csv, results/summary.md")
    for f in sorted(FIG.glob("*.png")):
        print("->", f.relative_to(ROOT))


if __name__ == "__main__":
    main()
