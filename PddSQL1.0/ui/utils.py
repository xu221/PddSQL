import wx
import wx.stc as stc
from sqlglot import parse_one

class SQLTextEditor(stc.StyledTextCtrl):
    """ SQL 编辑器，支持 SQL 关键字补全(ab 循环匹配) 并高亮关键字 """

    def __init__(self, parent):
        super().__init__(parent, size=(-1, 300), style=wx.TE_MULTILINE)

        # 设置 Python 语法高亮
        self.SetLexer(wx.stc.STC_LEX_PYTHON)
        self.SetCodePage(wx.stc.STC_CP_UTF8)
        self.StyleSetForeground(wx.stc.STC_P_COMMENTLINE, wx.Colour(0, 128, 0))  # 绿色注释
        #self.StyleSetForeground(stc.STC_P_STRING, wx.Colour(255, 0, 0))  # 红色字符串
        self.StyleSetForeground(wx.stc.STC_P_STRING, wx.Colour(0, 128, 0)) 
        self.StyleSetForeground(wx.stc.STC_P_WORD, wx.Colour(0, 0, 255))  # 蓝色关键字
        self.SetUndoCollection(True) 
 
        self.sql_keywords = [
            "SELECT", "FROM", "WHERE", "INSERT", "UPDATE", "DELETE",
            "ORDER BY", "GROUP BY", "HAVING", "JOIN", "LEFT JOIN",
            "RIGHT JOIN", "INNER JOIN", "OUTER JOIN", "ON", "AND", "OR",
            "LIMIT", "OFFSET", "DISTINCT", "COUNT(*)", "LIKE", "IN" , "ALTER TABLE",
            "ADD", "ENGINE", "INNODB", "VARIABLES", "STATUS", "SHOW", "INDEX"
        ]

        # 关键字高亮
        self.SetKeyWords(0, " ".join(self.sql_keywords))

        # 显示行号
        self.SetMarginType(1, wx.stc.STC_MARGIN_NUMBER)
        self.SetMarginWidth(1, 40)

        # tab
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_press)
        
        # ctrl z
        self.Bind(wx.stc.EVT_STC_MODIFIED, self.on_text_modified)

        # 记录匹配状态
        self.matching_keywords = []
        self.match_index = 0
        self.match_start_pos = None
        self._suspend_undo_split = False

    def on_text_modified(self, event):
        """确保 Ctrl+Z 只撤销一步"""
        if self._suspend_undo_split:
            event.Skip()
            return
        mod_type = event.GetModificationType()
        if mod_type & (wx.stc.STC_MOD_INSERTTEXT | wx.stc.STC_MOD_DELETETEXT):
            self.EndUndoAction()    # 结束上一个撤销块
            self.BeginUndoAction()  # 开始新的撤销块
        event.Skip()

    def on_key_press(self, event):
        """ 监听键盘事件，按 Tab 进行 SQL 关键字补全（循环匹配） """
        key = event.GetKeyCode()
        if key == wx.WXK_TAB:
            self.auto_complete()
        else:
            # 如果用户按了其他键，则重置匹配状态
            self.reset_matching_state()
            event.Skip()

    def auto_complete(self):
        """从光标位置向前收集字符直到空格或换行"""
        cursor_pos = self.GetCurrentPos()
        text = self.GetTextRange(max(0, cursor_pos - 100), cursor_pos) # 获取编辑器的前100个字符
        prefix = []
        # 如果匹配状态为空，先记录匹配起始位置
        if self.match_start_pos is None:
            # 向前收集字符直到遇到空格或换行
            for char in reversed(text[:cursor_pos]):
                if char.isspace() or char == '\n':
                    break
                prefix.insert(0, char)
            prefix_string = ''.join(prefix)
            if not prefix_string:
                return

            self.match_start_pos = cursor_pos - len(prefix_string)
            self.matching_keywords = [kw.upper() for kw in self.sql_keywords if kw.upper().startswith(prefix_string.upper())] 
            if self.matching_keywords:
                self.matching_keywords.append(prefix_string)
                self.match_index = 0 

        if self.matching_keywords:
            # 取出当前匹配的 SQL 关键字
            matched_keyword = self.matching_keywords[self.match_index]
            
            # 替换关键字
            self.SetSelection(self.match_start_pos, self.match_start_pos + len(self.matching_keywords[self.match_index - 1 ]))
            self.ReplaceSelection(matched_keyword)
            self.SetInsertionPoint(self.match_start_pos + len(matched_keyword))
            self.SetSelection(self.match_start_pos + len(matched_keyword), self.match_start_pos + len(matched_keyword))

            # 递增索引，循环匹配
            self.match_index = (self.match_index + 1) % len(self.matching_keywords)

    def reset_matching_state(self):
        """ 重置匹配状态（在光标移动或输入新字符时触发） """
        self.matching_keywords = []
        self.match_index = 0
        self.match_start_pos = None

    def safe_format_sql(self) -> str:
        """ 结构化选中的区域 """
        self._suspend_undo_split = True
        try:
            self.BeginUndoAction()

            selected_text = self.GetSelectedText()
            sel_start, sel_end = self.GetSelection()
            formatted_sql = parse_one(selected_text, read="mysql").sql(
                pretty=True,
                indent=2
            )
            self.SetTargetStart(sel_start)
            self.SetTargetEnd(sel_end)
            self.ReplaceTarget(formatted_sql + ';\n')
            
            self.EndUndoAction()
            self.SetSelection(sel_start, sel_start+len(formatted_sql + ';\n'))
            self.BeginUndoAction()
            self.EndUndoAction()
        except Exception:
            # fallback：不破坏用户输入
            return selected_text
        finally:
            self._suspend_undo_split = False