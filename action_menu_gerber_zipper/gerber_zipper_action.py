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

gerber_subdir = "Gerber"
merge_npth = False
use_aux_origin = True
zip_fname = ""
instruction_fname = ""

strtab = {
    'default':{
        'LABEL':'Make Gerber-files and ZIP for specific PCB manufacturers.',
        'MENUFACTURERS':'Manufacturers',
        'URL':'URL',
        'GERBERDIR':'Gerber Dir',
        'DESCRIPTION':'Description',
        'EXEC':'Make Gerber and ZIP',
        'DETAIL':'Show Settings Details',
        'CLOSE':'Close',
        'DESC2':'The changes here are temporary. If you want to change it permanently edit the corresponding json file',
        'COMPLETE':'GerberZipper Complete. \n\n Output file : %s'
    },
    'ja_JP':{
        'LABEL':u'選択した基板メーカー向けのガーバーを作成し ZIP ファイルにまとめます。',
        'MENUFACTURERS':u'基板メーカー',
        'URL':'URL',
        'GERBERDIR':u'ガーバーディレクトリ',
        'DESCRIPTION':u'説明',
        'EXEC':u'ガーバーとZIPファイルの作成',
        'DETAIL':u'設定の詳細を表示',
        'CLOSE':u'閉じる',
        'DESC2':u'ここでの変更は一時的なものです。恒久的に変更したい場合は対応するjsonファイルを編集してください。',
        'COMPLETE':u'GerberZipper 完了。 \n\n 出力ファイル : %s'
    },
}

layer_list = [
    {'name':'F.Cu', 'id':pcbnew.F_Cu},
    {'name':'B.Cu', 'id':pcbnew.B_Cu},
    {'name':'F.Adhes', 'id':pcbnew.F_Adhes},
    {'name':'B.Adhes', 'id':pcbnew.B_Adhes},
    {'name':'F.Paste', 'id':pcbnew.F_Paste},
    {'name':'B.Paste', 'id':pcbnew.B_Paste},
    {'name':'F.SilkS', 'id':pcbnew.F_SilkS},
    {'name':'B.SilkS', 'id':pcbnew.B_SilkS},
    {'name':'F.Mask', 'id':pcbnew.F_Mask},
    {'name':'B.Mask', 'id':pcbnew.B_Mask},
    {'name':'Dwgs.User', 'id':pcbnew.Dwgs_User},
    {'name':'Cmts.User', 'id':pcbnew.Cmts_User},
    {'name':'Eco1.User', 'id':pcbnew.Eco1_User},
    {'name':'Eco2.User', 'id':pcbnew.Eco2_User},
    {'name':'Edge.Cuts', 'id':pcbnew.Edge_Cuts},
    {'name':'F.CrtYd', 'id':pcbnew.F_CrtYd},
    {'name':'B.CrtYd', 'id':pcbnew.B_CrtYd},
    {'name':'F.Fab', 'id':pcbnew.F_Fab},
    {'name':'B.Fab', 'id':pcbnew.B_Fab},
    {'name':'In1.Cu', 'id':pcbnew.In1_Cu},
    {'name':'In2.Cu', 'id':pcbnew.In2_Cu},
    {'name':'In3.Cu', 'id':pcbnew.In3_Cu},
    {'name':'In4.Cu', 'id':pcbnew.In4_Cu},
    {'name':'In5.Cu', 'id':pcbnew.In5_Cu},
    {'name':'In6.Cu', 'id':pcbnew.In6_Cu}
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
  "InstructionFile":""
}

def message(s):
    s
#    alert(s)

def alert(s):
    wx.MessageBox(s, 'Gerber Zipper', wx.OK|wx.ICON_EXCLAMATION)

def getid(s):
    for i in range(len(layer_list)):
        if layer_list[i]['name']==s:
            return layer_list[i]['id']
    return 0

def getstr(s):
    lang = wx.Locale.GetCanonicalName(wx.GetLocale())
    if(lang not in strtab):
        tab =strtab['default']
    else:
        tab =strtab[lang]
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
    filler = pcbnew.ZONE_FILLER(board)
    zones = board.Zones()
    filler.Fill(zones)

