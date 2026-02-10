import wx
import threading
import pymysql
from ui.utils import SQLTextEditor
from ui.dialogs import DatabaseGridDialog
from scripts.db import extract_table_name_ddl, online_schema_change
import sqlglot


class RightPanelTop(wx.Panel):
    def __init__(self, parent):
        super(RightPanelTop, self).__init__(parent)
        # 创建 wx.Notebook 控件
        self.notebook = wx.Notebook(self)
        # 添加初始标签页
        self.notebook.AddPage(MyTabPanel(self.notebook, "Tab 1"), "Tab 1")
        self.notebook.AddPage(MyTabPanel(self.notebook, "Tab 2"), "Tab 2")
        # 添加 "添加标签页","删除标签页" 的占位标签页
        self.add_tab_placeholder = "+"
        self.del_tab_placeholder = "-"
        self.notebook.AddPage(wx.Panel(self.notebook), self.add_tab_placeholder)
        self.notebook.AddPage(wx.Panel(self.notebook), self.del_tab_placeholder)

        # 绑定事件处理
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_page_changed)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 0)

        self.SetSizer(main_sizer)

    def on_page_changed(self, event):
        notebook = self.notebook
        old_selection = event.GetOldSelection()
        new_selection = event.GetSelection()

        # 检查是否选择了最后一个标签页
        if notebook.GetPageText(new_selection) == self.add_tab_placeholder:
            self.add_new_tab(old_selection)
            print("+")
        if notebook.GetPageText(new_selection) == self.del_tab_placeholder:
            self.del_cur_tab(old_selection)
            print("-")
        event.Skip()

    def add_new_tab(self, old_selection):
        notebook = self.notebook

        new_page_number = int(notebook.GetPageText(old_selection).split(" ")[1]) + 1
        page_label = f"Tab {new_page_number}"
        new_panel = MyTabPanel(notebook, page_label)  
        notebook.InsertPage(old_selection+1, new_panel, page_label)
        notebook.SetSelection(old_selection+1)

    def del_cur_tab(self, old_selection):
        notebook = self.notebook
        
        # 不允许删除占位符页
        if notebook.GetPageText(old_selection) == self.add_tab_placeholder:
            wx.MessageBox("无法删除“添加标签页”占位符页", "提示", wx.OK | wx.ICON_INFORMATION)
            return
        
        # 删除当前选中的标签页
        if notebook.GetPageCount() > 3:  # 至少保留一个标签页和占位符
            notebook.DeletePage(old_selection)
        
        # 切换到前一个标签页
        if notebook.GetPageCount() > 1:
            notebook.SetSelection(max(0, old_selection - 1))


class MyTabPanel(wx.Panel):
    def __init__(self, parent, label):
        super(MyTabPanel, self).__init__(parent)
        
        self.text_ctrl = SQLTextEditor(self)

        # 创建右键菜单
        self.menu = wx.Menu()
        self.execute_direct_item = self.menu.Append(wx.ID_ANY, "执行选中的部分")
        self.execute_osc_item = self.menu.Append(wx.ID_ANY, "执行选中的部分[无锁变更]")
        self.beauty_sql_item = self.menu.Append(wx.ID_ANY, "美化SQL")
        self.Bind(wx.EVT_MENU, lambda event: self.execute_sql_ui("direct"), self.execute_direct_item)
        self.Bind(wx.EVT_MENU, lambda event: self.execute_sql_ui("online_schema_change"), self.execute_osc_item)
        self.Bind(wx.EVT_MENU, lambda event: self.format_sql(), self.beauty_sql_item)
        self.text_ctrl.Bind(wx.EVT_CONTEXT_MENU, self.on_right_click)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.text_ctrl, 1, wx.ALL | wx.EXPAND, 0)
        self.SetSizer(vbox)

    def on_right_click(self, event):
        # 弹出菜单
        self.PopupMenu(self.menu)
        # self.menu.Destroy()

    def execute_sql_ui(self, execute_type):
        # 获取选中的文本
        selected_text = self.text_ctrl.GetSelectedText()
        by_type = "TIME"
        if selected_text:
            wx.MessageBox(f"选中的SQL语句:\n{selected_text}", "执行SQL", wx.OK | wx.ICON_INFORMATION)
            wx.CallAfter(self.toggle_menu, False) 
            wx.GetApp().change_status_bar("查询中...")
            # 创建一个后台线程执行 SQL
            thread = threading.Thread(target=self.execute_sql, args=(execute_type, selected_text, by_type))
            thread.start()
        else:
            wx.MessageBox("没有选中的文本！", "错误", wx.OK | wx.ICON_ERROR)

    def format_sql(self) -> str:
        self.text_ctrl.safe_format_sql()

    def execute_sql(self, execute_type, alter_sql, by_type, condition=False):
        database_config = wx.GetApp().connect_instance
        try:
            if database_config:
                if execute_type == "online_schema_change":
                    table = extract_table_name_ddl(alter_sql)
                    if extract_table_name_ddl(alter_sql):
                        online_schema_change(database_config["host"], database_config["user"], database_config["password"], database_config["database"], table, by_type, alter_sql, condition)
                    else:
                        wx.MessageBox("未指定表名称", "错误", wx.OK | wx.ICON_ERROR)
                else:
                    with pymysql.connect(**database_config) as conn:
                        with conn.cursor() as cursor:
                            statements = sqlglot.parse(alter_sql, read="mysql")
                            for expr in statements:
                                stmt = expr.sql(dialect="mysql")
                                cursor.execute(stmt)
                            conn.commit()
                            data = cursor.fetchall()
                            # 更新 UI（必须用 wx.CallAfter）
                            wx.CallAfter(self.show_result, data)
            else:
                wx.MessageBox("未指定实例", "错误", wx.OK | wx.ICON_ERROR)

        except Exception as e:
            wx.CallAfter(self.show_error, str(e))
            print(e)     
        finally:
            wx.CallAfter(self.toggle_menu, True) 


    def show_result(self, data):
        """在 UI 线程中显示查询结果"""
        dlg = DatabaseGridDialog(self, "查询结果", data)
        wx.GetApp().change_status_bar("")
        dlg.ShowModal()
        dlg.Destroy()


    def show_error(self, error_msg):
        """在 UI 线程中显示错误信息"""
        wx.GetApp().change_status_bar("")
        wx.MessageBox(f"数据库查询失败:\n{error_msg}", "错误", wx.OK | wx.ICON_ERROR)


    def toggle_menu(self, enable):
        """启用/禁用右键菜单"""
        self.execute_direct_item.Enable(enable)
        self.execute_osc_item.Enable(enable)

