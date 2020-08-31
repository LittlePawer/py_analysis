import logging
import sys
import ROOT
import argparse
import os
import pprint
import math
import ctypes
import json
import copy
from tqdm import tqdm
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def InputClassfier(InputDir, FileStructure, RequiredProcess):
    if not os.path.exists(InputDir):
        logger.error('The input dir is not exists! Abort!')
        sys.exit()

    Dict = {}
    for filename in os.listdir(InputDir):
        if FileStructure == 'ProcessAsFile':
            logger.error('This block is still under developement! Abort!')
            sys.exit()
        elif FileStructure == 'ProcessInFile':
            file = ROOT.TFile.Open(InputDir + '/' + filename)
            if not file.IsOpen():
                logger.error('bkg root file is not open properly! Abort!')
                sys.exit()
            TreeName = [key.GetName() for key in file.GetListOfKeys() if key.GetClassName() == 'TTree' ]

            tmp = [(x, y) for x in RequiredProcess.keys() for y in TreeName]
            mask_tmp = [x in y for (x,y) in tmp]
            mask_index = [i for i, val in enumerate(mask_tmp) if val]
            Needed = [tmp[i][1] for i in mask_index]

            if len(mask_index) != len(RequiredProcess.keys()):
                logger.error(
                    "There is an error in matching the needed process and the available processes! Abort!")
                sys.exit()

            for Tree in Needed:
                Dict[Tree] = {'FileList': [
                    InputDir+'/'+filename], 'TreeList': [Tree]}
            file.Close()
        elif FileStructure == 'DSIDInFile':
            file = ROOT.TFile.Open(InputDir + '/' + filename)
            if not file.IsOpen():
                logger.error('bkg root file is not open properly! Abort!')
                sys.exit()
            for Pro in RequiredProcess.keys():
                Dict[Pro] = {'FileList': [
                    InputDir+'/'+filename], 'TreeList': []}
                
                TreeName = [key.GetName() for key in file.GetListOfKeys() if key.GetClassName() == 'TTree' ]

                tmp = [(x['DSID'], y) for x in RequiredProcess[Pro] for y in TreeName]
                mask_tmp = [x in y for (x,y) in tmp]
                mask_index = [i for i, val in enumerate(mask_tmp) if val]
                Needed = [tmp[i][1] for i in mask_index]

                if len(mask_index) != len(RequiredProcess[Pro]):
                    logger.error(
                    "There is an error in matching the needed process and the available processes! Abort!")
                    sys.exit()

                Dict[Pro]["TreeList"] = Needed
            file.Close()

    return Dict


def CutRegistrate(Config):
    Selection_Dict = LoadJsonConfig(Config)
    return Selection_Dict


def EventLevelCalculator(Vars, formula):
    cp_Vars = copy.deepcopy(Vars)
    OutValue = [float("nan")]
    for var in Vars.keys():
        if var in formula:
            tmp = var
            exec("%s = %d" % (tmp, cp_Vars[var][0]))
    OutValue[0] = eval(formula)
    return OutValue


def ApplySpecialCut(Vars, Cut):
    PassCut = False
    UsedVars = []
    if "formula" not in Cut["type"]:
        logger.error("Wrong type of cut take as special cut! Abort!")
        sys.exit()

    OutValue = EventLevelCalculator(Vars, Cut["type"].replace("formula=", ""))
    PassCut = ApplyCut(OutValue, Cut)
    return PassCut


def ApplyCut(Var, Cut):
    PassCut = False
    if len(Var) > 1:
        logger.error(
            "Can't handle well for the vector like variables for now! Abort!")
        sys.exit()

    if Cut['logic'] == '>':
        if float(Var[0]) > float(Cut['value']):
            PassCut = True
    elif Cut['logic'] == '<':
        if float(Var[0]) < float(Cut['value']):
            PassCut = True
    elif Cut['logic'] == '==':
        if float(Var[0]) == float(Cut['value']):
            PassCut = True
    elif Cut['logic'] == 'bool':
        if Cut['value'] == 'True':
            if Var[0]:
                PassCut = True
        if Cut['value'] == 'False':
            if not Var[0]:
                PassCut = True
    else:
        logger.error('It is not a proper logic for the cut! Abort!')
        sys.exit()
    return PassCut


def RegistrateHist(Config):
    Hist_Dict = LoadJsonConfig(Config)
    for name in Hist_Dict.keys():
        if Hist_Dict[name]['type'][0] == "TH1F":
            hist = ROOT.TH1F(name, Hist_Dict[name]["title"], Hist_Dict[name]["x-axis"]
                             [0], Hist_Dict[name]["x-axis"][1], Hist_Dict[name]["x-axis"][2])
            Hist_Dict[name]['HIST'] = hist
        elif Hist_Dict[name]['type'][0] == "TH2F":
            hist = ROOT.TH2F(name, Hist_Dict[name]["title"], Hist_Dict[name]["x-axis"][0], Hist_Dict[name]["x-axis"][1], Hist_Dict[name]
                             ["x-axis"][2], Hist_Dict[name]["y-axis"][0], Hist_Dict[name]["y-axis"][1], Hist_Dict[name]["y-axis"][2])
            Hist_Dict[name]['HIST'] = hist
        else:
            logger.error("Can't handle hist type {0}! Abort!".format(
                Hist_Dict[name]['type']))
            sys.exit()
    return Hist_Dict


def ProcessRegistrate(Config, SUSYDir, BKGDir):
    Process_List = LoadJsonConfig(Config)
    if not os.path.exists(SUSYDir):
        logger.error('SUSYDir is not exist! Abort!')
        sys.exit()
    if not os.path.exists(BKGDir):
        logger.warning('BKGDir is not exist! Please double check!')
    for sig in Process_List["sig"]:
        if not sig+".txt" in os.listdir(SUSYDir):
            logger.error(
                'You required a signal process which got no information in SUSYDir {0}! Abort!'.format(SUSYDir))
            sys.exit()
        file = open(SUSYDir+"/"+sig+".txt")
        for line in file.readlines():
            DSID = line.split(":")[1].split(".")[1]
            SP = line.split(":")[1].split(".")[2].split("_")[4]
            LSP = line.split(":")[1].split(".")[2].split("_")[5]
            if 'p0' in SP:
                SP = SP.replace("p0", "")
            if 'p0' in LSP:
                LSP = LSP.replace("p0", "")
            Process_List["sig"][sig].append(
                {"DSID": DSID, "SPmass": SP, "LSPmass": LSP})

    return Process_List


def LoadJsonConfig(Config):
    Dict = {}
    if not os.path.exists(Config):
        logger.error('Hist config file is not exist! Abort!')
        sys.exit()
    json_file = open(Config)
    Dict = json.load(json_file)
    return Dict
