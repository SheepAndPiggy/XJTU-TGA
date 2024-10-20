# -*- coding: utf-8 -*-
# @Time : 2024/8/27 1:24
# @Author : DanYang
# @File : setup.py
# @Software : PyCharm
from setuptools import setup, find_packages

setup(
    name='XJTU-TGA',
    version='0.1.9',
    packages=find_packages(),
    install_requires=[
        'numpy>=1.21.0',
        'scipy>=1.7.0',
        'pandas>=1.3.0',
        'PyQt5>=5.15.0',
        'PyQtWebEngine>=5.15.0',
        'plotly>=5.0.0',
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    include_package_data=True,
    package_data={
        'XJTU-TGA': ['dataset/*', 'plot/*', 'template/**/*', 'user_data/*', 'config.json', 'image/*'],
    },
    python_requires='>=3.6',
    zip_safe=False,
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown"
)
