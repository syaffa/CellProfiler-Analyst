from ColorBarPanel import ColorBarPanel
from DBConnect import DBConnect, UniqueImageClause, image_key_columns
from MulticlassSQL import filter_table_prefix
from PlateMapPanel import *
from PlotPanel import *
from Properties import Properties
from wx.combo import OwnerDrawnComboBox as ComboBox
import ImageTools
import matplotlib.cm
import numpy as np
import os
import re
import wx

p = Properties.getInstance()
db = DBConnect.getInstance()

NO_FILTER = 'No filter'

ID_EXIT = wx.NewId()
LOG_SCALE    = 'log'
LINEAR_SCALE = 'linear'


class DataSourcePanel(wx.Panel):
    '''
    A panel with controls for selecting the source data for a densityplot 
    '''
    def __init__(self, parent, figpanel, **kwargs):
        wx.Panel.__init__(self, parent, **kwargs)
        
        # the panel to draw charts on
        self.figpanel = figpanel
        
        sizer = wx.BoxSizer(wx.VERTICAL)

        tables = db.GetTableNames()
        self.table_choice = ComboBox(self, -1, choices=tables, style=wx.CB_READONLY)
        self.table_choice.Select(tables.index(p.image_table))
        self.x_choice = ComboBox(self, -1, size=(200,-1), style=wx.CB_READONLY)
        self.y_choice = ComboBox(self, -1, size=(200,-1), style=wx.CB_READONLY)
        self.gridsize_input = wx.TextCtrl(self, -1, '100')
        maps = [m for m in matplotlib.cm.datad.keys() if not m.endswith("_r")]
        maps.sort()
        self.colormap_choice = ComboBox(self, -1, choices=maps, style=wx.CB_READONLY)
        self.colormap_choice.SetSelection(maps.index('jet'))
        self.x_scale_choice = ComboBox(self, -1, choices=[LINEAR_SCALE, LOG_SCALE], style=wx.CB_READONLY)
        self.x_scale_choice.Select(0)
        self.y_scale_choice = ComboBox(self, -1, choices=[LINEAR_SCALE, LOG_SCALE], style=wx.CB_READONLY)
        self.y_scale_choice.Select(0)
        self.filter_choice = ComboBox(self, -1, choices=[NO_FILTER]+p._filters_ordered, style=wx.CB_READONLY)
        self.filter_choice.Select(0)
        self.update_chart_btn = wx.Button(self, -1, "Update Chart")
        
        self.update_column_fields()
        
        sz = wx.BoxSizer(wx.HORIZONTAL)
        sz.Add(wx.StaticText(self, -1, "table:"))
        sz.AddSpacer((5,-1))
        sz.Add(self.table_choice, 1, wx.EXPAND)
        sizer.Add(sz, 1, wx.EXPAND)
        sizer.AddSpacer((-1,5))
        sz = wx.BoxSizer(wx.HORIZONTAL)
        
        sz.Add(wx.StaticText(self, -1, "x-axis:"))
        sz.AddSpacer((5,-1))
        sz.Add(self.x_choice, 1, wx.EXPAND)
        sz.AddSpacer((5,-1))
        sz.Add(wx.StaticText(self, -1, "x-scale:"))
        sz.AddSpacer((5,-1))
        sz.Add(self.x_scale_choice)
        sizer.Add(sz, 1, wx.EXPAND)
        sizer.AddSpacer((-1,5))
        
        sz = wx.BoxSizer(wx.HORIZONTAL)
        sz.Add(wx.StaticText(self, -1, "y-axis:"))
        sz.AddSpacer((5,-1))
        sz.Add(self.y_choice, 1, wx.EXPAND)
        sz.AddSpacer((5,-1))
        sz.Add(wx.StaticText(self, -1, "y-scale:"))
        sz.AddSpacer((5,-1))
        sz.Add(self.y_scale_choice)
        sizer.Add(sz, 1, wx.EXPAND)
        sizer.AddSpacer((-1,5))
        
        sz = wx.BoxSizer(wx.HORIZONTAL)        
        sz.Add(wx.StaticText(self, -1, "grid size:"))
        sz.AddSpacer((5,-1))
        sz.Add(self.gridsize_input, 1, wx.EXPAND)
        sz.AddSpacer((5,-1))
        sz.Add(wx.StaticText(self, label='color map:'))
        sz.AddSpacer((5,-1))
        sz.Add(self.colormap_choice, 1, wx.EXPAND)
        sizer.Add(sz, 1, wx.EXPAND)
        sizer.AddSpacer((-1,5))
        
        sz = wx.BoxSizer(wx.HORIZONTAL)
        sz.Add(wx.StaticText(self, -1, "filter:"))
        sz.AddSpacer((5,-1))
        sz.Add(self.filter_choice, 1, wx.EXPAND)
        sizer.Add(sz, 1, wx.EXPAND)
        sizer.AddSpacer((-1,5))
        
        sizer.Add(self.update_chart_btn)    
        
        wx.EVT_COMBOBOX(self.table_choice, -1, self.on_table_selected)
        wx.EVT_COMBOBOX(self.colormap_choice, -1, self.on_cmap_selected)
        wx.EVT_BUTTON(self.update_chart_btn, -1, self.on_update_pressed)   
        self.Bind(wx.EVT_SIZE, self._onsize)
        
        self.SetSizer(sizer)
        self.Show(1)

    def on_table_selected(self, evt):
        self.update_column_fields()
        
    def on_cmap_selected(self, evt):
        self.figpanel.set_colormap(self.colormap_choice.GetStringSelection())
        
    def update_column_fields(self):
        tablename = self.table_choice.GetStringSelection()
        fieldnames = self.get_numeric_columns_from_table(tablename)
        self.x_choice.Clear()
        self.x_choice.AppendItems(fieldnames)
        self.x_choice.SetSelection(0)
        self.y_choice.Clear()
        self.y_choice.AppendItems(fieldnames)
        self.y_choice.SetSelection(0)

    def get_numeric_columns_from_table(self, table):
        ''' Fetches names of numeric columns for the given table. '''
        measurements = db.GetColumnNames(table)
        types = db.GetColumnTypes(table)
        return [m for m,t in zip(measurements, types) if t in [float, int, long]]
        
    def on_update_pressed(self, evt):
        filter = self.filter_choice.GetStringSelection()
        points = self.loadpoints(self.table_choice.GetStringSelection(),
                                 self.x_choice.GetStringSelection(),
                                 self.y_choice.GetStringSelection(),
                                 filter)
        self.figpanel.setgridsize(int(self.gridsize_input.GetValue()))
        self.figpanel.set_x_scale(self.x_scale_choice.GetStringSelection())
        self.figpanel.set_y_scale(self.y_scale_choice.GetStringSelection())
        self.figpanel.set_x_label(self.x_choice.GetStringSelection())
        self.figpanel.set_y_label(self.y_choice.GetStringSelection())
        self.figpanel.set_colormap(self.colormap_choice.GetStringSelection())
        self.figpanel.setpointslists(points)
        self.figpanel.draw()
        
    def removefromchart(self, event):
        selected = self.plotfieldslistbox.GetSelection()
        self.plotfieldslistbox.Delete(selected)
        
    def loadpoints(self, tablename, xpoints, ypoints, filter=NO_FILTER):
        fields = '%s.%s, %s.%s'%(tablename, xpoints, tablename, ypoints)
        tables = tablename
        where_clause = ''
        if filter != NO_FILTER:
            # If a filter is applied we must compute a WHERE clause and add the 
            # filter table to the FROM clause
            tables += ', `%s`'%(filter_table_prefix+filter) 
            filter_clause = ' AND '.join(['%s.%s=`%s`.%s'%(tablename, id, filter_table_prefix+filter, id) 
                                          for id in db.GetLinkingColumnsForTable(tablename)])
            where_clause = 'WHERE %s'%(filter_clause)
        return [db.execute('SELECT %s FROM %s %s'%(fields, tables, where_clause))]
    
    def _onsize(self, evt):
        self.figpanel._SetSize()
        evt.Skip()
        

