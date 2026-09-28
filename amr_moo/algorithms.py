"""NSGA-II / NSGA-III 建構與執行（pymoo 0.6.2）。"""
import time

from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.optimize import minimize
from pymoo.util.ref_dirs import get_reference_directions

from .problem import AMRTuningProblem

ALGO_TITLES = {"nsga2": "NSGA-II", "nsga3": "NSGA-III"}

# === 【GA 參數可調區域】（簡報的預設值；configs/experiments.yaml 與命令列參數會覆寫） ===
DEFAULTS = {
    "pop_size": 60,            # 族群大小 (Population Size)
    "n_gen": 50,               # 演化代數 (Generations)
    # SBX 交叉算子設定 (Simulated Binary Crossover)
    "crossover_prob": 0.9,     # 交叉機率 (預設 0.9)
    "eta_c": 15.0,             # 交叉分佈指數 η_c (值越大搜尋越保守，值越小搜尋越激進)
    # 多項式突變算子設定 (Polynomial Mutation)
    "mutation_prob": 0.2,      # 突變機率：pymoo 中是「每個個體」被突變的機率
    "mutation_prob_var": None,  # 被選中的個體中每個維度的突變機率；None = pymoo 預設 min(0.5, 1/n_var) = 0.2
    "eta_m": 20.0,             # 突變分佈指數 η_m (值越大擾動幅度越小/精細，值越小擾動越劇烈)
    # NSGA-III 結構化參考點 (Das-Dennis)
    "n_partitions": 12,        # 分段數 p；M=2 時產生 p+1 = 13 條參考射線
    "seed": 42,                # 亂數種子（簡報結果由 seed=42 產生）
}


def resolve_params(overrides=None):
    """以 DEFAULTS 補齊參數並統一型別。"""
    p = {**DEFAULTS, **{k: v for k, v in (overrides or {}).items() if k in DEFAULTS and v is not None}}
    for k in ("pop_size", "n_gen", "n_partitions", "seed"):
        p[k] = int(p[k])
    for k in ("crossover_prob", "eta_c", "mutation_prob", "eta_m"):
        p[k] = float(p[k])
    if p["mutation_prob_var"] is not None:
        p["mutation_prob_var"] = float(p["mutation_prob_var"])
    return p


def build_algorithm(algo, p):
    common = dict(
        pop_size=p["pop_size"],
        sampling=FloatRandomSampling(),
        crossover=SBX(prob=p["crossover_prob"], eta=p["eta_c"]),
        mutation=PM(prob=p["mutation_prob"], prob_var=p["mutation_prob_var"], eta=p["eta_m"]),
        eliminate_duplicates=True,
    )
    if algo == "nsga2":
        return NSGA2(**common)
    if algo == "nsga3":
        ref_dirs = get_reference_directions("das-dennis", 2, n_partitions=p["n_partitions"])
        return NSGA3(ref_dirs=ref_dirs, **common)
    raise ValueError(f"未知的演算法：{algo}（可用 nsga2 / nsga3）")


def run(algo, params=None, save_history=True, verbose=False):
    """執行一次最佳化，回傳 (pymoo Result, 完整參數, 執行秒數)。"""
    p = resolve_params(params)
    algorithm = build_algorithm(algo, p)
    t0 = time.perf_counter()
    res = minimize(AMRTuningProblem(), algorithm, ("n_gen", p["n_gen"]), seed=p["seed"],
                   save_history=save_history, verbose=verbose)
    return res, p, time.perf_counter() - t0
