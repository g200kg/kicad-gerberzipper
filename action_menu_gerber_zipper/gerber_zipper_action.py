# coding: utf-8
# file : gerber_zipper_action.py
#
# Copyright (C) 2020 g200kg
#   Released under MIT License
#

import pcbnew
from pcbnew import *
import wx
import wx.grid
import os
import locale
import zipfile
import glob
import json
import sys
import codecs
import inspect
import traceback

version = "1.0.4"
strtab = {}

layer_list = [
    {'name':'F.Cu', 'id':pcbnew.F_Cu, 'fnamekey':'${filename(F.Cu)}'},
    {'name':'B.Cu', 'id':pcbnew.B_Cu, 'fnamekey':'${filename(B.Cu)}'},
    {'name':'F.Adhes', 'id':pcbnew.F_Adhes, 'fnamekey':'${filename(F.Adhes)}'},
    {'name':'B.Adhes', 'id':pcbnew.B_Adhes, 'fnamekey':'${filename(B.Adhes)}'},
    {'name':'F.Paste', 'id':pcbnew.F_Paste, 'fnamekey':'${filename(F.Paste)}'},
    {'name':'B.Paste', 'id':pcbnew.B_Paste, 'fnamekey':'${filename(B.Paste)}'},
    {'name':'F.SilkS', 'id':pcbnew.F_SilkS, 'fnamekey':'${filename(F.SilkS)}'},
    {'name':'B.SilkS', 'id':pcbnew.B_SilkS, 'fnamekey':'${filename(B.SilkS)}'},
    {'name':'F.Mask', 'id':pcbnew.F_Mask, 'fnamekey':'${filename(F.Mask)}'},
    {'name':'B.Mask', 'id':pcbnew.B_Mask, 'fnamekey':'${filename(B.Mask)}'},
    {'name':'Dwgs.User', 'id':pcbnew.Dwgs_User, 'fnamekey':'${filename(Dwgs.User)}'},
    {'name':'Cmts.User', 'id':pcbnew.Cmts_User, 'fnamekey':'${filename(Cmts.User)}'},
    {'name':'Eco1.User', 'id':pcbnew.Eco1_User, 'fnamekey':'${filename(Eco1.User)}'},
    {'name':'Eco2.User', 'id':pcbnew.Eco2_User, 'fnamekey':'${filename(Eco2.User)}'},
    {'name':'Edge.Cuts', 'id':pcbnew.Edge_Cuts, 'fnamekey':'${filename(Edge.Cuts)}'},
    {'name':'F.CrtYd', 'id':pcbnew.F_CrtYd, 'fnamekey':'${filename(F.CrtYd)}'},
    {'name':'B.CrtYd', 'id':pcbnew.B_CrtYd, 'fnamekey':'${filename(B.CrtYd)}'},
    {'name':'F.Fab', 'id':pcbnew.F_Fab, 'fnamekey':'${filename(F.Fab)}'},
    {'name':'B.Fab', 'id':pcbnew.B_Fab, 'fnamekey':'${filename(B.Fab)}'},
    {'name':'In1.Cu', 'id':pcbnew.In1_Cu, 'fnamekey':'${filename(In1.Cu)}'},
    {'name':'In2.Cu', 'id':pcbnew.In2_Cu, 'fnamekey':'${filename(In2.Cu)}'},
    {'name':'In3.Cu', 'id':pcbnew.In3_Cu, 'fnamekey':'${filename(In3.Cu)}'},
    {'name':'In4.Cu', 'id':pcbnew.In4_Cu, 'fnamekey':'${filename(In4.Cu)}'},
    {'name':'In5.Cu', 'id':pcbnew.In5_Cu, 'fnamekey':'${filename(In5.Cu)}'},
    {'name':'In6.Cu', 'id':pcbnew.In6_Cu, 'fnamekey':'${filename(In6.Cu)}'}
]

