"""帕累托前緣品質指標（以理論前緣正規化到 0~1 後計算）。

- HV（Hypervolume，越大越好）：參考點 (1.1, 1.1)；hv_ratio = HV / 理論前緣的 HV。
- IGD（越小越好）：理論前緣上 1000 個等距點到解集合的平均最近距離，同時反映收斂與覆蓋範圍。
"""
import numpy as np
from pymoo.indicators.hv import HV
from pymoo.indicators.igd import IGD

from .true_front import normalize, true_front, uniform_front

REF_POINT = np.array([1.1, 1.1])
_HV = HV(ref_point=REF_POINT)
_IGD = IGD(normalize(uniform_front(1000)[1]))
HV_TRUE = float(_HV(normalize(true_front()[1])))


def front_metrics(F):
    F = np.asarray(F, dtype=float)
    Fn = normalize(F)
    hv = float(_HV(Fn))
    return {
        "n_solutions": int(len(F)),
        "hv": hv,
        "hv_ratio": hv / HV_TRUE,
        "igd": float(_IGD(Fn)),
        "time_min": float(F[:, 0].min()),
        "time_max": float(F[:, 0].max()),
        "risk_min": float(F[:, 1].min()),
        "risk_max": float(F[:, 1].max()),
    }


def history_metrics(history):
    """每一代回傳的解集合（algorithm.opt）的指標。"""
    rows = []
    for h in history:
        F = h.opt.get("F")
        rows.append({"gen": h.n_gen, "n_eval": h.evaluator.n_eval, **front_metrics(F)})
    return rows
