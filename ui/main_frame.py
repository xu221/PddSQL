import wx
from ui.menubar import MyMenuBar
from ui.dbtree_panel import LeftPanel
from ui.sql_panel import RightPanelTop
from ui.session_panel import RightPanelBottom
from ui.log_pannel import LogPanel

class MainFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super(MainFrame, self).__init__(*args, **kw)

        # 创建菜单栏
        self.menu_bar = MyMenuBar(self)

        # 创建状态栏
        self.status_bar = self.CreateStatusBar()

        # ========== 创建最外层的 SplitterWindow （内容区 + 日志框）=============
        self.outer_splitter = wx.SplitterWindow(self)
        container_splitter = wx.SplitterWindow(self.outer_splitter)
        self.log_panel = LogPanel(self.outer_splitter)

        # ========== 主内容区域 ==============================================
        self.left_panel = LeftPanel(container_splitter) 
        right_splitter = wx.SplitterWindow(container_splitter)              
        self.right_panel_top = RightPanelTop(right_splitter)
        self.right_panel_bottom = RightPanelBottom(right_splitter)           
        right_splitter.SplitHorizontally(self.right_panel_top, self.right_panel_bottom)
        right_splitter.SetMinimumPaneSize(250)
        container_splitter.SplitVertically(self.left_panel, right_splitter)
        container_splitter.SetSashPosition(400)
        container_splitter.SetMinimumPaneSize(400)

        # ========== 最外层的 SplitterWindow水平分割 ===========================
        self.outer_splitter.SplitHorizontally(container_splitter, self.log_panel)
        self.outer_splitter.SetSashGravity(1.0)
        self.outer_splitter.SetSashPosition(500)  # 日志框默认最小
        self.outer_splitter.SetMinimumPaneSize(150) 

        # 设置窗口尺寸
        self.SetSize((1450, 870))
        self.Centre()