default_settings = {
  "Name":"ManufacturersName",
  "Description":"description",
  "URL":"https://example.com/",
  "GerberDir":"Gerber",
  "ZipFilename":"*.ZIP",
  "Layers": {
    "F.Cu":"",
    "B.Cu":"",
    "F.Paste":"",
    "B.Paste":"",
    "F.SilkS":"",
    "B.SilkS":"",
    "F.Mask":"",
    "B.Mask":"",
    "Edge.Cuts":"",
    "In1.Cu":"",
    "In2.Cu":"",
    "In3.Cu":"",
    "In4.Cu":"",
    "In5.Cu":"",
    "In6.Cu":""
  },
  "PlotBorderAndTitle":False,
  "PlotFootprintValues":True,
  "PlotFootprintReferences":True,
  "ForcePlotInvisible":False,
  "ExcludeEdgeLayer":True,
  "ExcludePadsFromSilk":True,
  "DoNotTentVias":False,
  "UseAuxOrigin":False,
  "LineWidth":0.1,

  "CoodinateFormat46":True,
  "SubtractMaskFromSilk":True,
  "UseExtendedX2format": False,
  "IncludeNetlistInfo":False,

  "Drill": {
    "Drill":"",
    "DrillMap":"",
    "NPTH":"",
    "NPTHMap":"",
    "Report":""
  },
  "DrillUnitMM":True,
  "MirrorYAxis":False,
  "MinimalHeader":False,
  "MergePTHandNPTH":False,
  "RouteModeForOvalHoles":True,
  "ZerosFormat":{
    "DecimalFormat":True,
    "SuppressLeading":False,
    "SuppressTrailing":False,
    "KeepZeros":False
  },
  "MapFileFormat":{
    "HPGL":False,
    "PostScript":False,
    "Gerber":True,
    "DXF":False,
    "SVG":False,
    "PDF":False
  },
  "OptionalFiles":[]
}

chsize = (10,20)

def message(s):
    print('GerberZipper: '+s)

def alert(s, icon=0):
    wx.MessageBox(s, 'Gerber Zipper', wx.OK|icon)

def InitEm():
    global chsize
    dc=wx.ScreenDC()
    font=wx.Font(pointSize=10,family=wx.DEFAULT,style=wx.NORMAL,weight=wx.NORMAL)
    dc.SetFont(font)
    tx=dc.GetTextExtent("M")
    chsize=(tx[0],tx[1]*1.5)

def Em(x,y,dx=0,dy=0):
    return (chsize[0]*x+dx, chsize[1]*y+dy)

def getindex(s):
    for i in range(len(layer_list)):
        if layer_list[i]['name']==s:
            return i
    return -1

def getid(s):
    for i in range(len(layer_list)):
        if layer_list[i]['name']==s:
            return layer_list[i]['id']
    return 0

def getstr(s):
    lang = wx.Locale.GetCanonicalName(wx.GetLocale())
    lang = lang if lang else 'default'
    tab = strtab['default']
    if (lang in strtab):
        tab = strtab[lang]
    else:
        for x in strtab:
            if lang[0:3] in x:
                tab = strtab[x]
    return tab[s]

def forcedel(fname):
    if os.path.exists(fname):
        os.remove(fname)

def forceren(src, dst):
    if(src==dst):
        return
    forcedel(dst)
    if os.path.exists(src):
        os.rename(src, dst)

def refill(board):
    try:
        filler = pcbnew.ZONE_FILLER(board)
        zones = board.Zones()
        filler.Fill(zones)
    except:
        message('Refill Failed')

