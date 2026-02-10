import wx
import json, os
from scripts.utils import resource_path
import datetime
import matplotlib.dates as mdates
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.figure import Figure
import pymysql

class InstanceManager(wx.Dialog):
    def __init__(self, *args, **kw):
        super(InstanceManager, self).__init__(*args, **kw)

        # 设置窗口标题和大小
        self.SetPosition((500, 300))
        self.SetTitle("实例管理器")
        self.SetSize((900, 700))

        self.selected_instance = {}
        # 用于存储选定的实例名称
        # self.selected_instance =
        # {
        #     "instance_name" : instance_name,
        #     "instance_addr" : instance_addr,
        #     "instance_port" : instance_port,
        #     "instance_user" : instance_user,
        #     "instance_pswd" : instance_pswd,
        #     "instance_desc" : instance_desc
        # }

        # 创建一个 SplitterWindow
        splitter = wx.SplitterWindow(self)

        # 创建左侧面板和搜索框
        left_panel = wx.Panel(splitter)
        vbox_left = wx.BoxSizer(wx.VERTICAL)
        
        # 添加搜索框
        self.search_box = wx.TextCtrl(left_panel, style=wx.TE_PROCESS_ENTER)
        self.search_box.SetHint("Filter") 
        vbox_left.Add(self.search_box, 0, wx.EXPAND | wx.ALL, 5)

        # 添加实例列表
        self.instance_list = wx.ListBox(left_panel)
        vbox_left.Add(self.instance_list, 1, wx.EXPAND | wx.ALL, 5)
        left_panel.SetSizer(vbox_left)
        
        # 尝试读取现有的 JSON 文件
        self.instances = self.load_instances_from_file()

        # 创建右侧面板，用于填写实例信息
        right_panel = wx.Panel(splitter)
        grid_right = wx.GridBagSizer(6, 6)

        # 添加实例名
        name_label = wx.StaticText(right_panel, label="实例名:")
        self.instance_name = wx.TextCtrl(right_panel)
        grid_right.Add(name_label, pos=(0, 0), flag= wx.RIGHT | wx.TOP | wx.ALIGN_LEFT, border=5)
        grid_right.Add(self.instance_name, pos=(0, 1), flag=wx.EXPAND | wx.TOP | wx.RIGHT, border=5)

        # 添加地址
        ip_label = wx.StaticText(right_panel, label="链接地址:")
        self.instance_addr = wx.TextCtrl(right_panel)
        grid_right.Add(ip_label, pos=(1, 0), flag= wx.RIGHT | wx.TOP | wx.ALIGN_LEFT, border=5)
        grid_right.Add(self.instance_addr, pos=(1, 1), flag=wx.EXPAND | wx.TOP | wx.RIGHT, border=5)

        # 添加端口
        port_label = wx.StaticText(right_panel, label="端口:")
        self.instance_port = wx.TextCtrl(right_panel)
        grid_right.Add(port_label, pos=(2, 0), flag= wx.RIGHT | wx.TOP | wx.ALIGN_LEFT, border=5)
        grid_right.Add(self.instance_port, pos=(2, 1), flag=wx.EXPAND | wx.TOP | wx.RIGHT, border=5)

        # 添加用户名（此处为下拉选择 + 添加按钮 + 删除按钮） —— 对应“实例内部的多个用户”
        user_label = wx.StaticText(right_panel, label="用户名:")
        user_hbox = wx.BoxSizer(wx.HORIZONTAL)
        # 使用可下拉的 ComboBox 显示该实例下的用户
        self.instance_user = wx.ComboBox(right_panel, style=wx.CB_READONLY)
        self.add_user_btn = wx.Button(right_panel, label="+", size=(28, -1))
        self.remove_user_btn = wx.Button(right_panel, label="-", size=(28, -1))
        user_hbox.Add(self.instance_user, 1, wx.EXPAND)
        user_hbox.Add(self.add_user_btn, 0, wx.LEFT, 4)
        user_hbox.Add(self.remove_user_btn, 0, wx.LEFT, 4)
        grid_right.Add(user_label, pos=(3, 0), flag= wx.RIGHT | wx.TOP | wx.ALIGN_LEFT, border=5)
        grid_right.Add(user_hbox, pos=(3, 1), flag=wx.EXPAND | wx.TOP | wx.RIGHT, border=5)

        # 添加密码
        password_label = wx.StaticText(right_panel, label="密码:")
        self.instance_pswd = wx.TextCtrl(right_panel)
        grid_right.Add(password_label, pos=(4, 0), flag= wx.RIGHT | wx.TOP | wx.ALIGN_LEFT, border=5)
        grid_right.Add(self.instance_pswd , pos=(4, 1), flag=wx.EXPAND | wx.TOP | wx.RIGHT, border=5)  

        # 添加描述
        desc_label = wx.StaticText(right_panel, label="描述:")
        self.instance_desc = wx.TextCtrl(right_panel, style=wx.TE_MULTILINE)
        grid_right.Add(desc_label, pos=(5, 0), flag=wx.RIGHT | wx.TOP | wx.ALIGN_LEFT, border=5)
        grid_right.Add(self.instance_desc, pos=(5, 1), flag=wx.EXPAND | wx.TOP | wx.RIGHT, border=5)

        # 创建水平布局器用于按钮
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.AddStretchSpacer(1)
        # 添加保存按钮
        self.save_button = wx.Button(right_panel, label="保存实例")
        button_sizer.Add(self.save_button, 0, wx.ALIGN_RIGHT, 5)
        # 添加打开按钮
        self.open_button = wx.Button(right_panel, label="打开")
        button_sizer.Add(self.open_button, 0, wx.ALIGN_RIGHT, 5)
        # 添加删除按钮
        self.delete_button = wx.Button(right_panel, label="删除实例")
        button_sizer.Add(self.delete_button, 0, wx.ALIGN_RIGHT, 5)
        # 将按钮布局添加到 GridBagSizer
        grid_right.Add(button_sizer, pos=(6, 0), span=(1, 2), flag=wx.ALIGN_RIGHT | wx.ALL, border=5)

        # 设置描述布局
        grid_right.AddGrowableCol(1, 1)
        grid_right.AddGrowableRow(5, 1)
        right_panel.SetSizer(grid_right)

        # 设置 SplitterWindow 的左右布局
        splitter.SplitVertically(left_panel, right_panel)
        splitter.SetSashGravity(0.3)  # 设置分隔条偏向左侧

        # 绑定按钮事件
        self.save_button.Bind(wx.EVT_BUTTON, self.on_save_instance)
        self.open_button.Bind(wx.EVT_BUTTON, self.on_open_instance)
        self.delete_button.Bind(wx.EVT_BUTTON, self.on_delete_instance)
        self.add_user_btn.Bind(wx.EVT_BUTTON, self.on_add_user)
        self.remove_user_btn.Bind(wx.EVT_BUTTON, self.on_remove_user)
        self.instance_user.Bind(wx.EVT_COMBOBOX, self.on_user_select)

        # 绑定列表选择事件
        self.instance_list.Bind(wx.EVT_LISTBOX, self.on_instance_selection)

        # 绑定搜索框事件
        self.search_box.Bind(wx.EVT_TEXT, self.on_filter_instances)

    def on_add_user(self, event):
        if not self.instance_name.GetValue():
            wx.MessageBox("请先输入实例名。", "提示", wx.OK | wx.ICON_INFORMATION)
            return
        dlg = wx.TextEntryDialog(self, "输入新用户名：", "添加用户")
        if dlg.ShowModal() == wx.ID_OK:
            username = dlg.GetValue().strip()
            if not username:
                return
            users = self.selected_instance.setdefault("users", {})
            if username in users:
                wx.MessageBox("该用户已存在。", "提示", wx.OK | wx.ICON_WARNING)
                return
            users[username] = {"password": ""}
            self.instance_user.Append(username)
            self.instance_user.SetStringSelection(username)
            self.instance_pswd.SetValue("")
        dlg.Destroy()

    def on_remove_user(self, event):
        if not self.selected_instance:
            return
        user = self.instance_user.GetStringSelection()
        if not user:
            return
        users = self.selected_instance.get("users", {})
        if user in users:
            del users[user]
        idx = self.instance_user.GetSelection()
        self.instance_user.Delete(idx)
        if self.instance_user.GetCount() > 0:
            self.instance_user.SetSelection(0)
            first = self.instance_user.GetStringSelection()
            self.instance_pswd.SetValue(users[first].get("password", ""))
        else:
            self.instance_pswd.SetValue("")

    def on_user_select(self, event):
        user = self.instance_user.GetStringSelection()
        if not user or not self.selected_instance:
            return
        self.selected_instance["instance_user"] = user
        pswd = self.selected_instance.get("users", {}).get(user, {}).get("password", "")
        self.selected_instance["instance_pswd"] = pswd   
        self.instance_pswd.SetValue(pswd)

    def on_save_instance(self, event):
        instance_name = self.instance_name.GetValue().strip()
        if not instance_name:
            wx.MessageBox("请输入实例名", "错误", wx.OK | wx.ICON_ERROR)
            return
        try:
            port_value = int(self.instance_port.GetValue())
        except ValueError:
            wx.MessageBox("请输入有效的数字端口号！", "错误", wx.OK | wx.ICON_ERROR)
            return

        # 读取当前实例已有的用户信息
        users = {}
        if self.selected_instance and "users" in self.selected_instance:
            users = self.selected_instance["users"]

        # 当前选中的用户
        current_user = self.instance_user.GetStringSelection()
        if current_user:
            users[current_user] = {
                "password": self.instance_pswd.GetValue()
            }

        # 构建实例结构
        data = {
            "instance_name": instance_name,
            "instance_addr": self.instance_addr.GetValue(),
            "instance_port": port_value,
            "instance_desc": self.instance_desc.GetValue(),
            "instance_user": self.instance_user.GetValue(),
            "instance_pswd": self.instance_pswd.GetValue(),
            "users" : users
        }

        self.instances[instance_name] = data
        if self.instance_list.FindString(instance_name) == wx.NOT_FOUND:
            self.instance_list.Append(instance_name)
        self.save_instances_to_file()

        wx.MessageBox(f"实例 '{instance_name}' 已保存", "保存成功", wx.OK | wx.ICON_INFORMATION)

    def on_open_instance(self, event):
        # 获取选定的实例
        selection = self.instance_list.GetSelection()
        if selection != wx.NOT_FOUND:
            self.selected_instance = self.instances[self.instance_list.GetString(selection)]
            self.EndModal(wx.ID_OK)
        else:
            wx.MessageBox("请选择一个实例", "错误", wx.OK | wx.ICON_ERROR)

    def on_delete_instance(self, event):
        # 获取选定的实例
        selection = self.instance_list.GetSelection()
        if selection != wx.NOT_FOUND:
            instance_name = self.instance_list.GetString(selection)
            if instance_name in self.instances:
                del self.instances[instance_name]
                self.instance_list.Delete(selection)
                self.selected_instance = {}
                wx.MessageBox(f"实例 '{instance_name}' 已删除", "删除实例", wx.OK | wx.ICON_INFORMATION)
                # 保存到文件
                self.save_instances_to_file()
            else:
                wx.MessageBox("选定的实例不存在", "错误", wx.OK | wx.ICON_ERROR)
        else:
            wx.MessageBox("请选择一个实例", "错误", wx.OK | wx.ICON_ERROR)

    def on_instance_selection(self, event):
        selection = self.instance_list.GetSelection()
        if selection == wx.NOT_FOUND:
            return

        name = self.instance_list.GetString(selection)
        self.selected_instance = self.instances.get(name, {})

        self.instance_name.SetValue(name)
        self.instance_addr.SetValue(self.selected_instance.get("instance_addr", ""))
        self.instance_desc.SetValue(self.selected_instance.get("instance_desc", ""))
        self.instance_port.SetValue(str(self.selected_instance.get("instance_port", "")))

        # === 加载用户列表 ===
        self.instance_user.Clear()
        users = self.selected_instance.get("users", {})
        for username in users.keys():
            self.instance_user.Append(username)
        if self.instance_user.GetCount() > 0:
            self.instance_user.SetSelection(0)
            first_user = self.instance_user.GetStringSelection()
            self.selected_instance["instance_user"] = first_user
            self.instance_pswd.SetValue(users[first_user].get("password", ""))
            self.selected_instance["instance_pswd"] = users[first_user].get("password", "")
        else:
            self.instance_pswd.SetValue("")
            self.selected_instance["instance_pswd"] = ""

    def on_filter_instances(self, event):
        filter_text = self.search_box.GetValue().lower()
        self.instance_list.Clear()
        for instance_name in self.instances:
            if filter_text in instance_name.lower():
                self.instance_list.Append(instance_name)

    def load_instances_from_file(self):
        try:
            with open(resource_path('configs\instances.json'), 'r', encoding='utf-8') as file:
                instances = json.load(file)
                print(instances)
                for every_instance_name in instances.keys():
                    self.instance_list.Append(every_instance_name)

                return instances
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_instances_to_file(self):
        with open(resource_path('configs\instances.json'), 'w', encoding='utf-8') as file:
            json.dump(self.instances, file, indent=4, ensure_ascii=False)


