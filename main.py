import wx
import pymysql
from ui.main_frame import MainFrame


class MyApp(wx.App):
    def OnInit(self):
        self.base_title = "PddSQL 1.0 - "
        self.connect_instance = None
        self.frame = MainFrame(None, title="PddSQL")
        self.frame.Show()
        return True
    
    def change_instance(self, selected_instance):
        if selected_instance:
            database_config = {
                "host" : selected_instance.get("instance_addr"),     # Database host (e.g., "localhost" or "127.0.0.1")
                "user" : selected_instance.get("instance_user"),     # Username for database authentication
                "password" : selected_instance.get("instance_pswd"), # Password for database authentication
                "charset" : "utf8mb4",                               # Character encoding for the connection
                "cursorclass" : pymysql.cursors.DictCursor,          # Cursor type for result formatting
                "database" : None,  
                "port" : 3306                                
            }
            self.connect_instance = database_config
        else:
            self.connect_instance = None
        return self.connect_instance
    
    def change_status_bar(self, message):
        self.frame.status_bar.SetStatusText(message)

if __name__ == "__main__":
    app = MyApp()
    app.MainLoop()
