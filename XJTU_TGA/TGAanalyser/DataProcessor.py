# -*- coding: utf-8 -*-
# @Time : 2024/8/8 22:31
# @Author : DanYang
# @File : DataProcessor.py
# @Software : PyCharm
import os

import pandas as pd
import numpy as np
from scipy.signal import butter, filtfilt

from . import CONFIG


class TGAData:
    load_cfg = CONFIG["load_data"]
    delimiter = load_cfg["delimiter"]
    encoding = load_cfg["encoding"]
    delta_t = load_cfg["delta_t"]
    columns = load_cfg["columns"]

    filter_cfg = CONFIG["filter_data"]
    N = filter_cfg["N"]
    Wn = filter_cfg["Wn"]
    btype = filter_cfg["btype"]
    alpha = filter_cfg["alpha"]
    w0 = filter_cfg["w0"]

    def __init__(self, file_path: str):
        self.name = os.path.basename(file_path).split('.')[0]
        self._file_path = file_path
        self.raw_data = self._raw_data()
        self.raw_data.columns = self.columns[:3]
        self.raw_data.iloc[:, 0] = np.arange(0, self.raw_data.shape[0]) * self.delta_t
        self.raw_data.iloc[:, 1] += 273.15

    def _raw_data(self):
        df = pd.read_table(self._file_path, delimiter=self.delimiter,
                           encoding=self.encoding, dtype=float)
        return df

    def _get_derivation(self, dw):
        return np.diff(dw, 1) / self.w0 / self.delta_t

    def _butter_filter(self, data: np.ndarray):
        b, a = butter(N=self.N, Wn=self.Wn, btype=self.btype)
        filtered_data = filtfilt(b, a, data)
        filtered_data = pd.Series(filtered_data).ewm(alpha=self.alpha).mean().values

        return filtered_data

    @property
    def data(self):
        raw_DTG = self._get_derivation(self.raw_data.iloc[:, 2])
        filter_TG = self._butter_filter(self.raw_data.iloc[:, 2])
        filter_DTG = self._get_derivation(filter_TG)
        data = self.raw_data.copy(deep=True)
        data.drop(index=self.raw_data.index[-1], inplace=True)

        data[self.columns[3]] = raw_DTG
        data[self.columns[4]] = filter_DTG

        return data






