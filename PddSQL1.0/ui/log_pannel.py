import wx
from ui.utils import SQLTextEditor
from datetime import datetime

class LogPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)

        # 创建日志框
        self.log_ctrl = SQLTextEditor(self)
        self.log_ctrl.SetLexer(wx.stc.STC_LEX_SQL)
        self.log_ctrl.StyleSetForeground(wx.stc.STC_SQL_COMMENT, wx.Colour(128, 128, 128))  # 灰色注释
        self.log_ctrl.StyleSetForeground(wx.stc.STC_SQL_STRING, wx.Colour(0, 128, 0))       # 绿洲字符串
        self.log_ctrl.StyleSetForeground(wx.stc.STC_SQL_WORD, wx.Colour(0, 0, 255))
        self.log_ctrl.SetReadOnly(True)
        # 使用 BoxSizer 布局
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.log_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)

    def append_normal_log(self, message):
        """追加普通日志，使用默认字体颜色"""
        self.log_ctrl.SetForegroundColour("gray")  # 设置普通日志颜色
        self.log_ctrl.AppendText(message + "\n")

    def append_special_log(self, message, level):
        """追加带有特殊格式的日志（例如加上时间戳），并改变字体颜色"""
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        formatted_message = f"{timestamp} [{level}] {message}\n"
        self.log_ctrl.SetReadOnly(False)
        self.log_ctrl.AppendText(formatted_message)
        self.log_ctrl.SetReadOnly(True)