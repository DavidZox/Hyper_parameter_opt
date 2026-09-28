"""終端輸出格式（與簡報上的文字輸出逐字相同）。"""

HEADER = "  v_max |  a_max | w_safety | k_steer | q_r_ratio || Exec Time | Risk Score"


def solution_row(x, f):
    return (f"{x[0]:7.2f} | {x[1]:6.2f} | {x[2]:8.2f} | {x[3]:7.2f} | {x[4]:9.1f} || "
            f"{f[0]:9.2f} | {f[1]:10.2f}")


def pareto_table(X, F, n_rows=5):
    lines = ["=== 5 維 AMR 超參數 - 帕累托最優解 (部分) ===", HEADER, "-" * len(HEADER)]
    lines += [solution_row(X[i], F[i]) for i in range(min(n_rows, len(X)))]
    return "\n".join(lines)


def knee_block(x, f):
    return "\n".join([
        "=" * 50,
        "★【膝點法計算結果 - 最佳折衷方案 (Knee Point / Best Trade-off)】★",
        "=" * 50,
        f" ▸ 最高車速 (v_max)     : {x[0]:.2f} m/s",
        f" ▸ 最大加速度 (a_max)   : {x[1]:.2f} m/s²",
        f" ▸ 安全距離權重 (w_safe): {x[2]:.2f}",
        f" ▸ 轉向靈敏度 (k_steer)  : {x[3]:.2f}",
        f" ▸ MPC Q/R 比值         : {x[4]:.1f}",
        "-" * 45,
        f" 🎯 執行時間 (Exec Time) : {f[0]:.2f} 秒",
        f" 🎯 碰撞風險 (Risk Score): {f[1]:.2f}",
        "=" * 50,
    ])


def console_report(X, F, knee_idx, n_rows=5):
    return pareto_table(X, F, n_rows) + "\n\n" + knee_block(X[knee_idx], F[knee_idx])