class MyPopup(wx.PopupWindow):
    def __init__(self, parent, message):
        super(MyPopup, self).__init__(parent)
        
        # 创建一个面板并设置为popup内容
        self.panel = wx.Panel(self)
        self.panel.SetBackgroundColour(wx.Colour(255, 255, 220))  # 便签颜色
  
        # 创建静态文本
        text = wx.StaticText(self.panel, label=message)

        # 添加一个BoxSizer布局
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(text, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 10)
        self.panel.SetSizer(sizer)

        # 自动调整布局尺寸
        sizer.Fit(self.panel)
        self.Fit()  # 自动调整Popup大小

        # 自动关闭定时器
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
        self.timer.Start(1000)  # 2秒后自动关闭

    def on_timer(self, event):
        """定时器事件,自动关闭Popup"""
        if self:
            self.timer.Stop()  # 停止定时器
            self.Destroy()     # 仅销毁Popup，不影响其他窗口

    
class DatabaseGridDialog(wx.Dialog):
    def __init__(self, parent, title, data):
        super().__init__(parent, title=title, size=(700, 400), style=wx.DEFAULT_FRAME_STYLE | wx.RESIZE_BORDER)

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # 创建表格
        self.grid = wx.grid.Grid(panel)
        
        if data:
            # 获取表头（所有 dict 的 keys）
            columns = list(data[0].keys())
            self.grid.CreateGrid(len(data), len(columns))

            # 设置表头
            for col, col_name in enumerate(columns):
                self.grid.SetColLabelValue(col, col_name)

            # 填充数据
            for row, row_data in enumerate(data):
                for col, col_name in enumerate(columns):
                    if len(str(row_data[col_name])) > 50:
                        self.grid.SetCellRenderer(row, col, wx.grid.GridCellAutoWrapStringRenderer())
                    self.grid.SetCellValue(row, col, str(row_data[col_name]))

            # 自适应列宽
            self.grid.AutoSizeColumns()
        else:
            self.grid.CreateGrid(1, 1)
            self.grid.SetCellValue(0, 0, "查询无结果")

        vbox.Add(self.grid, 1, wx.EXPAND | wx.ALL, 10)

        # 关闭按钮
        btn_sizer = wx.StdDialogButtonSizer()
        close_btn = wx.Button(panel, wx.ID_CANCEL, "关闭")
        btn_sizer.AddButton(close_btn)
        btn_sizer.Realize()

        vbox.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        panel.SetSizer(vbox)

