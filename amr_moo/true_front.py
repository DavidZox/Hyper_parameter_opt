"""理論帕累托前緣（解析解，非簡報內容，用於計算 HV / IGD 等指標）。

兩個目標在邊界盒內都是凸函數，所以整條帕累托前緣都能用加權和 min λ·f1 + (1-λ)·f2 求得，
而且各變數互相獨立，每個 λ 都有封閉解：
    k_steer = 0.5（下界），q_r_ratio = 1000（上界）
    v_max    = clip( (100λ / (0.3(1-λ)))^(1/3), 0.5, 3.0 )
    a_max    = clip( sqrt(20λ / (1-λ)),          0.1, 2.0 )
    w_safety = clip( sqrt(5(1-λ) / (0.3λ)),       0.1, 10.0 )
"""
import numpy as np

from .problem import XL, XU, evaluate


def analytic_front(n=20001):
    """回傳 (X, F)，沿 λ 由 0 到 1 取樣（λ 以 logit 等距，兩端都取得夠密）。"""
    t = np.linspace(-30.0, 30.0, n)
    lam = 1.0 / (1.0 + np.exp(-t))
    one_minus = 1.0 / (1.0 + np.exp(t))          # 1-λ，避免 λ≈1 時相減失真
    v = np.clip(np.cbrt(100.0 * lam / (0.3 * one_minus)), XL[0], XU[0])
    a = np.clip(np.sqrt(20.0 * lam / one_minus), XL[1], XU[1])
    w = np.clip(np.sqrt(5.0 * one_minus / (0.3 * lam)), XL[2], XU[2])
    X = np.column_stack([v, a, w, np.full(n, XL[3]), np.full(n, XU[4])])
    return X, evaluate(X)


_X_TRUE, _F_TRUE = analytic_front()
IDEAL = _F_TRUE.min(axis=0)   # (38.463, 0.6875)：兩個目標各自的最佳值
NADIR = _F_TRUE.max(axis=0)   # (303.1, 52.45)：帕累托前緣上的最差值


def normalize(F):
    """以理論前緣的 ideal / nadir 正規化到 0~1。"""
    return (np.asarray(F, dtype=float) - IDEAL) / (NADIR - IDEAL)


def uniform_front(n=1000):
    """在正規化空間中依弧長等距取樣 n 點（IGD 的參考集）。回傳 (X, F)。"""
    Fn = normalize(_F_TRUE)
    seg = np.linalg.norm(np.diff(Fn, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    idx = np.searchsorted(s, np.linspace(0.0, s[-1], n)).clip(0, len(s) - 1)
    return _X_TRUE[idx], _F_TRUE[idx]


def true_front():
    return _X_TRUE, _F_TRUE
