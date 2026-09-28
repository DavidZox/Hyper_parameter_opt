"""AMR 5 維超參數的多目標最佳化（NSGA-II / NSGA-III），重現「超參數優化.pptx」的結果。"""
from .algorithms import ALGO_TITLES, DEFAULTS, build_algorithm, run
from .console import console_report
from .knee import knee_point_index
from .problem import OBJ_NAMES, VAR_NAMES, XL, XU, AMRTuningProblem, evaluate