class TableSizePanel(wx.Panel):
    def __init__(self, parent, database_config, data_file="tables_size.json"):
        super().__init__(parent)

        self.database_config = database_config

        # 获取数据并合并
        new_data = self.get_table_sizes(database_config["host"], 
                                        database_config["port"], 
                                        database_config["user"], 
                                        database_config["password"], 
                                        database_config["host"])
        old_data = self.load_from_json(data_file)
        self.data = self.merge_results(old_data, new_data)
        self.save_to_json(self.data, data_file)

        # Matplotlib 图表
        self.figure = Figure(figsize=(6, 4))
        self.axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self, -1, self.figure)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)

        # 绘制图表
        self.plot_all_tables()

        # 点击折线事件
        self.canvas.mpl_connect("button_press_event", self.on_line_click)

    def load_from_json(self, data_file):
        if not os.path.exists(data_file):
            return {}
        with open(data_file, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}

    def save_to_json(self, data, data_file):
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def merge_results(self, old_data, new_data):
        """合并新旧数据"""
        for ins, dbs in new_data.items():
            if ins not in old_data:
                old_data[ins] = {}
            for db, tbs in dbs.items():
                if db not in old_data[ins]:
                    old_data[ins][db] = {}
                for tb, dates in tbs.items():
                    if tb not in old_data[ins][db]:
                        old_data[ins][db][tb] = {}
                    old_data[ins][db][tb].update(dates)
        return old_data

    def get_table_sizes(self, host, port, user, password, instance_name):
        """获取 MySQL 表空间大小"""
        connection = pymysql.connect(
            host=host, port=port, user=user, password=password,
            charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor
        )
        sql = """
            SELECT TABLE_NAME, TABLE_SCHEMA,
            ROUND(DATA_LENGTH/1024/1024/1024) AS DATA_SIZE
            FROM information_schema.tables
            WHERE TABLE_SCHEMA NOT IN ('information_schema', 'mysql','sys')
            AND ROUND(DATA_LENGTH/1024/1024/1024, 2) >= 1
            ORDER BY DATA_LENGTH DESC;
        """
        today = datetime.date.today().strftime("%Y-%m-%d")
        result_dict = {instance_name: {}}
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()
                for row in rows:
                    db = row["TABLE_SCHEMA"]
                    tb = row["TABLE_NAME"]
                    size_gb = int(row["DATA_SIZE"])
                    result_dict[instance_name].setdefault(db, {})
                    result_dict[instance_name][db].setdefault(tb, {})
                    result_dict[instance_name][db][tb][today] = size_gb
        finally:
            connection.close()
        return result_dict

    def plot_all_tables(self):
        """绘制所有表的空间变化趋势"""
        self.axes.clear()
        if not self.data:
            self.axes.text(0.5, 0.5, "No Data", ha="center", va="center", fontsize=14)
            self.canvas.draw()
            return

        self.lines = []
        self.texts = []

        for ins, dbs in self.data.items():
            for db, tbs in dbs.items():
                for tb, time_dict in tbs.items():
                    dates, sizes = [], []
                    for date_str, size in sorted(time_dict.items()):
                        try:
                            dates.append(datetime.datetime.strptime(date_str, "%Y-%m-%d").date())
                            sizes.append(size)
                        except:
                            continue
                    if not dates:
                        continue
                    line, = self.axes.plot(
                        dates, sizes, marker="o", linestyle="-", linewidth=1.2, label=f"{db}.{tb}"
                    )
                    self.lines.append(line)
                    # 每个点的数值标签（默认隐藏）
                    text_objs = []
                    for x, y in zip(dates, sizes):
                        t = self.axes.text(x, y, f"{y}", fontsize=8, ha="center", va="bottom", visible=False)
                        text_objs.append(t)
                    self.texts.append(text_objs)

        # 添加右上角文本显示当前曲线
        self.info_text = self.axes.text(
            0.98, 0.95, "",
            transform=self.axes.transAxes,
            ha="right", va="top",
            fontsize=10, color="blue",
            bbox=dict(boxstyle="round,pad=0.3", fc="w", ec="gray", alpha=0.8)
        )

        self.axes.set_title(self.database_config["host"])
        self.axes.set_ylabel("Size (GB)")
        self.axes.grid(True)
        self.axes.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        self.axes.xaxis.set_major_locator(mdates.AutoDateLocator())
        self.figure.autofmt_xdate(rotation=30)
        self.figure.subplots_adjust(bottom=0.25)
        self.canvas.draw()

    def on_line_click(self, event):
        """点击曲线高亮显示表名与数据"""
        if event.inaxes != self.axes:
            return
        clicked_line = None
        for line in self.lines:
            contains, _ = line.contains(event)
            if contains:
                clicked_line = line
                break

        if clicked_line:
            for i, l in enumerate(self.lines):
                if l == clicked_line:
                    l.set_linewidth(3)
                    l.set_alpha(1.0)
                    for t in self.texts[i]:
                        t.set_visible(True)
                    label = l.get_label()
                    self.info_text.set_text(f"{label}")
                else:
                    l.set_linewidth(1.2)
                    l.set_alpha(0.15)
                    for t in self.texts[i]:
                        t.set_visible(False)
        else:
            # 点击空白区域，清除高亮
            for i, l in enumerate(self.lines):
                l.set_linewidth(1.2)
                l.set_alpha(1.0)
                for t in self.texts[i]:
                    t.set_visible(False)
            self.info_text.set_text("")

        self.canvas.draw_idle()


