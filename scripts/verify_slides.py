"""把重現結果與「超參數優化.pptx」逐項比對。

直接從 pptx 讀出每張結果頁的 GA 參數、帕累托解表格（前 5 列）與膝點，
和 results/<algo>/<exp>/console_output.txt 比對，並把簡報原圖與重現圖並排。
輸出：results/reproduction_check.{md,csv}、results/figures/slide_compare/<algo>_<exp>.png
"""
import csv
import io
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml
from PIL import Image

from amr_moo import ALGO_TITLES
from amr_moo.algorithms import resolve_params

PPTX = ROOT / "超參數優化.pptx"
RESULTS = ROOT / "results"
PARAM_KEYS = {"POP_SIZE": "pop_size", "N_GEN": "n_gen", "CROSSOVER_PROB": "crossover_prob",
              "ETA_C": "eta_c", "MUTATION_PROB": "mutation_prob", "ETA_M": "eta_m"}
KNEE_KEYS = [("v_max", "最高車速"), ("a_max", "最大加速度"), ("w_safety", "安全距離權重"),
             ("k_steer", "轉向靈敏度"), ("q_r_ratio", "MPC Q/R"),
             ("exec_time", "執行時間"), ("collision_risk", "碰撞風險")]


def slide_paragraphs(z, n):
    xml = z.read(f"ppt/slides/slide{n}.xml").decode("utf-8")
    paras = re.findall(r"<a:p>.*?</a:p>|<a:p [^>]*>.*?</a:p>", xml, flags=re.S)
    return [html_unescape("".join(re.findall(r"<a:t>([^<]*)</a:t>", p))) for p in paras]


def html_unescape(s):
    return s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&amp;", "&")


def slide_image(z, n):
    rels = z.read(f"ppt/slides/_rels/slide{n}.xml.rels").decode("utf-8")
    target = re.search(r'Type="[^"]*/image" Target="\.\./media/([^"]+)"', rels)
    return Image.open(io.BytesIO(z.read("ppt/media/" + target.group(1)))) if target else None


def knee_values(lines):
    lines = [l for l in lines if l.strip().startswith(("▸", "🎯"))]
    vals = {}
    for key, label in KNEE_KEYS:
        line = next(l for l in lines if label in l)
        vals[key] = re.search(r":\s*([-\d.]+)", line).group(1)
    return vals


def parse_slides():
    """回傳 [{slide, algo, params, rows, knee}]，algo 依所在章節（NSGA-II / NSGA-III 標題頁）判斷。"""
    z = zipfile.ZipFile(PPTX)
    n_slides = len([f for f in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", f)])
    algo, found = None, []
    for n in range(1, n_slides + 1):
        lines = slide_paragraphs(z, n)
        text = "\n".join(lines)
        if "Genetic Algorithm III" in text:
            algo = "nsga3"
        elif "Genetic Algorithm II" in text:
            algo = "nsga2"
        if "POP_SIZE =" not in text:
            continue
        params = {}
        for l in lines:
            m = re.match(r"\s*(POP_SIZE|N_GEN|CROSSOVER_PROB|ETA_C|MUTATION_PROB|ETA_M)\s*=\s*([-\d.eE]+)", l)
            if m:
                params[PARAM_KEYS[m.group(1)]] = float(m.group(2))
        rows = [l for l in lines if "||" in l and re.search(r"\d", l)]
        found.append({"slide": n, "algo": algo, "params": params, "rows": rows, "knee": knee_values(lines),
                      "image": slide_image(z, n)})
    return found


def match_experiment(slide, cfg):
    for name, spec in cfg["experiments"].items():
        p = resolve_params({k: v for k, v in (spec or {}).items() if k != "desc"})
        if all(abs(p[k] - v) <= 1e-12 * max(1.0, abs(v)) for k, v in slide["params"].items()):
            return name
    return None


def side_by_side(slide_img, repro_path, caption_left, caption_right, out_path):
    right = Image.open(repro_path)
    fig, axes = plt.subplots(1, 2, figsize=(17, 6.6))
    for ax, img, cap in [(axes[0], slide_img, caption_left), (axes[1], right, caption_right)]:
        ax.imshow(img)
        ax.set_title(cap, fontsize=12, loc="left")
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_path, dpi=110)
    plt.close(fig)


def main():
    cfg = yaml.safe_load(open(ROOT / "configs" / "experiments.yaml", encoding="utf-8"))
    slides = parse_slides()
    out_dir = RESULTS / "figures" / "slide_compare"
    out_dir.mkdir(parents=True, exist_ok=True)
    records, all_ok = [], True
    for s in slides:
        name = match_experiment(s, cfg)
        rec = {"slide": s["slide"], "algo": s["algo"], "exp": name or "-",
               "slide_knee_time": s["knee"]["exec_time"], "slide_knee_risk": s["knee"]["collision_risk"]}
        console = RESULTS / s["algo"] / str(name) / "console_output.txt"
        if name is None or not console.exists():
            rec.update(rows_match="0/5", knee_match="missing", repro_knee_time="-", repro_knee_risk="-")
            all_ok = False
            records.append(rec)
            continue
        lines = console.read_text(encoding="utf-8").splitlines()
        repro_rows = [l for l in lines if "||" in l and re.search(r"\d", l)]
        repro_knee = knee_values(lines)
        n_ok = sum(a == b for a, b in zip(s["rows"], repro_rows))
        knee_ok = repro_knee == s["knee"]
        all_ok &= n_ok == len(s["rows"]) and knee_ok
        rec.update(rows_match=f"{n_ok}/{len(s['rows'])}", knee_match="✅" if knee_ok else "❌",
                   repro_knee_time=repro_knee["exec_time"], repro_knee_risk=repro_knee["collision_risk"])
        records.append(rec)
        if s["image"] is not None:
            side_by_side(s["image"], RESULTS / s["algo"] / name / "pareto_front.png",
                         f"Slide p.{s['slide']} (original)",
                         f"Reproduced: results/{s['algo']}/{name}/pareto_front.png",
                         out_dir / f"{s['algo']}_{name}.png")

    with open(RESULTS / "reproduction_check.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        w.writeheader()
        w.writerows(records)

    md = ["# 簡報 vs 重現結果比對", "",
          f"比對來源：`{PPTX.name}`（自動解析每張結果頁的文字）。"
          "表格前 5 列與膝點 7 個數值皆以字串完全相同為準。", "",
          "| 簡報頁 | 演算法 | 實驗 | 帕累托表格前 5 列 | 膝點 7 個數值 | 簡報膝點 (時間, 風險) | 重現膝點 (時間, 風險) |",
          "|---|---|---|---|---|---|---|"]
    for r in records:
        md.append(f"| p.{r['slide']} | {ALGO_TITLES.get(r['algo'], r['algo'])} | {r['exp']} | {r['rows_match']} | "
                  f"{r['knee_match']} | ({r['slide_knee_time']}, {r['slide_knee_risk']}) | "
                  f"({r['repro_knee_time']}, {r['repro_knee_risk']}) |")
    md += ["", "結論：" + ("**全部 14 組完全一致。**" if all_ok and len(records) == 14 else "**有不一致的項目，請檢查上表。**")]
    (RESULTS / "reproduction_check.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