class Editor():
    def __init__(self, panel):
        self.panel = panel
        wx.StaticText(self.panel, wx.ID_ANY, getstr('LABEL'), pos=(1020,10))
        wx.StaticBox(self.panel, wx.ID_ANY,'Gerber', pos=(20,220), size=(370,290))
        wx.StaticBox(self.panel, wx.ID_ANY,'Drill', pos=(400,220), size=(220,340))
        wx.StaticBox(self.panel, wx.ID_ANY,'Other', pos=(20,510), size=(370,50))
        wx.StaticText(self.panel, wx.ID_ANY, getstr('DESC2'), pos=(20,570))
#        status=wx.StaticBox(self.panel, wx.ID_ANY, 'Ready', pos=(0,190), size=(300,20))
        self.layer = wx.grid.Grid(self.panel, wx.ID_ANY, size=(180,240), pos=(40,240))
        self.layer.CreateGrid(len(layer_list), 2)
        self.layer.SetColLabelValue(0, 'Layer')
        self.layer.SetColLabelValue(1, 'Filename')
        self.layer.SetRowLabelSize(1)
        self.layer.ShowScrollbars(wx.SHOW_SB_NEVER,wx.SHOW_SB_DEFAULT)
        for i in range(len(layer_list)):
            self.layer.SetCellValue(i, 0, layer_list[i]['name'])
            self.layer.SetReadOnly(i, 0, isReadOnly=True)
        self.opt_PlotBorderAndTitle = wx.CheckBox(self.panel, wx.ID_ANY, 'PlotBorderAndTitle', pos=(230,240))
        self.opt_PlotFootprintValues = wx.CheckBox(self.panel, wx.ID_ANY, 'PlotFootprintValues', pos=(230,260))
        self.opt_PlotFootprintReferences = wx.CheckBox(self.panel, wx.ID_ANY, 'PlotFootprintReferences', pos=(230,280))
        self.opt_ForcePlotInvisible = wx.CheckBox(self.panel, wx.ID_ANY, 'ForcePlotInvisible', pos=(230,300))
        self.opt_ExcludeEdgeLayer = wx.CheckBox(self.panel, wx.ID_ANY, 'ExcludeEdgeLayer', pos=(230,320))
        self.opt_ExcludePadsFromSilk = wx.CheckBox(self.panel, wx.ID_ANY, 'ExcludePadsFromSilk', pos=(230,340))
        self.opt_DoNotTentVias = wx.CheckBox(self.panel, wx.ID_ANY, 'DoNotTentVias', pos=(230,360))
        self.opt_UseAuxOrigin = wx.CheckBox(self.panel, wx.ID_ANY, 'UseAuxOrigin', pos=(230,380))
        self.opt_LineWidthLabel = wx.StaticText(self.panel, wx.ID_ANY, 'LineWidth(mm):', pos=(230,400))
        self.opt_LineWidth = wx.TextCtrl(self.panel, wx.ID_ANY, '', size=(50,18), pos=(230 + 5 + self.opt_LineWidthLabel.GetSize().GetWidth(),400))
        self.opt_SubtractMaskFromSilk = wx.CheckBox(self.panel, wx.ID_ANY, 'SubtractMaskFromSilk', pos=(230, 420))
        self.opt_UseExtendedX2format = wx.CheckBox(self.panel, wx.ID_ANY, 'UseExtendedX2format', pos=(230, 440))
        self.opt_CoodinateFormat46 = wx.CheckBox(self.panel, wx.ID_ANY, 'CoodinateFormat46', pos=(230, 460))
        self.opt_IncludeNetlistInfo = wx.CheckBox(self.panel, wx.ID_ANY, 'IncludeNetlistInfo', pos=(230, 480))

        self.drill = wx.grid.Grid(self.panel, wx.ID_ANY, size=(162,130), pos=(420,240))
        self.drill.CreateGrid(5, 2)
        self.drill.SetColSize(0, 80)
        self.drill.SetColSize(1, 80)
        self.drill.DisableDragGridSize()
        self.drill.ShowScrollbars(wx.SHOW_SB_NEVER,wx.SHOW_SB_NEVER)
        self.drill.SetColLabelValue(0, 'Drill')
        self.drill.SetColLabelValue(1, 'Filename')
        self.drill.SetRowLabelSize(1)
        drillfile = ['Drill', 'DrillMap', 'NPTH', 'NPTHMap', 'Report']
        for i in range(len(drillfile)):
            self.drill.SetCellValue(i, 0, drillfile[i])
            self.drill.SetReadOnly(i, 0, True)
        wx.StaticText(self.panel, wx.ID_ANY, 'Drill Unit :', pos=(420,380))
        self.opt_DrillUnit = wx.ComboBox(self.panel, wx.ID_ANY, '', choices=('inch','mm'), style=wx.CB_READONLY, pos=(490,376), size=(60,20))
        self.opt_MirrorYAxis = wx.CheckBox(self.panel, wx.ID_ANY, 'MirrorYAxis', pos=(420,400))
        self.opt_MinimalHeader = wx.CheckBox(self.panel, wx.ID_ANY, 'MinimalHeader', pos=(420,420))
        self.opt_MergePTHandNPTH = wx.CheckBox(self.panel, wx.ID_ANY, 'MergePTHandNPTH', pos=(420,440))
        self.opt_RouteModeForOvalHoles = wx.CheckBox(self.panel, wx.ID_ANY, 'RouteModeForOvalHoles', pos=(420,460))
        wx.StaticText(self.panel, wx.ID_ANY, 'Zeros :', pos=(420,480))
        self.opt_ZerosFormat = wx.ComboBox(self.panel, wx.ID_ANY, '', choices=('DecimalFormat','SuppressLeading','SuppresTrailing', 'KeepZeros'), pos=(460,480), size=(140,20), style=wx.CB_READONLY)
        wx.StaticText(self.panel, wx.ID_ANY, 'MapFileFormat :', pos=(420,520))
        self.opt_MapFileFormat = wx.ComboBox(self.panel, wx.ID_ANY, '', choices=('HPGL','PostScript','Gerber','DXF','SVG','PDF'), pos=(520,520), size=(80,20), style=wx.CB_READONLY)

        self.opt_InstructionLabel = wx.StaticText(self.panel, wx.ID_ANY, 'InstructionFile:', pos=(40,530))
        self.opt_InstructionFile = wx.TextCtrl(self.panel, wx.ID_ANY, '', size=(120,18), pos=(40 + 5 + self.opt_InstructionLabel.GetSize().GetWidth(),530))

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
        self.opt_InstructionFile.SetValue(self.settings.get('InstructionFile', ''))

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
        self.settings['InstructionFile'] = self.opt_InstructionFile.GetValue()
        return self.settings

