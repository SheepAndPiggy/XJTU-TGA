# -*- coding: utf-8 -*-
# @Time : 2024/8/8 22:29
# @Author : DanYang
# @File : __init__.py.py
# @Software : PyCharm
import json

with open("config.json", "r") as file:
    CONFIG = json.load(file)