class DensityPanel(PlotPanel):
    def __init__(self, parent, **kwargs):
        self.parent = parent
        self.point_lists = []
        self.gridsize = 100
        self.cb = None
        self.x_scale = LINEAR_SCALE
        self.y_scale = LINEAR_SCALE
        self.x_label = ''
        self.y_label = ''
        self.cmap ='jet'
        
        # initiate plotter
        PlotPanel.__init__(self, parent, color=(255, 255, 255), **kwargs)
        self.SetColor((255, 255, 255))
    
    def setpointslists(self, points):
        self.point_lists = points
    
    def getpointslists(self):
        return self.point_lists
    
    def setgridsize(self, gridsize):
        self.gridsize = gridsize

    def set_x_scale(self, scale):
        self.x_scale = scale
    
    def set_y_scale(self, scale):
        self.y_scale = scale

    def set_x_label(self, label):
        self.x_label = label
    
    def set_y_label(self, label):
        self.y_label = label
        
    def set_colormap(self, cmap):
        self.cmap = cmap
        self.draw()
        
    def draw(self):
        #Draw data.
        self.clear_figure()
        self.subplot = self.figure.add_subplot(111)
            
        for i, pt_list in enumerate(self.point_lists):
            plot_pts = np.array(pt_list)
            
            if self.x_scale == LOG_SCALE:
                plot_pts = plot_pts[(plot_pts[:,0]>0)]
            if self.y_scale == LOG_SCALE:
                plot_pts = plot_pts[(plot_pts[:,1]>0)]

            hb = self.subplot.hexbin(plot_pts[:, 0], plot_pts[:, 1], 
                                     gridsize=self.gridsize,
                                     xscale=self.x_scale,
                                     yscale=self.y_scale,
                                     cmap=matplotlib.cm.get_cmap(self.cmap))

            self.cb = self.figure.colorbar(hb)
            
            self.subplot.set_xlabel(self.x_label)
            self.subplot.set_ylabel(self.y_label)
            
            xmin = np.nanmin(plot_pts[:,0])
            xmax = np.nanmax(plot_pts[:,0])
            ymin = np.nanmin(plot_pts[:,1])
            ymax = np.nanmax(plot_pts[:,1])

            # Pad all sides
            if self.x_scale==LOG_SCALE:
                xmin = xmin/1.5
                xmax = xmax*1.5
            else:
                xmin = xmin-(xmax-xmin)/20.
                xmax = xmax+(xmax-xmin)/20.
                
            if self.y_scale==LOG_SCALE:
                ymin = ymin/1.5
                ymax = ymax*1.5
            else:
                ymin = ymin-(ymax-ymin)/20.
                ymax = ymax+(ymax-ymin)/20.

            self.subplot.axis([xmin, xmax, ymin, ymax])

        self.canvas.draw()
        

