import wx
import wx.grid
import pymysql
import threading
import time
from ui.dialogs import MyPopup, UserComboDialog
from scripts.db import normalize_sql


class RightPanelBottom(wx.Panel):
    def __init__(self, parent):
        super(RightPanelBottom, self).__init__(parent)
        self.selected_sessions = {}
        self.session_filter = None

        # 下半部分的面板布局
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 创建会话面板
        session_panel = wx.Panel(self, style=wx.BORDER_THEME) 
        session_sizer = wx.BoxSizer(wx.VERTICAL)
        session_panel.SetSizer(session_sizer)

        # 创建控制按钮面板
        button_panel = wx.Panel(session_panel) 
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn1 = wx.Button(button_panel, label="KILL")
        self.btn1.Bind(wx.EVT_BUTTON, self.on_execute_kill_sql)
        self.btn2 = wx.Button(button_panel, label="持续查杀")
        self.killing = True                                           # 持续查杀标志
        self.btn2.Bind(wx.EVT_BUTTON, self.on_execute_kill_sessions)
        self.btn3 = wx.CheckBox(button_panel, label="仅看活跃")
        self.btn3.Bind(wx.EVT_CHECKBOX, self.on_session_filter)
        button_sizer.Add(self.btn1, 0, wx.ALIGN_LEFT ,5)
        button_sizer.Add(self.btn2, 0, wx.ALIGN_LEFT ,5)
        button_sizer.AddStretchSpacer(1)                              # 中间空开
        button_sizer.Add(self.btn3, 0, wx.ALIGN_LEFT ,5)
        button_panel.SetSizer(button_sizer)
        # button_panel.SetMaxSize((-1, 40))

        # 创建200行9列的表格
        self.grid_session = wx.grid.Grid(session_panel) 
        self.grid_session.CreateGrid(55, 9)  
        self.grid_session.EnableDragRowSize(False)

        # 设置表头
        row_labels_with_sizes = [ 
            {"label": "#", "colsize": 60},
            {"label": "ID", "colsize": 80},
            {"label": "USER", "colsize": 120},
            {"label": "HOST", "colsize": 130},
            {"label": "DB", "colsize": 120},
            {"label": "COMMAND", "colsize": 140},
            {"label": "TIME", "colsize": 70},
            {"label": "STATE", "colsize": 140},
            {"label": "INFO", "colsize": 500}
        ]
        for idx, ery_label in enumerate(row_labels_with_sizes):
            self.grid_session.SetColSize(idx, ery_label.get("colsize"))
            self.grid_session.SetColLabelValue(idx, ery_label.get("label"))
            self.grid_session.SetColLabelAlignment(wx.ALIGN_LEFT, wx.ALIGN_CENTER)

        # 表格设置
        self.grid_session.SetColFormatBool(0)               # 复选框
        # self.set_grid_read_only(self.grid_session, True)
        self.grid_session.SetDefaultCellOverflow(False)     # 文本溢出
        # self.grid_session.EnableDragColSize(False)        # 禁用列大小调整
        self.grid_session.EnableDragRowSize(False)          # 禁用行大小调整
        self.grid_session.SetDoubleBuffered(True)
        self.grid_session.SetCellHighlightPenWidth(0)       # 聚焦框的宽度设置为 0

        session_sizer.Add(button_panel, 0, wx.EXPAND | wx.ALL, 5)
        session_sizer.Add(self.grid_session, 1, wx.EXPAND | wx.ALL, 5)

        # 将会话面板添加到主布局
        sizer.Add(session_panel, 1, wx.EXPAND | wx.ALL, 0)
        # 设置主面板的布局管理器
        self.SetSizer(sizer)
        
        # 事件绑定
        self.grid_session.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, self.on_cell_click)
        self.grid_session.Bind(wx.grid.EVT_GRID_RANGE_SELECT, self.on_range_select)
        self.grid_session.Bind(wx.grid.EVT_GRID_CELL_LEFT_DCLICK, self.on_cell_double_click)
        # 记录悬浮行
        self.current_hovered_row = -1
        self.current_hovered_col = -1
        gridWin = self.grid_session.GetGridWindow()
        gridWin.Bind(wx.EVT_MOTION, self.on_mouse_hover)
        gridWin.Bind(wx.EVT_LEAVE_WINDOW, self.on_mouse_leave)
        # 设置表格刷新
        self.running = True
        self.update_thread = threading.Thread(target=self.update_data_thread, daemon=True)
        self.update_thread.start()


    def update_data_thread(self):
        while self.running:
            try:
                # 连接数据库
                database_config = wx.GetApp().connect_instance
                if database_config:
                    # 执行查询
                    with pymysql.connect(**database_config) as conn:
                        with conn.cursor() as cursor:
                            cursor.execute("/*!50708 SET SESSION MAX_EXECUTION_TIME = 3000 */;")
                            while True:
                                use_db =  wx.GetApp().connect_instance["database"]
                                if use_db:
                                    if not self.session_filter:
                                        sql = f"/*PddSQL EXECUTE SQL*/ SELECT * FROM information_schema.processlist where DB='{use_db}' order by COMMAND, TIME DESC LIMIT 500; "
                                    else:
                                        sql = f"/*PddSQL EXECUTE SQL*/ SELECT * FROM information_schema.processlist where DB='{use_db}' AND Command != 'Sleep' order by COMMAND, TIME DESC LIMIT 500; "
                                else:
                                    if not self.session_filter:
                                        sql = "/*PddSQL EXECUTE SQL*/ SELECT * FROM information_schema.processlist order by TIME DESC LIMIT 500; "
                                    else:
                                        sql = "/*PddSQL EXECUTE SQL*/ SELECT * FROM information_schema.processlist where Command != 'Sleep' order by TIME DESC LIMIT 500; "
                                cursor.execute(sql)
                                data = cursor.fetchall()
                                # 更新表格
                                wx.CallAfter(self.populate_table, data)
                                # 更新表格数据
                                time.sleep(3)
                                print(self.selected_sessions)
                                if database_config != wx.GetApp().connect_instance:
                                    self.selected_sessions = {}
                                    print(self.selected_sessions)
                                    break
                                if not self.running:
                                    break

                else:
                    remain_rows = self.grid_session.GetNumberRows()
                    if remain_rows > 0:
                        self.grid_session.DeleteRows(0, remain_rows)
                    self.selected_sessions = {}
                    time.sleep(3)

            except Exception as e:
                wx.CallAfter(self.populate_table, None)
            
    def populate_table(self, results):
        """更新表格内容"""
        if results is not None:
            valid_ids = {str(row["ID"]) for row in results}

            # 剔除不存在于 results 中的 ID
            self.selected_sessions = {
                session_id: value
                for session_id, value in self.selected_sessions.items()
                    if session_id in valid_ids
            }

            # 处理选中状态
            selected_ids = list(self.selected_sessions.keys())
            selected_rows = [row for row in results if str(row["ID"]) in selected_ids]
            unselected_rows = [row for row in results if str(row["ID"]) not in selected_ids]
            # 将选中的会话排在前面
            sorted_data = selected_rows + unselected_rows

            self.grid_session.ClearGrid()
            
            # 调整行数
            current_rows = self.grid_session.GetNumberRows()
            if len(sorted_data) > current_rows:
                self.grid_session.AppendRows(len(sorted_data) - current_rows)
            elif len(sorted_data) < current_rows:
                self.grid_session.DeleteRows(len(sorted_data), current_rows - len(sorted_data))
            
            # 填充数据
            for row, process in enumerate(sorted_data):
                # 填写每一列数据
                self.grid_session.SetCellValue(row, 1, str(process["ID"]))
                self.grid_session.SetCellValue(row, 2, process["USER"])
                self.grid_session.SetCellValue(row, 3, process["HOST"])
                self.grid_session.SetCellValue(row, 4, str(process.get("DB"))) 
                self.grid_session.SetCellValue(row, 5, str(process["COMMAND"]))
                self.grid_session.SetCellValue(row, 6, str(process["TIME"]))
                self.grid_session.SetCellValue(row, 7, str(process["STATE"]))
                if process.get("INFO"):
                    self.grid_session.SetCellValue(row, 8, str(process.get("INFO").lstrip()[:2000]))
                else:
                    self.grid_session.SetCellValue(row, 8, " ")

                # 如果当前 ID 已经被选中，保持复选框选中状态
                if str(process["ID"]) in self.selected_sessions:
                    self.grid_session.SetCellValue(row, 0, "1")
                    self.set_row_background(row, "light blue")
                elif int(process["TIME"]) >= 10 and str(process["STATE"]) != "Sleep":
                    self.grid_session.SetCellValue(row, 0, "0")
                    self.set_row_background(row, "yellow")                 
                else:
                    self.grid_session.SetCellValue(row, 0, "0")
                    self.set_row_background(row, wx.NullColour)

            self.grid_session.ForceRefresh()  # 强制刷新以应用颜色
        else:
            if self.grid_session.GetNumberRows() > 0:
                self.grid_session.DeleteRows(0, self.grid_session.GetNumberRows())
            

    def set_row_background(self, row, colour):
        """设置指定行的背景色"""
        for col in range(self.grid_session.GetNumberCols()):
            self.grid_session.SetCellBackgroundColour(row, col, colour)

    def on_cell_click(self, event):
        """处理复选框点击事件"""
        row = event.GetRow()
        col = event.GetCol()
    
        # 仅处理第一列（复选框）
        if col == 0:
            self.grid_session.SetGridCursor(row, col)
            session_id = self.grid_session.GetCellValue(row, 1)  # 获取 ID 列值
            current_value = self.grid_session.GetCellValue(row, 0)
            new_value = "0" if current_value == "1" else "1"
            self.grid_session.SetCellValue(row, 0, new_value)
            
            # 更新选中字典
            if new_value == "1":
                self.selected_sessions[session_id] = True
                self.set_row_background(row, "light blue")
            else:
                self.selected_sessions.pop(session_id, None)
                self.set_row_background(row, wx.NullColour)

            print(f"Updated CLICK: {self.selected_sessions}")
        else:
            event.Skip()
            

    def on_mouse_hover(self, event):
        """处理鼠标悬停高亮显示"""
        pos = event.GetPosition()
        coords = self.grid_session.XYToCell(pos)
        row, col = coords
        if row != self.current_hovered_row:
            visible_row, visible_col = coords.GetRow(), coords.GetCol()
            # 获取滚动条位置（行的偏移量）
            row_offset = self.grid_session.GetScrollPos(wx.VERTICAL)
            col_offset = self.grid_session.GetScrollPos(wx.HORIZONTAL)
            # 计算实际的全局行和列
            global_row = visible_row + row_offset
            global_col = visible_col + col_offset

            x, y = self.grid_session.CalcUnscrolledPosition(pos.x, pos.y)
            
            # 通过像素位置找到对应的行列
            global_row = self.grid_session.YToRow(y)  # 获取全局行号
            col = self.grid_session.XToCol(x)  # 获取全局列号
            if self.current_hovered_row >= 0:
                # 恢复之前行的默认背景颜色
                self.reset_row_color(self.current_hovered_row)
            
            if global_row >= 0:  # 确保行有效
                self.set_row_color(global_row, "light blue")  # 设置悬浮行颜色

            self.current_hovered_row = global_row  # 更新当前悬浮的行
            self.current_hovered_col = global_col  # 更新当前悬浮的列

        event.Skip()

    def on_mouse_leave(self, event):
        """鼠标离开 Grid 时恢复颜色"""
        self.reset_row_color(self.current_hovered_row)
        event.Skip()

    def set_row_color(self, row, color):
        """设置整行背景色"""
        attr = wx.grid.GridCellAttr()
        attr.SetBackgroundColour(color)
        self.grid_session.SetRowAttr(row, attr)
        self.grid_session.ForceRefresh()

    def reset_row_color(self, row):
        """重置整行背景色为默认颜色"""
        attr = wx.grid.GridCellAttr()
        attr.SetBackgroundColour(wx.NullColour)
        self.grid_session.SetRowAttr(row, attr)
        #self.grid_session.ForceRefresh()

    def on_range_select(self, event):
        """处理范围选择事件"""
        if event.Selecting():  # 确保是选择范围事件
            # 获取范围坐标
            top_left = event.GetTopLeftCoords()
            bottom_right = event.GetBottomRightCoords()

            top_row, left_col = top_left
            print(top_left, bottom_right)
            bottom_row, right_col = bottom_right

            # 遍历选中范围
            for row in range(top_row, bottom_row + 1):
                #if left_col <= 0 <= right_col:  # 如果包含第0列
                    session_id = self.grid_session.GetCellValue(row, 1)  # 获取 ID 列值
                    current_value = self.grid_session.GetCellValue(row, 0)
                    new_value = "0" if current_value == "1" else "1"
                    self.grid_session.SetCellValue(row, 0, new_value)

                    # 更新选中字典
                    if new_value == "1":
                        self.selected_sessions[session_id] = True
                    else:
                        self.selected_sessions.pop(session_id, None)

            print(f"Updated selected_sessions after range select: {self.selected_sessions}")

    def on_cell_double_click(self, event):
        """双击表格单元格时弹出贴纸消息"""
        row = event.GetRow()
        col = event.GetCol()
        if col != 0:
            # 获取单元格内容
            cell_value = self.grid_session.GetCellValue(row, col)
            # 将内容复制到系统剪贴板
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(cell_value))
                wx.TheClipboard.Close()
            else:
                wx.MessageBox("无法打开剪贴板", "错误", wx.OK | wx.ICON_ERROR)

            # 创建并显示popup
            self.popup = MyPopup(self, f"已复制: {cell_value}")
            screen_pos = self.grid_session.ClientToScreen(event.GetPosition())
            self.popup.Position((screen_pos[0], screen_pos[1]), (0,0))
            self.popup.Show(True)

    def set_grid_read_only(self, gridobj, is_read_only):
        """设置整个Grid的所有单元格为只读"""
        for row in range(gridobj.GetNumberRows()):
            for col in range(gridobj.GetNumberCols()):
                gridobj.SetReadOnly(row, col, is_read_only)
    
    def on_execute_kill_sql(self, event):
        if not self.selected_sessions:
            wx.MessageBox("未勾选会话", "操作结果", wx.OK | wx.ICON_INFORMATION)
            return
        
        dlg = UserComboDialog(self, "选择用户")
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()   
            return 
        selected_user = dlg.get_selection()
        print(selected_user)
        database_config = wx.GetApp().connect_instance
        database_config["user"] = selected_user
        database_config["password"] = dlg.get_selection_userpwd()
        
        results = []
        try:
            conn = pymysql.connect(**database_config)
        except pymysql.err.OperationalError as e:
            wx.MessageBox(f"连接数据库失败：{e}", "连接错误", wx.OK | wx.ICON_ERROR)
            return
        except pymysql.MySQLError as e:
            wx.MessageBox(f"MySQL 错误：{e}", "错误", wx.OK | wx.ICON_ERROR)
            return

        try:
            with conn.cursor() as cursor:
                sql = "KILL %s;"
                for sid in self.selected_sessions:
                    try:
                        cursor.execute(sql, sid)
                        results.append(f"KILL {sid}; 成功 (影响行数: {cursor.rowcount})")
                    except Exception as e:
                        results.append(f"KILL {sid}; 失败: {e}")
        finally:
            conn.close()

        wx.MessageBox("\n".join(results), "操作结果", wx.OK | wx.ICON_INFORMATION)

    def on_execute_kill_sessions(self, event):
        if self.btn2.GetLabel() == "持续查杀":
            if not self.selected_sessions:
                wx.MessageBox("未勾选会话", "操作结果", wx.OK | wx.ICON_INFORMATION)
                return
            
            dlg = UserComboDialog(self, "选择用户")
            if dlg.ShowModal() != wx.ID_OK:
                dlg.Destroy()   
                return 
            selected_user = dlg.get_selection()
            if not selected_user:
                wx.MessageBox("请选择一个用户", "操作结果", wx.OK | wx.ICON_INFORMATION)
                return
            
            if len(self.selected_sessions) != 1:
                wx.MessageBox("仅能查杀一类SQL", "操作结果", wx.OK | wx.ICON_INFORMATION)
                return
            self.btn2.SetLabel("停止查杀")
            print("开始查杀会话...")
            thread = threading.Thread(
                target=lambda: self.on_execute_kill_sql_along(
                    selected_user=selected_user,
                    selected_password=dlg.get_selection_userpwd()
                ),
                daemon=True
            )
            thread.start()
        else:
            self.killing = False

    def on_execute_kill_sql_along(self, selected_user, selected_password):
        """持续查杀会话"""
        try:
            self.killing = True
            target_sql_id = next(iter(self.selected_sessions))
            # 连接数据库
            database_config = wx.GetApp().connect_instance
            database_config["user"] = selected_user
            database_config["password"] = selected_password
            with pymysql.connect(**database_config) as conn:
                with conn.cursor(pymysql.cursors.SSCursor) as cursor:
                    cursor.execute("SELECT * FROM information_schema.processlist WHERE ID = {0}".format(target_sql_id))
                    for row in cursor:
                        print(row)
                        id = row[0]
                        user = row[1]
                        info = row[7]
                    print(f"id={id} user={user} sql={info}")

                    if info is None:
                        wx.MessageBox("无内容", "操作结果", wx.OK | wx.ICON_INFORMATION)
                        return
                    else:
                        target_normalize_sql = normalize_sql(info)
                        wx.MessageBox(f"SQL类别: \n{target_normalize_sql}", "操作结果", wx.OK | wx.ICON_INFORMATION)
                    while self.killing:
                        kill_sql = "KILL %s;"
                        cursor.execute('SELECT * FROM information_schema.processlist WHERE INFO IS NOT NULL AND COMMAND NOT IN ("Sleep");')
                        sqls = cursor.fetchall()
                        for row in sqls:
                            every_sql = normalize_sql(row[7])
                            if every_sql == target_normalize_sql:
                                cursor.execute(kill_sql, row[0])
                                print(every_sql)
                        time.sleep(1)

        except Exception as kill_error:
            print(kill_error)

        finally:
            self.killing = False
            self.btn2.SetLabel("持续查杀")

    def on_session_filter(self, event):
        if self.btn3.IsChecked():
            print("✅ 仅看活跃启用")
            self.session_filter = 'AND Command != "Sleep"'
        else:
            self.session_filter = None
            print("🔁 显示全部")