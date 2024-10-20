# -*- coding: utf-8 -*-
# @Time : 2024/8/27 2:08
# @Author : DanYang
# @File : __init__.py
# @Software : PyCharm
import os
import shutil

WORK_PATH = os.path.dirname(__file__)
DIRS = ["dataset", "plot", "template", "user_data"]
FILES = ["config.json"]

for dirs in DIRS:
    if not os.path.exists(dirs):
        shutil.copytree(os.path.join(WORK_PATH, dirs), dirs)

for file in FILES:
    if not os.path.exists(file):
        shutil.copy(os.path.join(WORK_PATH, file), file)


from .TGAanalyser.DataPloter import run as run