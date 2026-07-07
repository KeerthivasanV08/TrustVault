import numpy as np


def normalize(value):
    return float(np.clip(value, 0, 1))


def safe_div(a, b):
    return a / b if b != 0 else 0