class UserComboDialog(wx.Dialog):
    def __init__(self, parent, title):
        super().__init__(parent, title=title, size=(300, 200))

        vbox = wx.BoxSizer(wx.VERTICAL)

        # 提示文字
        vbox.Add(wx.StaticText(self, label="请选择一个用户："), 0, wx.ALL | wx.EXPAND, 10)
        
        self.users = self.load_users_from_file()

        # 下拉选择框
        self.combo = wx.ComboBox(self, choices=list(self.users.keys()), style=wx.CB_READONLY)
        vbox.Add(self.combo, 0, wx.ALL | wx.EXPAND, 10)
        # 默认选中第一个（如果存在）
        if self.combo.GetCount() > 0:
            self.combo.SetSelection(0)

        # OK / Cancel 按钮
        hbox = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(self, wx.ID_OK)
        cancel_btn = wx.Button(self, wx.ID_CANCEL)
        hbox.AddButton(ok_btn)
        hbox.AddButton(cancel_btn)
        hbox.Realize()

        vbox.Add(hbox, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        self.SetSizer(vbox)

    def get_selection(self):
        """返回选中的用户"""
        return self.combo.GetStringSelection()
    
    def get_selection_userpwd(self):
        """返回选中的用户"""
        return self.users.get(self.combo.GetStringSelection(), 'unknow_user_pwd')
    
    def load_users_from_file(self):
        users = {}
        try:
            with open(resource_path('configs\instances.json'), 'r', encoding='utf-8') as file:
                instances = json.load(file)
                current_con_db = wx.GetApp().connect_instance.get("host")
                for ins_name, ins_item in instances.items():
                    if ins_item.get("instance_addr") == current_con_db:
                        for user_name, pswd_dict in ins_item.get("users").items():
                            users[user_name] = pswd_dict.get("password")
                return users
        except (FileNotFoundError, json.JSONDecodeError):
            return users