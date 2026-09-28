"""AMR 黑盒評價方程（簡報 p.2–9、p.13–19）。

5 維超參數 X = [v_max, a_max, w_safety, k_steer, q_r_ratio] -> 2 個目標 F = [執行時間, 碰撞風險]，兩者皆為最小化。
"""
import numpy as np
from pymoo.core.problem import ElementwiseProblem

VAR_NAMES = ["v_max", "a_max", "w_safety", "k_steer", "q_r_ratio"]
VAR_LABELS = {
    "v_max": "最高車速 v_max (m/s)",
    "a_max": "最大加速度 a_max (m/s²)",
    "w_safety": "安全距離權重 w_safety",
    "k_steer": "轉向靈敏度 k_steer",
    "q_r_ratio": "MPC Q/R 比值 q_r_ratio",
}
OBJ_NAMES = ["exec_time", "collision_risk"]

# 邊界矩陣（簡報 p.2 流程圖）
XL = np.array([0.5, 0.1, 0.1, 0.5, 10.0])
XU = np.array([3.0, 2.0, 10.0, 5.0, 1000.0])


def amr_objectives(v_max, a_max, w_safety, k_steer, q_r_ratio):
    """兩個目標值；純量或 numpy 陣列皆可。"""
    # 1. 執行時間 Time: 受最高速度限制，但加速度大降速快；轉向太靈敏可能震盪耗時
    execution_time = (100.0 / v_max) + (10.0 / a_max) + (0.3 * w_safety) + (0.2 * k_steer)
    # 2. 碰撞與不平穩風險 Risk: 速度與加速度越大風險越高；安全權重與 MPC 比值越大越平穩(風險低)
    collision_risk = (0.15 * (v_max ** 2)) + (0.5 * a_max) + (5.0 / w_safety) + (100.0 / q_r_ratio)
    return execution_time, collision_risk


def evaluate(X):
    """向量化評估：X 形狀 (n, 5)，回傳 F 形狀 (n, 2)。"""
    X = np.atleast_2d(np.asarray(X, dtype=float))
    return np.column_stack(amr_objectives(*X.T))


class AMRTuningProblem(ElementwiseProblem):
    """模擬多維度 AMR 黑盒評價方程（逐個體評估，與原始程式相同）。"""

    def __init__(self):
        super().__init__(n_var=5, n_obj=2, n_ieq_constr=0, xl=XL.copy(), xu=XU.copy())

    def _evaluate(self, x, out, *args, **kwargs):
        v_max, a_max, w_safety, k_steer, q_r_ratio = x
        out["F"] = list(amr_objectives(v_max, a_max, w_safety, k_steer, q_r_ratio))
