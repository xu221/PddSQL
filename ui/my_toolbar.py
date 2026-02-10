import wx

class MyToolBar(wx.ToolBar):
    def __init__(self, parent):
        super(MyToolBar, self).__init__(parent)
        # 左侧弹簧
        self.AddStretchableSpace()

        # 添加工具栏按钮
        new_tool = self.AddTool(wx.ID_NEW, "New", wx.ArtProvider.GetBitmap(wx.ART_NEW, wx.ART_TOOLBAR))
        open_tool = self.AddTool(wx.ID_OPEN, "Open", wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN, wx.ART_TOOLBAR))
        save_tool = self.AddTool(wx.ID_SAVE, "Save", wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE, wx.ART_TOOLBAR))

        # 右侧弹簧
        self.AddStretchableSpace()

        # 实现工具栏
        self.Realize()

        # 将工具栏设置到父框架
        parent.SetToolBar(self)

        # 绑定工具栏按钮事件
        parent.Bind(wx.EVT_TOOL, self.on_new, new_tool)
        parent.Bind(wx.EVT_TOOL, self.on_open, open_tool)
        parent.Bind(wx.EVT_TOOL, self.on_save, save_tool)

    def on_new(self, event):
        wx.MessageBox("New file created", "Info", wx.OK | wx.ICON_INFORMATION)

    def on_open(self, event):
        wx.MessageBox("Open file dialog", "Info", wx.OK | wx.ICON_INFORMATION)

    def on_save(self, event):
        wx.MessageBox("File saved", "Info", wx.OK | wx.ICON_INFORMATION)