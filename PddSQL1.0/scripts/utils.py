import sys
import os

def resource_path(relative_path):
    """获取资源文件路径, 兼容打包和开发环境"""
    if hasattr(sys, '_MEIPASS'):  # PyInstaller 解包目录
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    # print(os.path.join(base_path, relative_path))
    # print(os.path.join(base_path, *relative_path.split("/")))
    return os.path.join(base_path, relative_path)



