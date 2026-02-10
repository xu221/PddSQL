import wx
import pymysql
from scripts.utils import resource_path
from ui.dialogs import TableSizePanel

class LeftPanel(wx.Panel):
    def __init__(self, parent):
        super(LeftPanel, self).__init__(parent)

        # 搜索框
        self.db_search_box = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.db_search_box.SetHint("库过滤器")
        self.tb_search_box = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.tb_search_box.SetHint("表过滤器")

        # 右键菜单
        self.context_menu = wx.Menu()
        self.delete_item = self.context_menu.Append(wx.ID_ANY, "断开链接")
        self.Bind(wx.EVT_MENU, self.delete_instance_node, self.delete_item)
        self.tables_analyze_item = self.context_menu.Append(wx.ID_ANY, "统计表大小")
        self.Bind(wx.EVT_MENU, self.open_tablesize_chart, self.tables_analyze_item)       

        # 树控件
        self.tree = wx.TreeCtrl(self, style=wx.TR_HAS_BUTTONS | 
                                            wx.TR_LINES_AT_ROOT |
                                            wx.TR_SINGLE | 
                                            wx.TR_HIDE_ROOT | 
                                            wx.TR_FULL_ROW_HIGHLIGHT
                                )
        self.root = self.tree.AddRoot("Root")
        self.alive_instances = {}
        self.original_tree_structure = {}
        
        # 创建图标列表（ImageList）
        self.image_list = wx.ImageList(16, 16)
        self.node_icon_tb_index = self.image_list.Add(wx.Image(resource_path("resources/icons/table.png")).Scale(16, 16).ConvertToBitmap())
        self.node_icon_db_index = self.image_list.Add(wx.Image(resource_path("resources/icons/database.png")).Scale(16, 16).ConvertToBitmap())
        self.node_icon_db_check_index = self.image_list.Add(wx.Image(resource_path("resources/icons/database_check.png")).Scale(16, 16).ConvertToBitmap())        
        self.node_icon_ins_index = self.image_list.Add(wx.Image(resource_path("resources/icons/ins_mysql.png")).Scale(16, 16).ConvertToBitmap())
        self.tree.SetImageList(self.image_list)

        # 布局
        grid_sizer = wx.GridBagSizer(1, 5)
        grid_sizer.Add(self.db_search_box, pos=(0, 0), flag=wx.EXPAND | wx.ALL, border=1)
        grid_sizer.Add(self.tb_search_box, pos=(0, 1), flag=wx.EXPAND | wx.ALL, border=1)
        grid_sizer.Add(self.tree, pos=(1, 0), span=(1, 2), flag=wx.EXPAND | wx.ALL, border=1)
        grid_sizer.AddGrowableCol(0, 3)
        grid_sizer.AddGrowableCol(1, 4)
        grid_sizer.AddGrowableRow(1)
        self.SetSizer(grid_sizer)

        # 事件绑定
        self.db_search_box.Bind(wx.EVT_TEXT, self.on_search_input)
        self.tb_search_box.Bind(wx.EVT_TEXT, self.on_search_input)
        
        self.tree.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.on_expand)
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_select)
        self.tree.Bind(wx.EVT_RIGHT_DOWN, self.on_right_click)
        self.tree.Bind(wx.EVT_LEFT_DOWN, self.on_left_click)
        self.tree.Bind(wx.EVT_MOTION, self.on_mouse_hover)
        self.tree.Bind(wx.EVT_LEAVE_WINDOW, self.on_mouse_leave) 

        # 悬停高亮
        self.tree.hovered_item = None

        # 状态变量
        self.check_item = None

        # 过滤延迟变量
        self.filter_calllater = None

    def on_search_input(self, event):
        """搜索输入时，延迟触发过滤"""
        # 如果已有未执行的任务，取消掉
        if self.filter_calllater is not None:
            self.filter_calllater.Stop()

        # 重新设定 300ms 后执行
        self.filter_calllater = wx.CallLater(300, self.on_db_tb_filter)

    def on_db_tb_filter(self):
        """根据搜索框内容过滤树节点"""
        db_search_text = self.db_search_box.GetValue().lower()
        tb_search_text = self.tb_search_box.GetValue().lower()
        print(db_search_text is None, tb_search_text)
        # 遍历根节点下的实例节点
        instance_node, cookie = self.tree.GetFirstChild(self.root)
        while instance_node.IsOk():
            self.populate_filtered_tree(instance_node, db_search_text, tb_search_text)
            instance_node, cookie = self.tree.GetNextChild(self.root, cookie)

    def populate_filtered_tree(self, parent_item, db_search_text, tb_search_text):
        """根据过滤条件重新填充数据库节点"""
        for node_text, children in self.original_tree_structure.get(self.tree.GetItemText(parent_item), {}).items():
            if db_search_text in node_text.lower():
                db_item = self.find_or_create_db_node(parent_item, node_text)
                self.populate_children(db_item, children, tb_search_text)
            else:
                db_item = self.find_db_node_by_label(parent_item, node_text)
                if db_item:
                    self.tree.Delete(db_item)

    def populate_children(self, parent_item, children, tb_search_text):
        """根据表过滤条件递归添加表节点"""
        self.tree.DeleteChildren(parent_item)
        for child_text, child_children in children.items():
            if tb_search_text in child_text.lower():
                # 如果搜索目标存在于树结构[内存变量]中，则重新加入
                child = self.tree.AppendItem(parent_item, child_text)
                self.tree.SetItemImage(child, self.node_icon_tb_index)

    def add_instance_tree(self, selected_instance):
        """添加实例到树中"""
        if selected_instance["instance_name"] in self.alive_instances:
            return
        self.alive_instances[selected_instance["instance_name"]] = selected_instance
        ins_node_text = f"{selected_instance['instance_name']}[{selected_instance['instance_addr']}]"
        ins_node = self.tree.AppendItem(self.root, ins_node_text)
        self.tree.SetItemImage(ins_node, self.node_icon_ins_index)
        self.tree.SetItemHasChildren(ins_node, True)
        self.tree.SelectItem(ins_node)

    def find_db_node_by_label(self, parent, label):
        """查找指定文本的子节点"""
        item, cookie = self.tree.GetFirstChild(parent)
        while item.IsOk():
            if self.tree.GetItemText(item) == label:
                return item
            item, cookie = self.tree.GetNextChild(parent, cookie)
        return None

    def find_or_create_db_node(self, parent, label):
        """查找或创建节点"""
        node = self.find_db_node_by_label(parent, label)
        if not node:
            node = self.tree.AppendItem(parent, label)
            self.tree.SetItemImage(node, self.node_icon_db_index)
            self.tree.SetItemHasChildren(node, True)
            
        return node

    def on_mouse_hover(self, event):
        """处理鼠标悬停高亮显示"""
        pt = event.GetPosition()
        item, _ = self.tree.HitTest(pt)

        if item and item.IsOk() and self.tree.hovered_item != item:
            self.highlight_item(item)
        elif not item:
            self.clear_highlight()

        event.Skip()

    def on_mouse_leave(self, event):
        """鼠标移出 TreeCtrl 时清除高亮"""
        self.clear_highlight()
        event.Skip()


    def highlight_item(self, item):
        """高亮指定节点"""
        self.clear_highlight()
        self.tree.SetItemBackgroundColour(item, "light blue")
        self.tree.hovered_item = item

    def clear_highlight(self):
        """清除节点高亮"""
        if self.tree.hovered_item and self.tree.hovered_item.IsOk():
            self.tree.SetItemBackgroundColour(self.tree.hovered_item, wx.NullColour)
            self.tree.hovered_item = None

    def on_left_click(self, event):
        """处理鼠标左键单击"""
        pt = event.GetPosition()
        item, _ = self.tree.HitTest(pt)
        if item:
            self.tree.SelectItem(item)
        event.Skip()

    def on_right_click(self, event):
        """处理鼠标右键点击"""
        pos = event.GetPosition()
        item, _ = self.tree.HitTest(pos)
        if item.IsOk():
            self.tree.SelectItem(item)
            self.PopupMenu(self.context_menu, pos)

    def delete_instance_node(self, event):
        """删除实例节点"""
        selected_item = self.tree.GetSelection()
        if selected_item.IsOk():
            parent_item = self.get_instance_root(selected_item)
            if parent_item:
                instance_name = self.tree.GetItemText(parent_item).split("[")[0]
                self.alive_instances.pop(instance_name, None)
                wx.GetApp().change_instance(None)
                self.tree.Delete(parent_item)
                
    def open_tablesize_chart(self, event):
        """点击按钮弹出图表窗口"""
        frame = wx.Frame(None, title=f"表空间趋势", size=(900, 600),
                         style=wx.DEFAULT_FRAME_STYLE | wx.RESIZE_BORDER)
        database_config = wx.GetApp().connect_instance
        chart_panel = TableSizePanel(frame, 
                                     database_config=database_config, 
                                     data_file=resource_path("configs\/tables_size_{0}.json".format(database_config["host"])))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(chart_panel, 1, wx.EXPAND | wx.ALL, 5)
        frame.SetSizer(sizer)
        frame.Show()

    def get_instance_root(self, item):
        """获取实例节点"""
        while item.IsOk():
            parent = self.tree.GetItemParent(item)
            if parent == self.root:
                return item
            item = parent
        return None

    def on_select(self, event):
        """处理节点选择"""
        item = event.GetItem()
        if item:
            level = self.get_item_level(item)
            print(level)
            if level == 2:    # 实例
                self.handle_instance_selected(item)
            elif level == 3:  # 数据库
                self.handle_database_selected(item)
            elif level == 4:  # 表
                self.handle_table_selected(item)

    def get_item_level(self, item):
        """获取节点层级"""
        level = 0
        while item.IsOk():
            item = self.tree.GetItemParent(item)
            level += 1
        return level

    def on_expand(self, event):
        """处理节点展开"""
        item = event.GetItem()
        level = self.get_item_level(item)
        if level == 2:
            self.populate_filtered_tree(item, self.db_search_box.GetValue().lower(), self.tb_search_box.GetValue().lower())

        if level == 3: 
            ins_node = self.tree.GetItemParent(item)
            selected_instance = self.alive_instances[self.tree.GetItemText(ins_node).split("[")[0]]
            wx.GetApp().change_instance(selected_instance)
            database_config = wx.GetApp().connect_instance
            dbname = self.tree.GetItemText(item)
            if database_config:
                database_config["database"] = dbname
                with pymysql.connect(**database_config) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(f"USE {dbname}")
                        cursor.execute("SHOW TABLES;")
                        tables = cursor.fetchall()
                        self.original_tree_structure[self.tree.GetItemText(self.tree.GetItemParent(item))][self.tree.GetItemText(item)] = {}
                        for tb in tables:                             
                            self.original_tree_structure[self.tree.GetItemText(self.tree.GetItemParent(item))][self.tree.GetItemText(item)][tb[f"Tables_in_{dbname}"]] = {}
            
            self.populate_children(item, self.original_tree_structure[self.tree.GetItemText(self.tree.GetItemParent(item))][self.tree.GetItemText(item)], self.tb_search_box.GetValue().lower())      
        
        event.Skip()  # 继续传播事件

    def handle_instance_selected(self, item):
        """处理实例节点被选中"""
        selected_instance = self.alive_instances[self.tree.GetItemText(item).split("[")[0]]
        wx.GetApp().change_instance(selected_instance)
        database_config = wx.GetApp().connect_instance
        print(database_config)
        if self.check_item and self.check_item != item:
            self.tree.SetItemImage(self.check_item, self.node_icon_db_index)
        if database_config:
            with pymysql.connect(**database_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SHOW DATABASES;")
                    databases = cursor.fetchall()
                    self.original_tree_structure[self.tree.GetItemText(item)] = {}
                    for db in databases:
                        self.original_tree_structure[self.tree.GetItemText(item)][db["Database"]] = {}
                    wx.GetApp().frame.SetTitle(f"PddSQL 1.0 - {selected_instance['instance_addr']}")

    def handle_database_selected(self, item):
        """处理数据库节点被选中"""
        ins_node = self.tree.GetItemParent(item)
        selected_instance = self.alive_instances[self.tree.GetItemText(ins_node).split("[")[0]]
        wx.GetApp().change_instance(selected_instance)
        dbname = self.tree.GetItemText(item)
        wx.GetApp().connect_instance["database"] = dbname
        if self.check_item and self.check_item != item:
            self.tree.SetItemImage(self.check_item, self.node_icon_db_index)
        self.tree.SetItemImage(item, self.node_icon_db_check_index)
        self.check_item = item
        wx.GetApp().frame.SetTitle(f"PddSQL 1.0 - {selected_instance['instance_addr']}\{dbname}")

    def handle_table_selected(self, item):
        """处理表节点被选中"""
        ins_node = self.tree.GetItemParent(self.tree.GetItemParent(item))
        selected_instance = self.alive_instances[self.tree.GetItemText(ins_node).split("[")[0]]
        selected_database = self.tree.GetItemText(self.tree.GetItemParent(item))
        selected_table = self.tree.GetItemText(item)
        wx.GetApp().change_instance(selected_instance)     
        wx.GetApp().connect_instance["database"] =  selected_database
        wx.GetApp().frame.SetTitle(f"PddSQL 1.0 - {selected_instance['instance_addr']}\{selected_database}\{selected_table}")