class GerberZipperAction( pcbnew.ActionPlugin ):
    def defaults( self ):
        self.name = "Gerber Zipper"
        self.category = "Plot"
        self.description = "Make Gerber-Zip-file for selected PCB manufacturers"
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), 'icon.png')

    def Run(self):
        class Dialog(wx.Dialog):
            def __init__(self, parent):
                global strtab
                prefix_path = os.path.join(os.path.dirname(__file__))
                settings_fname = os.path.join(prefix_path, 'settings.json')
                self.plugin_settings_data = {}
                if os.path.exists(settings_fname):
                    self.plugin_settings_data = json.load(open(settings_fname))
                else:
                    self.plugin_settings_data["default"] = 0
                    json.dump(self.plugin_settings_data, open(settings_fname, "w"))

                self.icon_file_name = os.path.join(os.path.dirname(__file__), 'icon.png')
                self.manufacturers_dir = os.path.join(os.path.dirname(__file__), 'Manufacturers')
                manufacturers_list = glob.glob('%s/*.json' % self.manufacturers_dir)
                self.json_data = []
                for fname in manufacturers_list:
                    try:
                        self.json_data.append(json.load(open(fname)))
                    except Exception as err:
                        alert('JSON error \n\n File : %s\n%s' % (os.path.basename(fname), err.message), wx.ICON_WARNING)
                self.json_data = sorted(self.json_data, key=lambda x: x['Name'])
                self.locale_dir = os.path.join(os.path.dirname(__file__), "Locale")
                locale_list = glob.glob('%s/*.json' % self.locale_dir)
                strtab = {}
                for fpath in locale_list:
                    fname = os.path.splitext(os.path.basename(fpath))[0]
                    print (fname)
                    strtab[fname] = json.load(open(fpath))
                InitEm()
                wx.Dialog.__init__(self, parent, id=-1, title='Gerber-Zipper '+version, size=Em(65,12),
                                   style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
                self.panel = wx.Panel(self)
                icon=wx.Icon(self.icon_file_name)
                self.SetIcon(icon)
                manufacturers_arr=[]
                for item in self.json_data:
                    manufacturers_arr.append(item['Name'])
                
                wx.StaticText(self.panel, wx.ID_ANY, getstr('LABEL'), size=Em(70,1), pos=Em(1,1))
                wx.StaticText(self.panel, wx.ID_ANY, getstr('MENUFACTURERS'),size=Em(14,1), pos=Em(1,2.5))

                self.manufacturers = wx.ComboBox(self.panel, wx.ID_ANY, 'Select Manufacturers', size=Em(30,1.5), pos=Em(16,2.5), choices=manufacturers_arr, style=wx.CB_READONLY)
                wx.StaticText(self.panel, wx.ID_ANY, getstr('URL'),size=Em(14,1), pos=Em(1,4))
                self.url = wx.TextCtrl(self.panel, wx.ID_ANY, '', size=Em(30,1), pos=Em(16,4), style=wx.TE_READONLY)
                wx.StaticText(self.panel, wx.ID_ANY, getstr('GERBERDIR'),size=Em(14,1), pos=Em(1,5.1))
                self.gerberdir = wx.TextCtrl(self.panel, wx.ID_ANY, '',size=Em(30,1), pos=Em(16,5.1))
                wx.StaticText(self.panel, wx.ID_ANY, getstr('ZIPFNAME'),size=Em(14,1), pos=Em(1,6.2))
                self.zipfilename = wx.TextCtrl(self.panel, wx.ID_ANY, '',size=Em(30,1), pos=Em(16,6.2))
                wx.StaticText(self.panel, wx.ID_ANY, getstr('DESCRIPTION'),size=Em(14,1), pos=Em(1,7.3))
                self.label = wx.StaticText(self.panel, wx.ID_ANY, '',size=Em(45,1), pos=Em(16,7.3))

                self.manufacturers.SetSelection(self.plugin_settings_data.get("default",0))
                self.detailbtn = wx.ToggleButton(self.panel, wx.ID_ANY, getstr('DETAIL'),size=Em(15,1),pos=Em(2,8.5))
                self.execbtn = wx.Button(self.panel, wx.ID_ANY, getstr('EXEC'),size=Em(15,1),pos=Em(18,8.5))
                self.clsbtn = wx.Button(self.panel, wx.ID_ANY, getstr('CLOSE'),size=Em(15,1),pos=Em(34,8.5))
                wx.StaticLine(self.panel, wx.ID_ANY, size=(Em(65,1)[0],2), pos=Em(1,10.5))
                self.manufacturers.Bind(wx.EVT_COMBOBOX, self.OnManufacturers)
                self.clsbtn.Bind(wx.EVT_BUTTON, self.OnClose)
                self.execbtn.Bind(wx.EVT_BUTTON, self.OnExec)
                self.detailbtn.Bind(wx.EVT_TOGGLEBUTTON, self.OnDetail)

                wx.StaticBox(self.panel, wx.ID_ANY,'Gerber', pos=Em(2,11), size=Em(40,15))
                wx.StaticBox(self.panel, wx.ID_ANY,'Other', pos=Em(2,26), size=Em(64,3))
                wx.StaticBox(self.panel, wx.ID_ANY,'Drill', pos=Em(43,11), size=Em(20,15))
                wx.StaticText(self.panel, wx.ID_ANY, getstr('DESC2'), pos=Em(2,29))

#                self.panel = panel
                self.layer = wx.grid.Grid(self.panel, wx.ID_ANY, size=Em(18,13), pos=Em(3,12))
                self.layer.SetColLabelSize(Em(1,1)[1])
                self.layer.DisableDragColSize()
                self.layer.DisableDragRowSize()
                self.layer.CreateGrid(len(layer_list), 2)
                self.layer.SetColLabelValue(0, 'Layer')
                self.layer.SetColLabelValue(1, 'Filename')
                self.layer.SetRowLabelSize(1)
                self.layer.ShowScrollbars(wx.SHOW_SB_NEVER,wx.SHOW_SB_DEFAULT)
                self.layer.SetColSize(0, Em(7,1)[0])
                self.layer.SetColSize(1, Em(9,1)[0])
                for i in range(len(layer_list)):
                    self.layer.SetCellValue(i, 0, layer_list[i]['name'])
                    self.layer.SetReadOnly(i, 0, isReadOnly=True)
                self.opt_PlotBorderAndTitle = wx.CheckBox(self.panel, wx.ID_ANY, 'PlotBorderAndTitle', pos=Em(23,12))
                self.opt_PlotFootprintValues = wx.CheckBox(self.panel, wx.ID_ANY, 'PlotFootprintValues', pos=Em(23,13))
                self.opt_PlotFootprintReferences = wx.CheckBox(self.panel, wx.ID_ANY, 'PlotFootprintReferences', pos=Em(23,14))
                self.opt_ForcePlotInvisible = wx.CheckBox(self.panel, wx.ID_ANY, 'ForcePlotInvisible', pos=Em(23,15))
                self.opt_ExcludeEdgeLayer = wx.CheckBox(self.panel, wx.ID_ANY, 'ExcludeEdgeLayer', pos=Em(23,16))
                self.opt_ExcludePadsFromSilk = wx.CheckBox(self.panel, wx.ID_ANY, 'ExcludePadsFromSilk', pos=Em(23,17))
                self.opt_DoNotTentVias = wx.CheckBox(self.panel, wx.ID_ANY, 'DoNotTentVias', pos=Em(23,18))
                self.opt_UseAuxOrigin = wx.CheckBox(self.panel, wx.ID_ANY, 'UseAuxOrigin', pos=Em(23,19))
                self.opt_LineWidthLabel = wx.StaticText(self.panel, wx.ID_ANY, 'LineWidth(mm):', pos=Em(23,20))
                self.opt_LineWidth = wx.TextCtrl(self.panel, wx.ID_ANY, '', size=Em(5,1), pos=Em(33,20))
                self.opt_SubtractMaskFromSilk = wx.CheckBox(self.panel, wx.ID_ANY, 'SubtractMaskFromSilk', pos=Em(23, 21))
                self.opt_UseExtendedX2format = wx.CheckBox(self.panel, wx.ID_ANY, 'UseExtendedX2format', pos=Em(23, 22))
                self.opt_CoodinateFormat46 = wx.CheckBox(self.panel, wx.ID_ANY, 'CoodinateFormat46', pos=Em(23, 23))
                self.opt_IncludeNetlistInfo = wx.CheckBox(self.panel, wx.ID_ANY, 'IncludeNetlistInfo', pos=Em(23, 24))

                self.drill = wx.grid.Grid(self.panel, wx.ID_ANY, size=Em(18,6,1,0), pos=Em(44,12))
                self.drill.DisableDragColSize()
                self.drill.DisableDragRowSize()
                self.drill.CreateGrid(5, 2)
                self.drill.DisableDragGridSize()
                self.drill.ShowScrollbars(wx.SHOW_SB_NEVER,wx.SHOW_SB_NEVER)
                self.drill.SetColLabelValue(0, 'Drill')
                self.drill.SetColLabelValue(1, 'Filename')
                self.drill.SetRowLabelSize(1)
                self.drill.SetColSize(0, Em(9,1)[0])
                self.drill.SetColSize(1, Em(9,1)[0])
                drillfile = ['Drill', 'DrillMap', 'NPTH', 'NPTHMap', 'Report']
                self.drill.SetColLabelSize(Em(1,1)[1])
                for i in range(len(drillfile)):
                    self.drill.SetCellValue(i, 0, drillfile[i])
                    self.drill.SetReadOnly(i, 0, True)
                    self.drill.SetRowSize(i, Em(1,1)[1])
                wx.StaticText(self.panel, wx.ID_ANY, 'Drill Unit :', pos=Em(44,18))
                self.opt_DrillUnit = wx.ComboBox(self.panel, wx.ID_ANY, '', choices=('inch','mm'), style=wx.CB_READONLY, pos=Em(53,18), size=Em(8,1))
                self.opt_MirrorYAxis = wx.CheckBox(self.panel, wx.ID_ANY, 'MirrorYAxis', pos=Em(44,19))
                self.opt_MinimalHeader = wx.CheckBox(self.panel, wx.ID_ANY, 'MinimalHeader', pos=Em(44,20))
                self.opt_MergePTHandNPTH = wx.CheckBox(self.panel, wx.ID_ANY, 'MergePTHandNPTH', pos=Em(44,21))
                self.opt_RouteModeForOvalHoles = wx.CheckBox(self.panel, wx.ID_ANY, 'RouteModeForOvalHoles', pos=Em(44,22))
                wx.StaticText(self.panel, wx.ID_ANY, 'Zeros :', pos=Em(44,23))
                self.opt_ZerosFormat = wx.ComboBox(self.panel, wx.ID_ANY, '', choices=('DecimalFormat','SuppressLeading','SuppresTrailing', 'KeepZeros'), pos=Em(50,23), size=Em(12,1.5), style=wx.CB_READONLY)
                wx.StaticText(self.panel, wx.ID_ANY, 'MapFileFormat :', pos=Em(44,24.5))
                self.opt_MapFileFormat = wx.ComboBox(self.panel, wx.ID_ANY, '', choices=('HPGL','PostScript','Gerber','DXF','SVG','PDF'), pos=Em(54,24.5), size=Em(8,1.5), style=wx.CB_READONLY)

                self.opt_OptionalLabel = wx.StaticText(self.panel, wx.ID_ANY, 'OptionalFile:', pos=Em(4,27.5))
                self.opt_OptionalFile = wx.TextCtrl(self.panel, wx.ID_ANY, '', size=Em(12,1), pos=Em(15,27.5))
                self.opt_OptionalContent = wx.TextCtrl(self.panel, wx.ID_ANY, '', size=Em(37,1), pos=Em(28,27.5))

#                self.editor = Editor(self.panel)
                self.Select(self.plugin_settings_data.get("default",0))

            def Set(self, settings):
                self.settings=dict(default_settings,**settings)
                l = self.settings.get('Layers',{})
                for i in range(self.layer.GetNumberRows()):
                    k = self.layer.GetCellValue(i, 0)
                    if l.get(k,None) != None:
                        self.layer.SetCellValue(i, 1, l.get(k))
                    else:
                        self.layer.SetCellValue(i, 1, '')
                l = self.settings.get('Drill',{})
                for i in range(self.drill.GetNumberRows()):
                    k = self.drill.GetCellValue(i,0)
                    if l.get(k,None) != None:
                        self.drill.SetCellValue(i, 1, l.get(k))
                    else:
                        self.drill.SetCellValue(i, 1, '')
                self.opt_PlotBorderAndTitle.SetValue(self.settings.get('PlotBorderAndTitle',False))
                self.opt_PlotFootprintValues.SetValue(self.settings.get('PlotFootprintValues',True))
                self.opt_PlotFootprintReferences.SetValue(self.settings.get('PlotFootprintReferences',True))
                self.opt_ForcePlotInvisible.SetValue(self.settings.get('ForcePlotInvisible',False))
                self.opt_ExcludeEdgeLayer.SetValue(self.settings.get('ExcludeEdgeLayer',True))
                self.opt_ExcludePadsFromSilk.SetValue(self.settings.get('ExcludePadsFromSilk',True))
                self.opt_DoNotTentVias.SetValue(self.settings.get('DoNotTentVias',False))
                self.opt_UseAuxOrigin.SetValue(self.settings.get('UseAuxOrigin', False))
                self.opt_LineWidth.SetValue(str(self.settings.get('LineWidth', 0.1)))
                self.opt_SubtractMaskFromSilk.SetValue(self.settings.get('SubtractMaskFromSilk', False))
                self.opt_UseExtendedX2format.SetValue(self.settings.get('UseExtendedX2format', False))
                self.opt_CoodinateFormat46.SetValue(self.settings.get('CoodinateFormat46',True))
                self.opt_IncludeNetlistInfo.SetValue(self.settings.get('IncludeNetlistInfo',False))
                self.opt_DrillUnit.SetSelection(1 if self.settings.get('DrillUnitMM',True) else 0)
                self.opt_MirrorYAxis.SetValue(self.settings.get('MirrorYAxis', False))
                self.opt_MinimalHeader.SetValue(self.settings.get('MinimalHeader', False))
                self.opt_MergePTHandNPTH.SetValue(self.settings.get('MergePTHandNPTH', False))
                self.opt_RouteModeForOvalHoles.SetValue(self.settings.get('RouteModeForOvalHoles', True))
                zeros = self.settings.get('ZerosFormat',{})
                i = 0
                for k in zeros:
                    if(zeros[k]):
                        i = {'DecimalFormat':0,'SuppressLeading':1,'SuppressTrailing':2,'KeepZeros':3}.get(k,0)
                self.opt_ZerosFormat.SetSelection(i)

                map = self.settings.get('MapFileFormat',{})
                i = 2
                for k in map:
                    if(map[k]):
                        i = {'HPGL':0,'PostScript':1,'Gerber':2,'DXF':3,'SVG':4,'PDF':5}.get(k,2)
                self.opt_MapFileFormat.SetSelection(i)
                files=self.settings.get('OptionalFiles',[])
                if len(files)==0:
                    files=[{'name':'','content':''}]
                self.opt_OptionalFile.SetValue(files[0]['name'])
                self.opt_OptionalContent.SetValue(files[0]['content'])

            def Get(self):
                l = self.settings.get('Layers',{})
                for i in range(self.layer.GetNumberRows()):
                    k = self.layer.GetCellValue(i, 0)
                    v = self.layer.GetCellValue(i, 1)
                    l[k] = v
                self.settings['Layers'] = l
                d = self.settings.get('Drill',{})
                for i in range(self.drill.GetNumberRows()):
                    k = self.drill.GetCellValue(i, 0)
                    v = self.drill.GetCellValue(i, 1)
                    d[k] = v
                self.settings['Drill'] = d
                self.settings['PlotBorderAndTitle'] = self.opt_PlotBorderAndTitle.GetValue()
                self.settings['PlotFootprintValues'] = self.opt_PlotFootprintValues.GetValue()
                self.settings['PlotFootprintReferences'] = self.opt_PlotFootprintReferences.GetValue()
                self.settings['ForcePlotInvisible'] = self.opt_ForcePlotInvisible.GetValue()
                self.settings['ExcludeEdgeLayer'] = self.opt_ExcludeEdgeLayer.GetValue()
                self.settings['ExcludePadsFromSilk'] = self.opt_ExcludePadsFromSilk.GetValue()
                self.settings['DoNotTentVias'] = self.opt_DoNotTentVias.GetValue()
                self.settings['UseAuxOrigin'] = self.opt_UseAuxOrigin.GetValue()
                self.settings['LineWidth'] = self.opt_LineWidth.GetValue()
                self.settings['SubtractMaskFromSilk'] = self.opt_SubtractMaskFromSilk.GetValue()
                self.settings['UseExtendedX2format'] = self.opt_UseExtendedX2format.GetValue()
                self.settings['CoodinateFormat46'] = self.opt_CoodinateFormat46.GetValue()
                self.settings['IncludeNetlistInfo'] = self.opt_IncludeNetlistInfo.GetValue()
                self.settings['DrillUnitMM'] = True if self.opt_DrillUnit.GetSelection() else False
                self.settings['MirrorYAxis'] = self.opt_MirrorYAxis.GetValue()
                self.settings['MinimalHeader'] = self.opt_MinimalHeader.GetValue()
                self.settings['MergePTHandNPTH'] = self.opt_MergePTHandNPTH.GetValue()
                self.settings['RouteModeForOvalHoles'] = self.opt_RouteModeForOvalHoles.GetValue()
                zeros = self.settings['ZerosFormat']
                i = self.opt_ZerosFormat.GetSelection()
                zeros['DecimalFormat'] = i == 0
                zeros['SuppressLeading'] = i == 1
                zeros['SuppressTrailing'] = i == 2
                zeros['KeepZeros'] = i == 3
                map = self.settings['MapFileFormat']
                i = self.opt_MapFileFormat.GetSelection()
                map['HPGL'] = i == 0
                map['PostScript'] = i == 1
                map['Gerber'] = i == 2
                map['DXF'] = i == 3
                map['SVG'] = i == 4
                map['PDF'] = i == 5
                f = {'name':self.opt_OptionalFile.GetValue(), 'content':self.opt_OptionalContent.GetValue()}
                self.settings['OptionalFiles'] = [f]
                return self.settings

            def Select(self,n):
                self.settings = self.json_data[n]
                # Save this selection as default
                self.plugin_settings_data["default"] = n
                prefix_path = os.path.join(os.path.dirname(__file__))
                settings_fname = os.path.join(prefix_path, 'settings.json');                
                json.dump(self.plugin_settings_data, open(settings_fname,"w"))
                self.label.SetLabel(self.settings.get('Description', ''))
                self.url.SetValue(self.settings.get('URL','---'))
                self.gerberdir.SetValue(self.settings.get('GerberDir','Gerber'))
                self.zipfilename.SetValue(self.settings.get('ZipFilename','*.ZIP'))
#                self.editor.Set(self.settings)
                self.Set(self.settings)

            def OnManufacturers(self,e):
                obj = e.GetEventObject()
                self.Select(obj.GetSelection())
                e.Skip()

            def OnDetail(self,e):
                if self.detailbtn.GetValue():
                    sz=Em(65,32)
                    self.SetSize(wx.Size(sz[0],sz[1]))
                    self.opt_ZerosFormat.SetPosition(wx.Point(Em(50,23)[0],Em(50,23)[1]))
                else:
                    sz=Em(65,12)
                    self.SetSize(wx.Size(sz[0],sz[1]))
                e.Skip()

            def OnClose(self,e):
                e.Skip()
                self.Close()

            def OnExec(self,e):
                try:
#                    self.settings = self.editor.Get()
                    self.settings = self.Get()
                    global zip_fname
                    board = pcbnew.GetBoard()
                    board_fname = board.GetFileName()
                    board_basename = (os.path.splitext(os.path.basename(board_fname)))[0]
                    gerber_dir = self.gerberdir.GetValue()
                    if gerber_dir[0:2] == '~/':
                        gerber_dir = '%s/%s' % (os.environ['HOME'], gerber_dir[2:])
                    if gerber_dir[0] != '/' and gerber_dir[1] != ':':
                        gerber_dir = '%s/%s' % (os.path.dirname(board_fname), gerber_dir)
                    zip_fname = '%s/%s' % (gerber_dir, self.zipfilename.GetValue().replace('*',board_basename))
                    if not os.path.exists(gerber_dir):
                        os.mkdir(gerber_dir)
                    refill(board)
                    zipfiles = []
                # PLOT
                    message('PlotStart')
                    pc = pcbnew.PLOT_CONTROLLER(board)
                    po = pc.GetPlotOptions()

                    po.SetOutputDirectory(gerber_dir)
                    po.SetPlotFrameRef( self.settings.get('PlotBorderAndTitle',False))
                    po.SetPlotValue( self.settings.get('PlotFootprintValues',True))
                    po.SetPlotReference( self.settings.get('PlotFootprintReferences',True))
                    po.SetPlotInvisibleText( self.settings.get('ForcePlotInvisible',False))
                    po.SetExcludeEdgeLayer( self.settings.get('ExcludeEdgeLayer',True))
                    if hasattr(po,'SetPlotPadsOnSilkLayer'):
                        po.SetPlotPadsOnSilkLayer( not self.settings.get('ExcludePadsFromSilk',False))
                    po.SetPlotViaOnMaskLayer( self.settings.get('DoNotTentVias',False))
                    if hasattr(po,'SetUseAuxOrigin'):
                        po.SetUseAuxOrigin(self.settings.get('UseAuxOrigin',False))
                    if hasattr(po,'SetLineWidth'):
                        po.SetLineWidth(FromMM(float(self.settings.get('LineWidth'))))
                    po.SetSubtractMaskFromSilk(self.settings.get('SubtractMaskFromSilk',True))
                    po.SetUseGerberX2format(self.settings.get('UseExtendedX2format',False))
                    po.SetIncludeGerberNetlistInfo(self.settings.get('IncludeNetlistInfo',False))
                    po.SetGerberPrecision(6 if self.settings.get('CoodinateFormat46',True) else 5)
#                   SetDrillMarksType() : Draw Drill point to Cu layers if 1 (default)
#                                         But seems set to 0 in Plot Dialog
                    po.SetDrillMarksType(0)
                    layer = self.settings.get('Layers',{})
                    forcedel(zip_fname)
                    for i in range(len(layer_list)):
                        layer_list[i]['fname'] = ''
                    for i in layer:
                        fnam = layer[i]
                        id = getid(i)
                        if(len(fnam)>0 and board.IsLayerEnabled(id)):
                            pc.SetLayer(id)
                            pc.OpenPlotfile(i,PLOT_FORMAT_GERBER,i)
                            pc.PlotLayer()
                            pc.ClosePlot()
                            targetname = '%s/%s' % (gerber_dir, fnam.replace('*',board_basename))
                            forcedel(targetname)
                            forceren(pc.GetPlotFileName(), targetname)
                            layer_list[getindex(i)]['fname'] = targetname
                            zipfiles.append(targetname)
                    message('Drill')
                # DRILL
                    drill_fname = ''
                    drill_map_fname = ''
                    npth_fname = ''
                    npth_map_fname =''
                    drill_report_fname = ''
                    drill = self.settings.get('Drill',{})
                    fname = drill.get('Drill','')
                    if len(fname)>0:
                        drill_fname = '%s/%s' % (gerber_dir, fname.replace('*', board_basename))
                        forcedel(drill_fname)
                    fname = drill.get('DrillMap','')
                    if len(fname)>0:
                        drill_map_fname = '%s/%s' % (gerber_dir, fname.replace('*', board_basename))
                        forcedel(drill_map_fname)
                    fname = drill.get('NPTH','')
                    if len(fname)>0:
                        npth_fname = '%s/%s' % (gerber_dir, fname.replace('*', board_basename))
                        forcedel(npth_fname)
                    fname = drill.get('NPTHMap','')
                    if len(fname)>0:
                        npth_map_fname = '%s/%s' % (gerber_dir, fname.replace('*', board_basename))
                        forcedel(npth_map_fname)
                    fname = drill.get('Report','')
                    if len(fname)>0:
                        drill_report_fname = '%s/%s' % (gerber_dir, fname.replace('*', board_basename))
                        forcedel(drill_report_fname)

                    ew = EXCELLON_WRITER(board)
                    excellon_format = EXCELLON_WRITER.DECIMAL_FORMAT
                    zeros = self.settings.get('ZerosFormat')
                    if zeros.get('SuppressLeading'):
                        excellon_format = EXCELLON_WRITER.SUPPRESS_LEADING
                    if zeros.get('SuppressTrailing'):
                        excellon_format = EXCELLON_WRITER.SUPPRESS_TRAILING
                    if zeros.get('KeepZeros'):
                        excellon_format = EXCELLON_WRITER.KEEP_ZEROS
                    ew.SetFormat(self.settings.get('DrillUnitMM',True), excellon_format, 3, 3)
                    offset = wxPoint(0,0)
                    if self.settings.get('UseAuxOrigin',False):
                        if hasattr(board, 'GetAuxOrigin'):
                            offset = board.GetAuxOrigin()
                        else:
                            bds = board.GetDesignSettings()
                            offset = bds.m_AuxOrigin
                    ew.SetOptions(self.settings.get('MirrorYAxis',False), self.settings.get('MinimalHeader',False), offset, self.settings.get('MergePTHandNPTH',False))
                    ew.SetRouteModeForOvalHoles(self.settings.get('RouteModeForOvalHoles'))
                    map_format = pcbnew.PLOT_FORMAT_GERBER
                    map_ext = 'gbr'
                    map = self.settings.get('MapFileFormat')
                    if map.get('HPGL'):
                        map_format = pcbnew.PLOT_FORMAT_HPGL
                        map_ext = 'plt'
                    if map.get('PostScript'):
                        map_format = pcbnew.PLOT_FORMAT_POST
                        map_ext = 'ps'
                    if map.get('Gerber'):
                        map_format = pcbnew.PLOT_FORMAT_GERBER
                        map_ext = 'gbr'
                    if map.get('DXF'):
                        map_format = pcbnew.PLOT_FORMAT_DXF
                        map_ext = 'dxf'
                    if map.get('SVG'):
                        map_format = pcbnew.PLOT_FORMAT_SVG
                        map_ext = 'svg'
                    if map.get('PDF'):
                        map_format = pcbnew.PLOT_FORMAT_PDF
                        map_ext = 'pdf'
                    ew.SetMapFileFormat(map_format)
                    enable_map = len(drill_map_fname)>0 or len(npth_map_fname)>0
                    message('MapFile')
                    ew.CreateDrillandMapFilesSet(gerber_dir,True,enable_map)
                    if self.settings.get('MergePTHandNPTH',False):
                        if drill_fname:
                            forceren('%s/%s.drl' % (gerber_dir, board_basename), drill_fname)
                            zipfiles.append(drill_fname)
                        if drill_map_fname:
                            forceren('%s/%s-drl_map.%s' % (gerber_dir, board_basename, map_ext), drill_map_fname)
                            zipfiles.append(drill_map_fname)
                    else:
                        if drill_fname:
                            forceren('%s/%s-PTH.drl' % (gerber_dir, board_basename), drill_fname)
                            zipfiles.append(drill_fname)
                        if drill_map_fname:
                            forceren('%s/%s-PTH-drl_map.%s' % (gerber_dir, board_basename, map_ext), drill_map_fname)
                            zipfiles.append(drill_map_fname)
                        if npth_fname:
                            forceren('%s/%s-NPTH.drl' % (gerber_dir, board_basename), npth_fname)
                            zipfiles.append(npth_fname)
                        if npth_map_fname:
                            forceren('%s/%s-NPTH-drl_map.gbr' % (gerber_dir, board_basename), npth_map_fname)
                            zipfiles.append(npth_map_fname)
                    if drill_report_fname:
                        ew.GenDrillReportFile(drill_report_fname)
                        zipfiles.append(drill_report_fname)

                # OptionalFile
                    message('optional')
                    files = self.settings.get('OptionalFiles',[])
                    for n in range(len(files)):
                        if(len(files[n]['name'])):
                            optional_fname = '%s/%s' % (gerber_dir, files[n]['name'])
                            optional_content = files[n]['content']
                            optional_content = optional_content.replace('${basename}',board_basename)
                            for i in range(len(layer_list)):
                                kpath = '${filepath('+layer_list[i]['name']+')}'
                                kname = '${filename('+layer_list[i]['name']+')}'
                                path = layer_list[i]['fname']
                                name = os.path.basename(path)
                                optional_content = optional_content.replace(kname,name)
                            if optional_fname:
                                with codecs.open(optional_fname, 'w', 'utf-8') as f:
                                    f.write(optional_content)
                            zipfiles.append(optional_fname)

                # ZIP
                    message('Zip')
                    with zipfile.ZipFile(zip_fname,'w',compression=zipfile.ZIP_DEFLATED) as f:
                        for i in range(len(zipfiles)):
                            fnam = zipfiles[i]
                            if os.path.exists(fnam):
                                f.write(fnam, os.path.basename(fnam))
                    alert(getstr('COMPLETE') % zip_fname, wx.ICON_INFORMATION)
                except Exception:
                    s=traceback.format_exc(chain=False)
                    print(s)
                    alert(s, wx.ICON_ERROR)
                e.Skip()
        dialog = Dialog(None)
        dialog.Center()
        dialog.ShowModal()
        dialog.Destroy()
