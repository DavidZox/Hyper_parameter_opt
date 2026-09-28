"""膝點法（Knee Point）：正規化後，選擇距離理想點 (0, 0) 最近的解（簡報 p.2 方法一）。"""
import numpy as np


def knee_point_index(F, ideal=None, nadir=None):
    """回傳膝點在 F 中的索引。

    預設以 F 自身的最小/最大值正規化（與簡報相同）；
    也可傳入固定的 ideal / nadir（例如理論前緣的值），讓不同實驗用同一把尺比較。
    """
    F = np.asarray(F, dtype=float)
    ideal = F.min(axis=0) if ideal is None else np.asarray(ideal, dtype=float)
    nadir = F.max(axis=0) if nadir is None else np.asarray(nadir, dtype=float)
    F_norm = (F - ideal) / (nadir - ideal)
    return int(np.argmin(np.linalg.norm(F_norm, axis=1)))
