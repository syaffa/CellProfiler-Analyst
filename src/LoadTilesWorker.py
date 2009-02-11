from DBConnect import DBConnect
from ImageCollection import ImageCollection
from Properties import Properties
import threading
import wx

# Define a result event which is generated by the image loader thread.
EVT_IMAGE_RESULT_ID = wx.NewId()

def EVT_IMAGE_RESULT(win, func):
    ''' Any class that wishes to handle ImageResultEvents must first call this function
    with itself as the first parameter, and it's handler as the second parameter.'''
    win.Connect(-1, -1, EVT_IMAGE_RESULT_ID, func)
   
class ImageResultEvent(wx.PyEvent):
    ''' ========================================================================
    This event type is raised whenever an ImageTile is loaded with data = obKey
    and whenever the thread completes loading images with data = None
    ============================================================================ '''
    def __init__(self, data):
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_IMAGE_RESULT_ID)
        self.data = data
        


class LoadTilesWorker(threading.Thread):
    ''' ===========================================================================
    This thread uses ImageCollection.FetchTile to load tile data for a list of object keys.
    For each loaded tile, it posts a ImageResultEvent to the notify_window with
    data = (obKey, imgs).
    * notify_window must first call EVT_IMAGE_RESULT(notify_window, handler) to bind
    the ImageResultEvent to it's handler.
    =============================================================================== '''
    def __init__(self, notify_window, obKeys):
        threading.Thread.__init__(self)
        self._notify_window = notify_window
        self._want_abort = 0
        self.obKeys = obKeys
        self.start()

    def run(self):
        p = Properties.getInstance()
        db = DBConnect.getInstance()
        IC = ImageCollection.getInstance(p)
        
        # Load the tiles
        for obKey in self.obKeys:
            if self._want_abort:
                wx.PostEvent(self._notify_window, ImageResultEvent(None))
                db.CloseConnection()
                return
            
            imgs = IC.FetchTile(obKey)
            
            if self._notify_window:
                wx.PostEvent(self._notify_window, ImageResultEvent((obKey,imgs)))
            else:  # die if the parent has been closed
                db.CloseConnection()
                return
            
        db.CloseConnection()
        wx.PostEvent(self._notify_window, ImageResultEvent(None))

    def abort(self):
        self._want_abort = True