class GerberZipperAction( pcbnew.ActionPlugin ):
    def defaults( self ):
        self.name = "Gerber Zipper"
        self.category = "Plot"
        self.description = "Make Gerber-Zip-file for selected PCB manufacturers"
        self.icon_file_name = os.path.join(os.path.dirname(__file__), 'icon.png')

    def Run(self):
        class Dialog(wx.Dialog):
            def __init__(self, parent):
                self.icon_file_name = os.path.join(os.path.dirname(__file__), 'icon.png')
                self.manufacturers_dir = os.path.join(os.path.dirname(__file__), 'Manufacturers')
                manufacturers_list = glob.glob('%s/*.json' % self.manufacturers_dir)
                self.json_data = []
                for fname in manufacturers_list:
                    try:
                        self.json_data.append(json.load(open(fname),'utf-8'))
                    except Exception as err:
                        alert('JSON error \n\n File : %s\n%s' % (os.path.basename(fname), err.message))
                self.json_data = sorted(self.json_data, key=lambda x: x['Name'])
                wx.Dialog.__init__(self, parent, id=-1, title='Gerber-Zipper', size=(650,240))
                self.panel = wx.Panel(self)
                icon=wx.EmptyIcon()
                icon_source=wx.Image(self.icon_file_name,wx.BITMAP_TYPE_PNG)
                icon.CopyFromBitmap(icon_source.ConvertToBitmap())
                self.SetIcon(icon)
                manufacturers_arr=[]
                for item in self.json_data:
                    manufacturers_arr.append(item['Name'])
                wx.StaticText(self.panel, wx.ID_ANY, getstr('LABEL'), pos=(20,10))
                wx.StaticText(self.panel, wx.ID_ANY, 'Manufacturers :', pos=(20,40))
                wx.StaticText(self.panel, wx.ID_ANY, 'URL :', pos=(20,70))
                wx.StaticText(self.panel, wx.ID_ANY, 'Gerber Dir :', pos=(20,95))
                wx.StaticText(self.panel, wx.ID_ANY, 'Zip Filename :', pos=(20,120))
                wx.StaticText(self.panel, wx.ID_ANY, 'Description :', pos=(20,150))
                wx.StaticLine(self.panel, wx.ID_ANY, pos=(20,215),size=(600,2))
                self.manufacturers = wx.ComboBox(self.panel, wx.ID_ANY, 'Select Manufacturers', choices=manufacturers_arr, style=wx.CB_READONLY, size=(200,24), pos=(120,40))
                self.url = wx.TextCtrl(self.panel, wx.ID_ANY, '', size=(270,20), pos=(120,70), style=wx.TE_READONLY)
                self.gerberdir = wx.TextCtrl(self.panel, wx.ID_ANY, '', size=(270,20), pos=(120,95))
                self.zipfilename = wx.TextCtrl(self.panel, wx.ID_ANY, '', size=(270,20), pos=(120,120))
                self.label = wx.StaticText(self.panel, wx.ID_ANY, '', size=(300,20), pos=(120,150))
                self.manufacturers.SetSelection(0)
                self.execbtn = wx.Button(self.panel, wx.ID_ANY, getstr('EXEC'), pos=(170,175))
                self.clsbtn = wx.Button(self.panel, wx.ID_ANY, getstr('CLOSE'), pos=(340,175))
                self.detailbtn = wx.ToggleButton(self.panel, wx.ID_ANY, getstr('DETAIL'), pos=(20,175))
                self.manufacturers.Bind(wx.EVT_COMBOBOX, self.OnManufacturers)
                self.clsbtn.Bind(wx.EVT_BUTTON, self.OnClose)
                self.execbtn.Bind(wx.EVT_BUTTON, self.OnExec)
                self.detailbtn.Bind(wx.EVT_TOGGLEBUTTON, self.OnDetail)
                self.editor = Editor(self.panel)
                self.Select(0)

            def Select(self,n):
                self.settings = self.json_data[n]
                self.label.SetLabel(self.settings.get('Description', ''))
                self.url.SetLabel(self.settings.get('URL',''))
                self.gerberdir.SetValue(self.settings.get('GerberDir','Gerber'))
                self.zipfilename.SetValue(self.settings.get('ZipFilename','*.ZIP'))
                self.editor.Set(self.settings)

            def OnManufacturers(self,e):
                obj = e.GetEventObject()
                self.Select(obj.GetSelection())
                e.Skip()

            def OnDetail(self,e):
                if self.detailbtn.GetValue():
                    self.SetSize(wx.Size(650,630))
                else:
                    self.SetSize(wx.Size(650,240))
                e.Skip()

            def OnClose(self,e):
                e.Skip()
                self.Close()

            def OnDump(self,e):
                s = json.dumps(self.editor.Get())
                wx.MessageBox(s, 'Gerber Zipper', wx.OK|wx.ICON_INFORMATION)
                e.Skip()

            def OnExec(self,e):
                try:
                    self.settings = self.editor.Get()
                    global zip_fname
                    board = pcbnew.GetBoard()
                    board_fname = board.GetFileName()
                    board_dir = os.path.dirname(board_fname)
                    board_basename = (os.path.splitext(os.path.basename(board_fname)))[0]
                    gerber_dir = '%s/%s' % (board_dir, self.gerberdir.GetValue())
                    zip_fname = '%s/%s' % (gerber_dir, self.zipfilename.GetValue().replace('*',board_basename))
                    instruction_fname = self.settings.get('InstructionFile')
                    if len(instruction_fname)>0:
                        instruction_fname = '%s/%s' % (gerber_dir, instruction_fname)
                    if not os.path.exists(gerber_dir):
                        os.mkdir(gerber_dir)
                    refill(board)
                    zipfiles = []
                # PLOT
                    message('PlotStart')
                    pc = pcbnew.PLOT_CONTROLLER(board)
                    po = pc.GetPlotOptions()

