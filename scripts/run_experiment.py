"""執行 NSGA-II / NSGA-III 實驗，輸出帕累托前緣圖、收斂圖、終端輸出與 CSV/JSON。

用法：
  python scripts/run_experiment.py --all                            # configs/experiments.yaml 全部 14 組
  python scripts/run_experiment.py --algo nsga2 --exp e4_etac1000   # 其中一組
  python scripts/run_experiment.py --algo nsga3 --pop-size 200 --eta-m 5 --name my_test   # 自訂參數
輸出：results/<algo>/<實驗名稱>/
"""
import argparse
import csv
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib
import numpy as np
import pymoo
import yaml

from amr_moo import ALGO_TITLES, OBJ_NAMES, VAR_NAMES, console_report, knee_point_index, run
from amr_moo.metrics import front_metrics, history_metrics
from amr_moo.plotting import SERIES, plot_convergence, plot_pareto_front
from amr_moo.true_front import IDEAL, NADIR

CONFIG = ROOT / "configs" / "experiments.yaml"
PARAM_ARGS = {  # 命令列參數 -> 參數名稱
    "pop_size": int, "n_gen": int, "crossover_prob": float, "eta_c": float,
    "mutation_prob": float, "mutation_prob_var": float, "eta_m": float, "n_partitions": int, "seed": int,
}


def load_config():
    with open(CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f)


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def run_one(algo, name, overrides, desc="", out_root=ROOT / "results", quiet=False):
    res, p, seconds = run(algo, overrides, save_history=True)
    X, F = res.X, res.F
    k = knee_point_index(F)
    k_fixed = knee_point_index(F, IDEAL, NADIR)
    report = console_report(X, F, k)

    out = out_root / algo / name
    out.mkdir(parents=True, exist_ok=True)
    (out / "console_output.txt").write_text(report + "\n", encoding="utf-8")

    title = f"{ALGO_TITLES[algo]} 5D Tuning with Knee Point Selection (η_c={p['eta_c']}, η_m={p['eta_m']})"
    plot_pareto_front(res.history, F, k, title, p["n_gen"], out / "pareto_front.png")

    gen_rows = history_metrics(res.history)
    write_csv(out / "generation_metrics.csv", gen_rows)
    plot_convergence(gen_rows, f"{ALGO_TITLES[algo]} · {name} · convergence of the returned solution set",
                     out / "convergence.png", color=SERIES[algo])

    # 完整解集合（順序與 pymoo 輸出、簡報表格相同）
    sol_rows = []
    for i, (x, f) in enumerate(zip(X, F)):
        row = {"idx": i, **{v: float(x[j]) for j, v in enumerate(VAR_NAMES)},
               **{o: float(f[j]) for j, o in enumerate(OBJ_NAMES)},
               "is_knee": int(i == k), "is_knee_fixed_norm": int(i == k_fixed)}
        sol_rows.append(row)
    write_csv(out / "pareto_solutions.csv", sol_rows)

    summary = {
        "algo": algo, "name": name, "desc": desc, "params": p, "runtime_sec": round(seconds, 3),
        "n_eval": int(res.algorithm.evaluator.n_eval),
        "knee": {"idx": k, **{v: float(X[k][j]) for j, v in enumerate(VAR_NAMES)},
                 **{o: float(F[k][j]) for j, o in enumerate(OBJ_NAMES)}},
        "knee_fixed_norm": {"idx": k_fixed, **{v: float(X[k_fixed][j]) for j, v in enumerate(VAR_NAMES)},
                            **{o: float(F[k_fixed][j]) for j, o in enumerate(OBJ_NAMES)}},
        "metrics": front_metrics(F),
        "versions": {"python": platform.python_version(), "pymoo": pymoo.__version__,
                     "numpy": np.__version__, "matplotlib": matplotlib.__version__},
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    if not quiet:
        print(f"\n##### {ALGO_TITLES[algo]} | {name} {desc} | "
              f"POP_SIZE={p['pop_size']} N_GEN={p['n_gen']} ETA_C={p['eta_c']} ETA_M={p['eta_m']} "
              f"seed={p['seed']} | {seconds:.2f} s")
        print(report)
        print(f"-> {out.relative_to(ROOT)}/")
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true", help="執行 configs/experiments.yaml 中的全部實驗")
    ap.add_argument("--algo", choices=["nsga2", "nsga3"], help="演算法")
    ap.add_argument("--exp", help="configs/experiments.yaml 中的實驗名稱，例如 e2_pop1000")
    ap.add_argument("--name", help="輸出資料夾名稱（自訂參數時使用，預設 custom）")
    for key, typ in PARAM_ARGS.items():
        ap.add_argument("--" + key.replace("_", "-"), dest=key, type=typ, help=f"覆寫 {key}")
    args = ap.parse_args()
    cfg = load_config()
    cli = {k: getattr(args, k) for k in PARAM_ARGS if getattr(args, k) is not None}

    if args.all:
        for algo in cfg["algorithms"]:
            for name, spec in cfg["experiments"].items():
                spec = dict(spec or {})
                desc = spec.pop("desc", "")
                spec.pop("algorithms", None)
                run_one(algo, name, {**spec, **cli}, desc)
        return

    if not args.algo:
        ap.error("請指定 --algo（或使用 --all）")
    if args.exp:
        known = {**cfg["experiments"], **cfg.get("suggested", {})}
        if args.exp not in known:
            ap.error(f"找不到實驗 {args.exp}，可用：{', '.join(known)}")
        spec = dict(known[args.exp] or {})
        desc = spec.pop("desc", "")
        spec.pop("algorithms", None)
        run_one(args.algo, args.name or args.exp, {**spec, **cli}, desc)
    else:
        run_one(args.algo, args.name or "custom", cli, "自訂參數")


if __name__ == "__main__":
    main()
