"""多種子研究（非簡報內容）：同一組參數換不同亂數種子，看結論是否穩定。

對 configs/experiments.yaml 的 7 組簡報設定與建議實驗（suggested），每組跑 --seeds 個種子（預設 0~19），
統計膝點（簡報方法 / 固定正規化）、HV、IGD 的平均與標準差。
輸出：results/seed_study/{runs.csv, summary.csv, summary.md}、results/figures/seed_study.png
用法：python scripts/seed_study.py [--seeds 20]
"""
import argparse
import csv
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

from amr_moo import ALGO_TITLES, knee_point_index, run
from amr_moo.metrics import front_metrics
from amr_moo.plotting import GRID, INK, INK2, SERIES, _style_axes
from amr_moo.true_front import IDEAL, NADIR, true_front

OUT = ROOT / "results" / "seed_study"
SLIDE_SEED = 42
METRICS = ["knee_time", "knee_risk", "knee_fixed_time", "knee_fixed_risk", "hv_ratio", "igd", "risk_max",
           "k_steer_median", "q_r_ratio_median"]


def configs(cfg):
    for group in ("experiments", "suggested"):
        for name, spec in (cfg.get(group) or {}).items():
            spec = dict(spec or {})
            spec.pop("desc", None)
            for algo in spec.pop("algorithms", cfg["algorithms"]):
                yield group, algo, name, spec


def one_run(algo, spec, seed):
    res, p, sec = run(algo, {**spec, "seed": seed}, save_history=False)
    F, X = res.F, res.X
    k, kf = knee_point_index(F), knee_point_index(F, IDEAL, NADIR)
    m = front_metrics(F)
    return {"knee_time": F[k, 0], "knee_risk": F[k, 1], "knee_fixed_time": F[kf, 0], "knee_fixed_risk": F[kf, 1],
            "hv_ratio": m["hv_ratio"], "igd": m["igd"], "risk_max": m["risk_max"],
            "k_steer_median": float(np.median(X[:, 3])), "q_r_ratio_median": float(np.median(X[:, 4])),
            "n_solutions": m["n_solutions"], "runtime_sec": sec}


def label(name, spec):
    keys = {"pop_size": "POP_SIZE", "n_gen": "N_GEN", "eta_c": "η_c", "eta_m": "η_m", "mutation_prob": "p_m",
            "mutation_prob_var": "p_m,var", "n_partitions": "n_partitions", "crossover_prob": "p_c"}
    changed = [f"{keys[k]}={v:g}" for k, v in spec.items() if k in keys]
    return f"{name.split('_')[0]} · {', '.join(changed) or 'baseline'}"