#                    s = {}
#                    for k in inspect.getmembers(po, inspect.ismethod):
#                        s[k[0]]='method'
                    s = self.settings
                    message(json.dumps(s,sort_keys=True,indent=4))

                    po.SetOutputDirectory(gerber_dir)
                    po.SetPlotFrameRef( self.settings.get('PlotBorderAndTitle',False))
                    po.SetPlotValue( self.settings.get('PlotFootprintValues',True))
                    po.SetPlotReference( self.settings.get('PlotFootprintReferences',True))
                    po.SetPlotInvisibleText( self.settings.get('ForcePlotInvisible',False))
                    po.SetExcludeEdgeLayer( self.settings.get('ExcludeEdgeLayer',True))
                    po.SetPlotPadsOnSilkLayer( not self.settings.get('ExcludePadsFromSilk',False))
                    po.SetPlotViaOnMaskLayer( self.settings.get('DoNotTentVias',False))
                    po.SetUseAuxOrigin(self.settings.get('UseAuxOrigin',False))
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
                        offset = board.GetAuxOrigin()
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
                # InstructionFile
                    message('Instruction')
                    if instruction_fname:
                        with codecs.open(instruction_fname, 'w', 'utf-8') as f:
                            for k in layer:
                                fnam = layer[k]
                                id = getid(k)
                                if len(fnam)>0 and board.IsLayerEnabled(id):
                                    fnam = fnam.replace('*',board_basename)
                                    f.write(fnam)
                                    if id==pcbnew.F_Cu:
                                        f.write(u' (部品面パターン)\n')
                                    elif id==pcbnew.B_Cu:
                                        f.write(u' (半田面パターン)\n')
                                    elif id==pcbnew.F_SilkS:
                                        f.write(u' (部品面シルク)\n')
                                    elif id==pcbnew.B_SilkS:
                                        f.write(u' (半田面シルク)\n')
                                    elif id==pcbnew.F_Mask:
                                        f.write(u' (部品面レジスト)\n')
                                    elif id==pcbnew.B_Mask:
                                        f.write(u' (半田面レジスト)\n')
                                    elif id==pcbnew.In1_Cu:
                                        f.write(u' (内層パターン 2)\n')
                                    elif id==pcbnew.In2_Cu:
                                        f.write(u' (内層パターン 3)\n')
                                    elif id==pcbnew.In3_Cu:
                                        f.write(u' (内層パターン 4)\n')
                                    elif id==pcbnew.In4_Cu:
                                        f.write(u' (内層パターン 5)\n')
                                    elif id==pcbnew.In5_Cu:
                                        f.write(u' (内層パターン 6)\n')
                                    elif id==pcbnew.In6_Cu:
                                        f.write(u' (内層パターン 7)\n')
                                    elif id==pcbnew.Edge_Cuts:
                                        f.write(u' (基板外形)\n')
                            if drill_fname:
                                f.write(u'\x0D\x0A')
                                f.write(os.path.basename(drill_fname))
                                f.write(u' (ドリルデータ)\n')
                            if drill_map_fname:
                                f.write(os.path.basename(drill_map_fname))
                                f.write(u' (ドリルマップ)\n')
                            if drill_report_fname:
                                f.write(os.path.basename(drill_report_fname))
                                f.write(u' (ドリルリスト)\n')
                        zipfiles.append(instruction_fname)

                # ZIP
                    message('Zip')
                    with zipfile.ZipFile(zip_fname,'w') as f:
                        for i in range(len(zipfiles)):
                            fnam = zipfiles[i]
                            if os.path.exists(fnam):
                                f.write(fnam, os.path.basename(fnam))
                            f.write(fnam, os.path.basename(fnam))
                    wx.MessageBox(getstr('COMPLETE') % zip_fname, 'Gerber Zipper', wx.OK|wx.ICON_INFORMATION)
                except Exception as err:
                    alert(err.message)
                e.Skip()
        dialog = Dialog(None)
        dialog.Center()
        dialog.ShowModal()
        dialog.Destroy()
