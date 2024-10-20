# -*- coding: utf-8 -*-
# @Time : 2024/8/22 20:10
# @Author : DanYang
# @File : DataPloter.py
# @Software : PyCharm
import sys
import os
from functools import partial
import json
import random
import itertools
import pickle

from PyQt5.QtCore import QUrl, Qt
from PyQt5 import QtGui
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QWidget, \
    QTableWidget, QTableWidgetItem, QAction, QVBoxLayout, QFileDialog, \
    QMessageBox, QInputDialog
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import QObject, pyqtSlot
import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import numpy as np

from .DataProcessor import TGAData

pio.templates.default = "ggplot2"


class Backend(QObject):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    @pyqtSlot()
    def init_param(self):
        with open("config.json", "r") as file:
            config = json.load(file)
        filter_data = config["filter_data"]
        N = filter_data["N"]
        Wn = filter_data["Wn"]
        alpha = filter_data["alpha"]
        self.parent.browser.page().runJavaScript(f"var N = {N};var Wn = {Wn};var alpha = {alpha}")
        x = self.parent.data.data.iloc[:, 1].values.tolist()
        y1 = self.parent.data.data.iloc[:, 3].values.tolist()
        y2 = self.parent.data.data.iloc[:, 4].values.tolist()
        result = json.dumps({"x": x, "y1": y1, "y2": y2})
        self.parent.browser.page().runJavaScript(f"var data = {result}")

    @pyqtSlot(float, float, float)
    def process_request(self, N, Wn, alpha):
        TGAData.N = N
        TGAData.Wn = Wn
        TGAData.alpha = alpha
        with open("config.json", "r") as file:
            config = json.load(file)
        filter_data = config["filter_data"]
        filter_data["N"] = int(N)
        filter_data["Wn"] = Wn
        filter_data["alpha"] = alpha
        with open("config.json", "w") as file:
            json.dump(config, file, indent=3)
        y2 = self.parent.data.data.iloc[:, 4].values.tolist()
        y2 = json.dumps(y2)
        self.parent.browser.page().runJavaScript(f"data.y2 = {y2}")

    @pyqtSlot()
    def init_keypoint(self):
        with open("config.json", "r") as file:
            config = json.load(file)
        key_point_cfg = config["keypoint_select"]
        x = self.parent.data.data.iloc[:, 1].values.tolist()
        y = self.parent.data.data.iloc[:, 4].values.tolist()
        result = json.dumps({"x": x, "y": y})
        for key, value in key_point_cfg.items():
            if not value:
                key_point_cfg[key] = sorted(random.sample(range(len(x)), 3))
            self.parent.browser.page().runJavaScript(f"var {key} = {value}")
        with open("config.json", "w") as file:
            json.dump(config, file, indent=3)
        self.parent.browser.page().runJavaScript(f"var data = {result}")

    @pyqtSlot(str, float, float, float)
    def set_keypoint(self, name, start, middle, end):
        x = self.parent.data.data.iloc[:, 1].values.tolist()
        with open("config.json", "r") as file:
            config = json.load(file)
        key_point_cfg = config["keypoint_select"]
        key_point_cfg[name] = sorted([start, middle, end])
        with open("config.json", "w") as file:
            json.dump(config, file, indent=3)
        values = list(key_point_cfg.values())
        for posi, i in enumerate(values):
            for posj, j in enumerate(values):
                values[posi][posj] = f"{x[int(values[posi][posj])]: .2f}"
        self.parent.update_table(self.parent.table1, values)

    @pyqtSlot()
    def init_range(self):
        with open("config.json", "r") as file:
            config = json.load(file)
        key_point_cfg = config["interval_select"]
        x = self.parent.data.data.iloc[:, 1].values.tolist()
        y = self.parent.data.data.iloc[:, 4].values.tolist()
        result = json.dumps({"x": x, "y": y})
        for key, value in key_point_cfg.items():
            if not value["range"]:
                key_point_cfg[key]["range"] = sorted(random.sample(range(len(x)), 2))
            self.parent.browser.page().runJavaScript(f"var {key} = {value['range']}")
        with open("config.json", "w") as file:
            json.dump(config, file, indent=3)
        self.parent.browser.page().runJavaScript(f"var data = {result}")

    @pyqtSlot(str, float, float)
    def set_range(self, name, start, end):
        self.parent.update_range(name, start, end)
        x = self.parent.data.data.iloc[:, 1].values.tolist()
        with open("config.json", "r") as file:
            config = json.load(file)
        key_point_cfg = config["interval_select"]
        key_point_cfg[name]["range"] = sorted([start, end])
        with open("config.json", "w") as file:
            json.dump(config, file, indent=3)
        values = [i["range"] for i in key_point_cfg.values()]
        for posi, i in enumerate(values):
            for posj, j in enumerate(values):
                values[posi][posj] = f"{x[int(values[posi][posj])]: .3f}"
        for pos in range(5):
            values.append([f"{list(list(key_point_cfg.values())[0]['data'].values())[pos]: .3f}",
                           f"{list(list(key_point_cfg.values())[1]['data'].values())[pos]: .3f}"])
        self.parent.update_table(self.parent.table3, values)