def plot(rows, order, labels, path):
    panels = [("knee_time", "Knee execution time (s), slide method"),
              ("knee_fixed_time", "Knee execution time (s), fixed normalization"),
              ("igd", "IGD (lower is better)")]
    fig, axes = plt.subplots(1, 3, figsize=(17, 0.55 * len(order) + 1.8), sharey=True)
    axes[1].sharex(axes[0])  # 兩種膝點用同一個 x 軸範圍，才能直接比較穩定度
    y_of = {name: i for i, name in enumerate(order[::-1])}
    k_true = knee_point_index(true_front()[1])
    for ax, (key, title) in zip(axes, panels):
        for algo, dy in (("nsga2", 0.14), ("nsga3", -0.14)):
            for name in order:
                r = [x for x in rows if x["algo"] == algo and x["exp"] == name]
                if not r:
                    continue
                vals = np.array([x[key] for x in r])
                seeds = np.array([x["seed"] for x in r])
                y = np.full(len(vals), y_of[name] + dy)
                ax.scatter(vals, y, s=22, color=SERIES[algo], alpha=0.55, edgecolors="none", zorder=3)
                ax.scatter(vals.mean(), y[0], s=70, marker="|", color=INK, linewidths=2, zorder=4)
                hit = seeds == SLIDE_SEED
                if hit.any():
                    ax.scatter(vals[hit], y[hit], s=70, facecolors="none", edgecolors=INK, linewidths=1.2, zorder=5)
        if key != "igd":
            ax.axvline(true_front()[1][k_true, 0], color=INK2, linewidth=1, linestyle="-", zorder=1)
        ax.set_title(title, fontsize=10.5, color=INK, loc="left")
        _style_axes(ax)
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(range(len(order)), [labels[n] for n in order[::-1]], fontsize=9.5)
    axes[2].set_xlim(left=0)
    handles = [Line2D([], [], marker="o", linestyle="", color=SERIES[a], alpha=0.7, label=ALGO_TITLES[a])
               for a in ("nsga2", "nsga3")]
    handles += [Line2D([], [], marker="|", linestyle="", color=INK, markersize=10, markeredgewidth=2, label="mean"),
                Line2D([], [], marker="o", linestyle="", markerfacecolor="none", markeredgecolor=INK,
                       label=f"seed={SLIDE_SEED} (the slides)"),
                Line2D([], [], color=INK2, linewidth=1, label="true knee (43.54 s)")]
    fig.legend(handles=handles, loc="upper right", ncol=5, frameon=False, fontsize=9.5)
    fig.suptitle(f"Seed study: each dot is one run ({len({r['seed'] for r in rows})} seeds per setting)",
                 fontsize=12, color=INK, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20, help="種子數量（使用 0 ~ N-1，並額外加入簡報的 42）")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(ROOT / "configs" / "experiments.yaml", encoding="utf-8"))
    seeds = sorted(set(range(args.seeds)) | {SLIDE_SEED})
    OUT.mkdir(parents=True, exist_ok=True)

    rows, labels, order = [], {}, []
    for group, algo, name, spec in configs(cfg):
        labels[name] = label(name, spec)
        if name not in order:
            order.append(name)
        for s in seeds:
            rows.append({"group": group, "algo": algo, "exp": name, "seed": s, **one_run(algo, spec, s)})
        print(f"{ALGO_TITLES[algo]:8s} {name:16s} done ({len(seeds)} seeds)")

    with open(OUT / "runs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # 統計：平均與標準差使用全部種子（含 42）
    summary = []
    for algo in cfg["algorithms"]:
        for name in order:
            r = [x for x in rows if x["algo"] == algo and x["exp"] == name]
            if not r:
                continue
            row = {"algo": algo, "exp": name, "n_runs": len(r)}
            for m in METRICS:
                v = np.array([x[m] for x in r])
                row[f"{m}_mean"], row[f"{m}_std"] = float(v.mean()), float(v.std(ddof=1))
                row[f"{m}_min"], row[f"{m}_max"] = float(v.min()), float(v.max())
            row["seed42_knee_time"] = next(x["knee_time"] for x in r if x["seed"] == SLIDE_SEED)
            summary.append(row)
    with open(OUT / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)

    md = ["# 多種子研究", "",
          f"每組設定跑 {len(seeds)} 個種子（0~{args.seeds - 1} 與簡報的 {SLIDE_SEED}），表中為 平均 ± 標準差（最小 ~ 最大）。"
          "e1~e7 為簡報設定，s1、s2 為建議實驗。", "",
          "| 演算法 | 設定 | 膝點時間：簡報方法 (s) | seed=42 | 膝點時間：固定正規化 (s) | HV 比例 | IGD | 前緣最高風險 | k_steer 中位數 |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in summary:
        f = lambda m, d=2: f"{r[m + '_mean']:.{d}f} ± {r[m + '_std']:.{d}f}"
        md.append(f"| {ALGO_TITLES[r['algo']]} | {labels[r['exp']]} | {f('knee_time', 1)} "
                  f"({r['knee_time_min']:.1f} ~ {r['knee_time_max']:.1f}) | {r['seed42_knee_time']:.1f} | "
                  f"{f('knee_fixed_time')} | {r['hv_ratio_mean']:.4f} | {f('igd', 3)} | {f('risk_max', 1)} | "
                  f"{f('k_steer_median')} |")
    (OUT / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))

    fig_dir = ROOT / "results" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    plot(rows, order, labels, fig_dir / "seed_study.png")
    print("-> results/seed_study/, results/figures/seed_study.png")


if __name__ == "__main__":
    main()
