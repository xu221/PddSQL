import wx
import pymysql
import threading
from ui.dialogs import InstanceManager


class MyMenuBar(wx.MenuBar):
    def __init__(self, parent):
        super(MyMenuBar, self).__init__()

        # 创建文件菜单
        filemenu = wx.Menu()
        self.menu_item_manage_instances = filemenu.Append(wx.ID_ANY, "实例管理器", "打开实例管理器")
        filemenu.Append(wx.ID_ABOUT, "关于", "关于程序的信息")
        filemenu.AppendSeparator()
        filemenu.Append(wx.ID_EXIT, "退出", "终止应用程序")

        # 将菜单添加到菜单栏
        self.Append(filemenu, u"文件")

        # 将菜单栏设置到父框架
        parent.SetMenuBar(self)
        
        # 绑定菜单事件
        parent.Bind(wx.EVT_MENU, self.on_open_instance_manager, self.menu_item_manage_instances)
        parent.Bind(wx.EVT_MENU, self.on_about, id=wx.ID_ABOUT)
        parent.Bind(wx.EVT_MENU, self.on_exit, id=wx.ID_EXIT)
        self.frame_index = parent

    def on_open_instance_manager(self, event):
        # 打开实例管理器窗口
        instance_manager = InstanceManager(self.frame_index)
        if instance_manager.ShowModal() == wx.ID_OK:
            selected_instance = instance_manager.selected_instance
            print(selected_instance)
            if selected_instance:
                threading.Thread(target=self.connect_to_database, args=(selected_instance,), daemon=True).start()
                instance_manager.Destroy()
            event.Skip()
        
    def connect_to_database(self, selected_instance):
        """在后台线程中连接数据库"""
        database_config = {
            "host": selected_instance.get("instance_addr"),
            "port": selected_instance.get("instance_port"),
            "user": selected_instance.get("instance_user"),
            "password": selected_instance.get("instance_pswd"),
            "charset": "utf8mb4",
            "cursorclass": pymysql.cursors.DictCursor,
            "database": None,
        }
        print(database_config["host"])
        try:
            wx.CallAfter(wx.GetApp().frame.log_panel.append_special_log, f"/* 正在连接 {database_config['host']} ... */", "INFO")
            connection = pymysql.connect(**database_config)
            connection.ping()
        except Exception as e:
            wx.CallAfter(wx.GetApp().frame.log_panel.append_special_log, f"/* 链接失败 {database_config['host']} , {str(e)} */", "ERROR")
        else:
            wx.CallAfter(wx.GetApp().change_instance, selected_instance)
            wx.CallAfter(self.frame_index.left_panel.add_instance_tree, selected_instance)
            wx.CallAfter(wx.GetApp().frame.log_panel.append_special_log, f"\"     已连接 {database_config['host']} ... \"", "INFO")

    def on_about(self, event):
        wx.MessageBox("PDDSQL 1.0", "关于", wx.OK | wx.ICON_INFORMATION)

    def on_exit(self, event):
        self.GetParent().Close()