class PlotWindow(QWebEngineView):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        index_path = "template/index.html"
        self.setUrl(QUrl.fromLocalFile(os.path.abspath(index_path)))

    def set_plot(self, html_path: str):
        url = QUrl.fromLocalFile(os.path.abspath(html_path))
        self.setUrl(url)

    def save_screenshot(self, image_path):
        screenshot = self.grab()
        screenshot.save(image_path, "JPG")
        self.parent.plot_save_action.disconnect()


class TableWindow(QTableWidget):
    def __init__(self, width, length):
        super().__init__(width, length)
        self.init_table(width, length)

    def init_table(self, width, length):
        self.setSelectionMode(QTableWidget.ExtendedSelection)
        self.setSelectionBehavior(QTableWidget.SelectItems)
        for i in range(width):
            for j in range(length):
                item = QTableWidgetItem("")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.setItem(i, j, item)

    def set_table_value(self, row, column, value):
        item = QTableWidgetItem(str(value))
        self.setItem(row, column, item)


class ActionBar(QAction):
    def __init__(self, name, parent):
        super().__init__(name, parent)

    def band_action(self, func):
        self.triggered.connect(func)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("XJTU-TGA")
        self.setWindowIcon(QIcon("template/logo.png"))

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        self.menu_bar = self.menuBar()
        self.set_menu()

        self.hbox_layout = QHBoxLayout(central_widget)
        self.set_plot_window()
        self.vbox_table_layout = QVBoxLayout()
        self.set_table_window()
        self.hbox_layout.addLayout(self.vbox_table_layout)
        self.hbox_layout.setStretch(0, 3)
        self.hbox_layout.setStretch(1, 1)

        self.setGeometry(100, 100, 2600, 1600)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        super().resizeEvent(a0)
        self.browser.page().runJavaScript("location.reload()")

    def open_file_dialog(self, file_name=None):
        if not file_name:
            file_name, _ = QFileDialog.getOpenFileName(self, "选择文件", "", "文本文件 (*.txt);;所有文件 (*)")
            if not file_name:
                return
            with open("config.json", "r") as file:
                config = json.load(file)
            config["load_data"]["file_path"] = file_name
            with open("config.json", "w") as file:
                json.dump(config, file, indent=3)
        try:
            self.data = TGAData(file_name)
            self.init_table()
        except (pd.errors.EmptyDataError, pd.errors.ParserError, ValueError):
            message_box = QMessageBox()
            message_box.setIcon(QMessageBox.Warning)
            message_box.setText("导入文件格式错误！")
            message_box.setWindowTitle("错误")
            message_box.exec_()
        except UnicodeDecodeError:
            message_box = QMessageBox()
            message_box.setIcon(QMessageBox.Warning)
            message_box.setText("导入文件编码错误！")
            message_box.setWindowTitle("错误")
            message_box.exec_()
        except FileNotFoundError:
            message_box = QMessageBox()
            message_box.setIcon(QMessageBox.Warning)
            message_box.setText("导入文件不存在！")
            message_box.setWindowTitle("错误")
            message_box.exec_()
        self.goto_index()

    def clean_data(self):
        with open("config.json", "r") as file:
            config = json.load(file)
        for key in config["keypoint_select"].keys():
            config["keypoint_select"][key] = [0, 0, 0]
        config["interval_select"]["coal_pyrolysis"]["range"] = [0, 0]
        config["interval_select"]["carbon_combustion"]["range"] = [0, 0]
        for key in config["parsed_data"].keys():
            config["parsed_data"][key] = 0
        for key in config["interval_select"]["coal_pyrolysis"]["data"].keys():
            config["interval_select"]["coal_pyrolysis"]["data"][key] = 0
        for key in config["interval_select"]["carbon_combustion"]["data"].keys():
            config["interval_select"]["carbon_combustion"]["data"][key] = 0
        with open("config.json", "w") as file:
            json.dump(config, file, indent=3)

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "选择文件", "", "JSON文件 (*.json);;所有文件 (*)")
        if not file_name:
            return
        with open(file_name, "r") as file:
            config = json.load(file)
        with open("config.json", "w") as file:
            json.dump(config, file, indent=3)
        self.open_file_dialog(file_name=config["load_data"]["file_path"])
        self.setWindowTitle(f"XJTU-TGA: {os.path.splitext(os.path.basename(file_name))[0]}")
        self.goto_index()

    def save_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_name, _ = QFileDialog.getSaveFileName(self,
                                                   '保存文件',
                                                   '',
                                                   'JSON文件 (*.json);;所有文件 (*)',
                                                   options=options)
        if not file_name:
            return
        if os.path.abspath("./config.json") == os.path.abspath(file_name):
            message_box = QMessageBox()
            message_box.setIcon(QMessageBox.Warning)
            message_box.setText("不可以在根目录下保存为config.json！")
            message_box.setWindowTitle("错误")
            message_box.exec_()
            return
        with open("config.json", "r") as file:
            config = json.load(file)
        with open(file_name, "w") as file:
            json.dump(config, file, indent=3)
        with open('.'.join(file_name.split('.')[:-1]) + ".pkl", "wb") as file:
            pickle.dump(self.data.data, file)

    def butter_param_select(self):
        self.channel = QWebChannel()
        self.backend = Backend(self)
        self.channel.registerObject("backend", self.backend)
        self.browser.page().setWebChannel(self.channel)
        if not self.judge_import_file():
            return
        self.browser.set_plot("./template/filter_choose.html")
        self.plot_save_action.band_action(partial(self.browser.save_screenshot, image_path="plot/DTG_param_select.jpg"))

    def keypoint_select(self):
        self.channel = QWebChannel()
        self.backend = Backend(self)
        self.channel.registerObject("backend", self.backend)
        self.browser.page().setWebChannel(self.channel)
        if not self.judge_import_file():
            return
        self.browser.set_plot("./template/point_choose.html")
        self.plot_save_action.band_action(
            partial(self.browser.save_screenshot, image_path="plot/DTG_keypoint_select.jpg"))

    def range_select(self):
        self.channel = QWebChannel()
        self.backend = Backend(self)
        self.channel.registerObject("backend", self.backend)
        self.browser.page().setWebChannel(self.channel)
        if not self.judge_import_file():
            return
        self.browser.set_plot("./template/range_choose.html")
        self.plot_save_action.band_action(
            partial(self.browser.save_screenshot, image_path="plot/DTG_range_select.jpg"))

    def init_table(self):
        with open("config.json", "r") as file:
            config = json.load(file)
        if config["filter_data"]["w0"] <= 0:
            self.select_w0()
        x = self.data.data.iloc[:, 1].values.tolist()
        key_point_cfg = config["keypoint_select"]
        interval_cfg = config["interval_select"]
        parse_data = config["parsed_data"]
        table_data = [[f"{parse_data['Ti']: .2f}"], [f"{parse_data['Tf']: .2f}"], [f"{parse_data['Tp']: .2f}"],
                      [f"{parse_data['Vp']: .2e}"], [f"{parse_data['Vmean']: .2e}"]]
        values = list(key_point_cfg.values())
        for posi, i in enumerate(values):
            for posj, j in enumerate(i):
                values[posi][posj] = f"{x[int(values[posi][posj])]: .2f}"
        interval_value = np.zeros((7, 2))
        for posi in range(7):
            for posj in range(2):
                if posi < 2:
                    interval_value[posi][posj] = f"{x[int(list(interval_cfg.values())[posj]['range'][posi])]: .3f}"
                else:
                    interval_value[posi][posj] = f"{list(list(interval_cfg.values())[posj]['data'].values())[posi - 2]: .3f}"
        self.update_table(self.table1, values)
        self.update_table(self.table2, table_data)
        self.update_table(self.table3, interval_value)

    def set_plot_window(self):
        self.browser = PlotWindow(self)
        self.hbox_layout.addWidget(self.browser)

    def update_table(self, table, array):
        w, h = len(array), len(array[0])
        for i, j in list(itertools.product(range(w), range(h))):
            value = array[i][j]
            table.set_table_value(i, j, value)

    def set_table_window(self):
        self.table1 = TableWindow(3, 4)
        self.table1.setVerticalHeaderLabels(["水蒸发", "煤热解", "碳燃烧"])
        self.table1.setHorizontalHeaderLabels(["开始", "剧烈", "结束", "单位"])
        self.table1.set_table_value(0, 3, "K")
        self.table1.set_table_value(1, 3, "K")
        self.table1.set_table_value(2, 3, "K")
        self.vbox_table_layout.addWidget(self.table1)

        self.table2 = TableWindow(5, 2)
        self.table2.setVerticalHeaderLabels(["Ti", "Tf", "Tp", "Vp", "Vmean"])
        self.table2.setHorizontalHeaderLabels(["数值", "单位"])
        self.table2.set_table_value(0, 1, "K")
        self.table2.set_table_value(1, 1, "K")
        self.table2.set_table_value(2, 1, "K")
        self.table2.set_table_value(3, 1, "%/s")
        self.table2.set_table_value(4, 1, "%/min")
        self.vbox_table_layout.addWidget(self.table2)

        self.table3 = TableWindow(7, 3)
        self.table3.setVerticalHeaderLabels(["Tmin", "Tmax", "A", "b", "R", "E", "k0"])
        self.table3.setHorizontalHeaderLabels(["煤热解", "碳燃烧", "单位"])
        self.table3.set_table_value(0, 2, "K")
        self.table3.set_table_value(1, 2, "K")
        self.table3.set_table_value(2, 2, "/")
        self.table3.set_table_value(3, 2, "/")
        self.table3.set_table_value(4, 2, "/")
        self.table3.set_table_value(5, 2, "kJ/mol")
        self.table3.set_table_value(6, 2, "/")
        self.vbox_table_layout.addWidget(self.table3)

    def select_w0(self):
        with open("config.json", "r") as file:
            config = json.load(file)
        w0 = config["filter_data"]["w0"]
        num, ok = QInputDialog.getDouble(self, '输入w0', '请输入w0(mg):', value=w0)

        if ok:
            config["filter_data"]["w0"] = num
            with open("config.json", "w") as file:
                json.dump(config, file, indent=3)
            TGAData.w0 = num

    def goto_index(self):
        self.browser.set_plot("template/index.html")

    def open_select(self):
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(self,
                                                "选择一个或多个文件",
                                                "",
                                                "JSON文件 (*.json);;所有文件 (*)",
                                                options=options)
        if not files:
            return
        self.range_split_datas = []
        self.range_datas = []
        self.names = []
        for file in files:
            with open(file, "r") as f:
                config = json.load(f)
            with open('.'.join(file.split('.')[:-1]) + ".pkl", "rb") as f:
                data = pickle.load(f)
            range_data = [config["interval_select"]["coal_pyrolysis"]["range"],
                          config["interval_select"]["carbon_combustion"]["range"]]
            self.range_split_datas.append(range_data)
            self.range_datas.append(data)
            self.names.append(os.path.splitext(os.path.basename(file))[0])

    def goto_help(self):
        self.browser.set_plot("template/help.html")

    def set_menu(self):
        file_menu = self.menu_bar.addMenu("文件")
        filter_menu = self.menu_bar.addMenu("滤波")
        point_menu = self.menu_bar.addMenu("特征")
        plot_menu = self.menu_bar.addMenu("绘图")
        help_action = ActionBar("帮助", self)
        help_action.band_action(self.goto_help)
        self.menu_bar.addAction(help_action)

        index_action = ActionBar("主页", self)
        index_action.band_action(self.goto_index)
        import_action = ActionBar('导入', self)
        import_action.band_action(self.open_file_dialog)
        clean_action = ActionBar("重置", self)
        clean_action.band_action(self.clean_data)
        open_action = ActionBar('打开', self)
        open_action.band_action(self.open_file)
        select_action = ActionBar("采集", self)
        select_action.band_action(self.open_select)
        save_action = ActionBar('保存', self)
        save_action.band_action(self.save_file)
        butter_action = ActionBar("参数选择", self)
        butter_action.band_action(self.butter_param_select)
        W0_action = ActionBar("w0输入", self)
        W0_action.band_action(self.select_w0)
        character_action = ActionBar("特征点选择", self)
        character_action.band_action(self.keypoint_select)
        corridor_action = ActionBar("动力区间选择", self)
        corridor_action.band_action(self.range_select)
        TG_plot_action = ActionBar("TG-T", self)
        TG_plot_action.band_action(self.TG_plot)
        DTG_plot_action = ActionBar("DTG-T", self)
        DTG_plot_action.band_action(self.DTG_plot)
        DTG_TG_plot_action = ActionBar("DTG-TG-T", self)
        DTG_TG_plot_action.band_action(self.DTG_TG_plot)
        union_pyrolysis_action = ActionBar("煤热解动力区间绘图", self)
        union_pyrolysis_action.band_action(self.coal_pyrolysis_union_plot)
        union_burn_action = ActionBar("碳燃烧动力区间绘图", self)
        union_burn_action.band_action(self.carbon_combustion_union_plot)
        self.plot_save_action = ActionBar("保存当前图像", self)

        file_menu.addAction(index_action)
        file_menu.addSeparator()
        file_menu.addAction(import_action)
        file_menu.addAction(open_action)
        file_menu.addAction(select_action)
        file_menu.addSeparator()
        file_menu.addAction(save_action)
        file_menu.addAction(clean_action)

        filter_menu.addAction(butter_action)
        filter_menu.addSeparator()
        filter_menu.addAction(W0_action)

        point_menu.addAction(character_action)
        file_menu.addSeparator()
        point_menu.addAction(corridor_action)

        plot_menu.addAction(TG_plot_action)
        plot_menu.addAction(DTG_plot_action)
        plot_menu.addAction(DTG_TG_plot_action)
        plot_menu.addSeparator()
        plot_menu.addAction(union_pyrolysis_action)
        plot_menu.addAction(union_burn_action)
        plot_menu.addSeparator()
        plot_menu.addAction(self.plot_save_action)

    def update_range(self, name, start, end):
        with open("config.json", "r") as file:
            config = json.load(file)
        value = config["interval_select"][name]["data"]
        if start > end:
            start, end = end, start
        x = 1 / self.data.data.iloc[:, 1].values[int(start): int(end)]
        y = np.log(np.abs(self.data.data.iloc[:, 4].values[int(start): int(end)]))
        A, b, *_ = np.polyfit(x, y, 1)
        y_pred = A * x + b
        ss_res = np.sum((y - y_pred) ** 2)  # 残差平方和
        ss_tot = np.sum((y - np.mean(y)) ** 2)  # 总体平方和
        R = 1 - (ss_res / ss_tot)
        E = 8.314 * -A
        k0 = np.exp(b)
        value["A"] = -A
        value["b"] = b
        value["E"] = E / 1000
        value["k0"] = k0
        value["R"] = R
        with open("config.json", "w") as file:
            json.dump(config, file, indent=3)

    def judge_import_file(self):
        try:
            self.data
            return True
        except AttributeError:
            message_box = QMessageBox()
            message_box.setIcon(QMessageBox.Warning)
            message_box.setText("请先导入文件！")
            message_box.setWindowTitle("错误")
            message_box.exec_()
            return False

    def judge_union_file(self):
        try:
            self.names
            return True
        except AttributeError:
            message_box = QMessageBox()
            message_box.setIcon(QMessageBox.Warning)
            message_box.setText("请先采集配置文件！")
            message_box.setWindowTitle("错误")
            message_box.exec_()
            return False

    def TG_plot(self):
        if not self.judge_import_file():
            return
        x = self.data.data.iloc[:, 1]
        y = self.data.data.iloc[:, 2]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=y, mode='lines', name='TG'))
        fig.update_layout(
            title={"text": "TG-T", "font": {"size": 50, "family": "Times New Roman"}},
            xaxis_title={"text": "T/K", "font": {"size": 40, "family": "Times New Roman"}},
            yaxis_title={"text": "TG/mg", "font": {"size": 40, "family": "Times New Roman"}}
        )
        fig.update_xaxes(
            tickfont=dict(
                size=30,
                family="Times New Roman"
            )
        )
        fig.update_yaxes(
            tickfont=dict(
                size=30,
                family="Times New Roman"
            )
        )
        fig.update_layout(
            legend=dict(
                font=dict(
                    size=30,
                    family="Times New Roman"
                )
            )
        )
        fig.write_html("plot/TG-T.html")
        self.browser.set_plot("plot/TG-T.html")
        self.plot_save_action.band_action(partial(self.browser.save_screenshot, image_path="plot/TG-T.jpg"))

    def DTG_plot(self):
        if not self.judge_import_file():
            return
        with open("config.json", "r") as file:
            keypoint_cfg = json.load(file)["keypoint_select"]
        x = self.data.data.iloc[:, 1]
        y1 = self.data.data.iloc[:, 3]
        y2 = self.data.data.iloc[:, 4]
        y2_min = min(y2)
        y2_max = max(y2)
        y2_range = y2_max - y2_min
        y2_ranges = [y2_min - y2_range / 20, y2_max + y2_range / 20]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=y1, mode='lines', name='raw DTG',
                                 line=dict(color='rgba(0, 0, 255, 0.25)', width=1.5)))
        fig.add_trace(go.Scatter(x=x, y=y2, mode='lines', name="filter DTG",
                                 line=dict(color="rgba(255, 0, 0, 1)", width=2)))
        colors = ["LightSkyBlue", "SaddleBrown", "DarkSlateGray"]
        names = ["水蒸发", "煤热解", "碳燃烧"]
        for pos, i in enumerate(keypoint_cfg.values()):
            fig.add_shape(
                type="rect",
                x0=x[min(i)],  # 起始x坐标
                x1=x[max(i)],  # 结束x坐标
                y0=y2_ranges[0],  # y轴下边界（可以是图表中的最小值或一个固定值）
                y1=y2_ranges[1],  # y轴上边界（可以是图表中的最大值或一个固定值）
                fillcolor=colors[pos],  # 填充颜色
                opacity=0.35,  # 透明度
                line=dict(
                    color="black",  # 边框颜色
                    width=2,  # 边框宽度
                    dash="dashdot"  # 边框样式：'solid', 'dot', 'dash', 'dashdot'
                )
            )
            fig.add_trace(go.Scatter(
                x=[x[j] for j in i],
                y=[y2[j] for j in i],
                mode="markers",
                marker=dict(
                    size=20,
                    color=colors[pos],
                    symbol="x"
                ),
                name=names[pos]
            ))
            fig.add_annotation(
                x=(x[min(i)] + x[max(i)]) / 2,  # x 轴位置
                y=y2_ranges[1] - y2_range / 20,  # y 轴位置
                text=names[pos] + "区域",  # 要显示的文字
                font=dict(
                    size=30,  # 文字大小
                    color="black",
                    family="Times New Roman"
                ),
                align="center"
            )
        fig.update_layout(
            title={"text": "DTG-T", "font": {"size": 50, "family": "Times New Roman"}},
            xaxis_title={"text": "T/K", "font": {"size": 40, "family": "Times New Roman"}},
            yaxis_title={"text": "DTG/s<sup>-1</sup>", "font": {"size": 40, "family": "Times New Roman"}}
        )
        fig.update_xaxes(
            tickfont=dict(
                size=30,
                family="Times New Roman"
            )
        )
        fig.update_yaxes(
            range=y2_ranges,
            tickfont=dict(
                size=30,
                family="Times New Roman"
            )
        )
        fig.update_layout(
            legend=dict(
                font=dict(
                    size=30,
                    family="Times New Roman"
                )
            )
        )
        fig.write_html("plot/DTG-T.html")
        self.browser.set_plot("plot/DTG-T.html")
        self.plot_save_action.band_action(partial(self.browser.save_screenshot, image_path="plot/DTG-T.jpg"))

    def parse_DTG_data(self):
        with open("config.json", "r") as file:
            config = json.load(file)
            keypoint_cfg = config["keypoint_select"]
            w0 = config["filter_data"]["w0"]

        x = self.data.data.iloc[:, 1].values
        t = self.data.data.iloc[:, 0].values
        y1 = self.data.data.iloc[:, 2].values
        y2 = self.data.data.iloc[:, 4].values

        argmin_y2 = np.argmin(y2)
        Tp = x[argmin_y2]
        Vp = y2[argmin_y2]
        beta = (x[-1] - x[0]) / (len(t) - 1) * (60 / TGAData.delta_t)
        A = (Tp, y1[argmin_y2])
        k = ((y1[argmin_y2 + 5] - y1[argmin_y2 - 5]) / (x[argmin_y2 + 5] - x[argmin_y2 - 5])).mean()
        self.yL1 = y1[int(keypoint_cfg["coal_pyrolysis"][0])]
        self.yL2 = y1[int(keypoint_cfg["carbon_combustion"][-1])]
        Ti = (self.yL1 - A[1]) / k + A[0]
        Tf = (self.yL2 - A[1]) / k + A[0]
        ai = self.yL1 / w0 + 1
        af = self.yL2 / w0 + 1
        Vmean = beta * (ai - af) / (Tf - Ti)

        config["parsed_data"] = {
            "Ti": Ti,
            "Tf": Tf,
            "Tp": Tp,
            "Vp": Vp * 100,
            "Vmean": Vmean * 100
        }
        with open("config.json", "w") as file:
            json.dump(config, file, indent=3)
        table_data = [[f"{Ti: .2f}"], [f"{Tf: .2f}"], [f"{Tp: .2f}"],
                      [f"{Vp * 100: .2e}"], [f"{Vmean * 100: .2e}"]]
        self.update_table(self.table2, table_data)
        return config["parsed_data"]

    def DTG_TG_plot(self):
        if not self.judge_import_file():
            return
        with open("config.json", "r") as file:
            config = json.load(file)
            keypoint_cfg = config["keypoint_select"]
        parse_data = self.parse_DTG_data()
        x = self.data.data.iloc[:, 1]
        y1 = self.data.data.iloc[:, 2]
        y2 = self.data.data.iloc[:, 4]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=y1, mode='lines', name='TG',
                                 line=dict(color='rgba(255, 0, 0, 1)', width=2)))
        fig.add_trace(go.Scatter(x=x, y=y2, mode='lines', name="DTG",
                                 line=dict(color="rgba(0, 0, 255, 1)", width=2, dash="dash"), yaxis='y2'))
        fig.add_trace(go.Scatter(x=[parse_data["Ti"], parse_data["Tf"]], y=[self.yL1, self.yL2],
                                 mode="lines", line=dict(width=1, dash="dashdot", color="black"), showlegend=False))
        fig.add_trace(go.Scatter(x=[x[int(keypoint_cfg["coal_pyrolysis"][0])], parse_data["Ti"]],
                                 y=[self.yL1, self.yL1],
                                 mode="lines", line=dict(width=1, dash="dashdot", color="black"), showlegend=False))
        fig.add_trace(go.Scatter(x=[parse_data["Tf"], x[int(keypoint_cfg["carbon_combustion"][-1])]],
                                 y=[self.yL2, self.yL2],
                                 mode="lines", line=dict(width=1, dash="dashdot", color="black"), showlegend=False))
        fig.add_annotation(
            x=parse_data["Ti"],
            y=self.yL1,
            text="i",
            font=dict(
                size=30,
                color="black",
                family="Times New Roman"
            ),
            align="center",
            yanchor="middle"
        )
        fig.add_annotation(
            x=parse_data["Tf"],
            y=self.yL2,
            text="f",
            font=dict(
                size=30,
                color="black",
                family="Times New Roman"
            ),
            align="center",
            yanchor="middle"
        )
        fig.update_layout(
            yaxis2=dict(
                tickfont=dict(
                    size=30,
                    family="Times New Roman",
                    color="blue"
                ),
                title={"text": "DTG/s<sup>-1</sup>", "font": {"size": 40, "family": "Times New Roman"}},
                titlefont=dict(color='blue'),
                overlaying='y',
                side='right',
                showgrid=False
            ),
            xaxis=dict(
                tickfont=dict(
                    size=30,
                    family="Times New Roman"
                ),
                title={"text": "T/K", "font": {"size": 40, "family": "Times New Roman"}}
            ),
            yaxis=dict(
                tickfont=dict(
                    size=30,
                    family="Times New Roman",
                    color="red"
                ),
                title={"text": "TG/mg", "font": {"size": 40, "family": "Times New Roman"}},
                titlefont=dict(color='red'),
            ),
            title={"text": "DTG/TG-T", "font": {"size": 50, "family": "Times New Roman"}}
        )
        fig.update_layout(
            legend=dict(
                font=dict(
                    size=30,
                    family="Times New Roman"
                )
            )
        )
        fig.write_html("plot/DTG-TG-T.html")
        self.browser.set_plot("plot/DTG-TG-T.html")
        self.plot_save_action.band_action(partial(self.browser.save_screenshot, image_path="plot/DTG-TG-T.jpg"))

    def coal_pyrolysis_union_plot(self):
        if not self.judge_union_file():
            return
        fig = go.Figure()
        colors = [
            '#636EFA',  # 蓝色
            '#EF553B',  # 橙红色
            '#00CC96',  # 青绿色
            '#AB63FA',  # 紫色
            '#FFA15A',  # 浅橙色
            '#19D3F3',  # 天蓝色
            '#FF6692',  # 粉红色
            '#B6E880',  # 浅绿色
            '#FF97FF',  # 浅紫色
            '#FECB52'  # 黄色
        ]
        for pos, (ran, data, name) in enumerate(zip(self.range_split_datas, self.range_datas, self.names)):
            x = data.iloc[:, 4].values[int(ran[0][0]): int(ran[0][1])]
            y = data.iloc[:, 1].values[int(ran[0][0]): int(ran[0][1])]
            k = np.polyfit(x, y, 1)
            x0 = [min(x), max(x)]
            y0 = np.polyval(k, x0)
            fig.add_trace(go.Scatter(x=x, y=y, mode='lines', name=name,
                                 line=dict(color=colors[pos], width=1.5, dash="dash")))
            fig.add_trace(go.Scatter(x=x0, y=y0, mode='lines', name=name + " fit",
                                     line=dict(color=colors[pos], width=2)))
        fig.update_layout(
            title={"text": "Coal Pyrolysis Union", "font": {"size": 50, "family": "Times New Roman"}},
            xaxis_title={"text": "T<sup>-1</sup>/K<sup>-1</sup>", "font": {"size": 40, "family": "Times New Roman"}},
            yaxis_title={"text": "ln(DTG)/~", "font": {"size": 40, "family": "Times New Roman"}}
        )
        fig.update_xaxes(
            tickfont=dict(
                size=30,
                family="Times New Roman"
            )
        )
        fig.update_yaxes(
            tickfont=dict(
                size=30,
                family="Times New Roman"
            )
        )
        fig.update_layout(
            legend=dict(
                font=dict(
                    size=30,
                    family="Times New Roman"
                )
            )
        )
        fig.write_html("plot/coal_pyrolysis_union.html")
        self.browser.set_plot("plot/coal_pyrolysis_union.html")
        self.plot_save_action.band_action(partial(self.browser.save_screenshot, image_path="plot/coal_pyrolysis_union.jpg"))

    def carbon_combustion_union_plot(self):
        if not self.judge_union_file():
            return
        fig = go.Figure()
        colors = [
            '#636EFA',  # 蓝色
            '#EF553B',  # 橙红色
            '#00CC96',  # 青绿色
            '#AB63FA',  # 紫色
            '#FFA15A',  # 浅橙色
            '#19D3F3',  # 天蓝色
            '#FF6692',  # 粉红色
            '#B6E880',  # 浅绿色
            '#FF97FF',  # 浅紫色
            '#FECB52'  # 黄色
        ]
        for pos, (ran, data, name) in enumerate(zip(self.range_split_datas, self.range_datas, self.names)):
            x = data.iloc[:, 4].values[int(ran[1][0]): int(ran[1][1])]
            y = data.iloc[:, 1].values[int(ran[1][0]): int(ran[1][1])]
            k = np.polyfit(x, y, 1)
            x0 = [min(x), max(x)]
            y0 = np.polyval(k, x0)
            fig.add_trace(go.Scatter(x=x, y=y, mode='lines', name=name,
                                     line=dict(color=colors[pos], width=1.5, dash="dash")))
            fig.add_trace(go.Scatter(x=x0, y=y0, mode='lines', name=name + " fit",
                                     line=dict(color=colors[pos], width=2)))
        fig.update_layout(
            title={"text": "Carbon Combustion Union", "font": {"size": 50, "family": "Times New Roman"}},
            xaxis_title={"text": "T<sup>-1</sup>/K<sup>-1</sup>", "font": {"size": 40, "family": "Times New Roman"}},
            yaxis_title={"text": "ln(DTG)/~", "font": {"size": 40, "family": "Times New Roman"}}
        )
        fig.update_xaxes(
            tickfont=dict(
                size=30,
                family="Times New Roman"
            )
        )
        fig.update_yaxes(
            tickfont=dict(
                size=30,
                family="Times New Roman"
            )
        )
        fig.update_layout(
            legend=dict(
                font=dict(
                    size=30,
                    family="Times New Roman"
                )
            )
        )
        fig.write_html("plot/carbon_combustion_union.html")
        self.browser.set_plot("plot/carbon_combustion_union.html")
        self.plot_save_action.band_action(
            partial(self.browser.save_screenshot, image_path="plot/carbon_combustion_union.jpg"))


def run():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