class Density(wx.Frame):
    '''
    A very basic density plot with controls for setting it's data source.
    '''
    def __init__(self, parent, size=(600,600)):
        wx.Frame.__init__(self, parent, -1, size=size, title='density plot')
        
        figpanel = DensityPanel(self)
        configpanel = DataSourcePanel(self, figpanel)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(figpanel, 1, wx.EXPAND)
        sizer.Add(configpanel, 0, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(sizer)
        
def LoadProperties():
    import os
    dlg = wx.FileDialog(None, "Select a the file containing your properties.", style=wx.OPEN|wx.FD_CHANGE_DIR)
    if dlg.ShowModal() == wx.ID_OK:
        filename = dlg.GetPath()
        os.chdir(os.path.split(filename)[0])  # wx.FD_CHANGE_DIR doesn't seem to work in the FileDialog, so I do it explicitly
        p.LoadFile(filename)
    else:
        print 'Densityplot requires a properties file.  Exiting.'
        exit()

            
if __name__ == "__main__":
    app = wx.PySimpleApp()
        
    # Load a properties file if passed in args
    if len(sys.argv) > 1:
        propsFile = sys.argv[1]
        p.LoadFile(propsFile)
    else:
        LoadProperties()

    import MulticlassSQL
    MulticlassSQL.CreateFilterTables()
    
    density = Density(None)
    density.Show()
    
    app.MainLoop()