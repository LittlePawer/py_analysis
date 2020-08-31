######################################################################
#
#This is a description block to describe how to use this framework
#
#
#
######################################################################


########################################################################
# Start parameter block
#########################################################################


import logging
import sys
import ROOT
import argparse
import os
import pprint
import math
import ctypes
import Utils
import Function
from tqdm import tqdm

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--InputData', type=str,
                    default='', help='Path for data')
parser.add_argument('-s', '--InputSignal', type=str,
                    default='', help='Path for signal')
parser.add_argument('-b', '--InputBkg', type=str,
                    default='', help='Path for background')
parser.add_argument('-o', '--OutputDir', type=str,
                    default='', help='output dir path')
parser.add_argument('-f', '--Function', type=str, default='pre-selection',
                    help='chose which function you want to use')
parser.add_argument('--DataFS', type=str, help='Data file structure that the input bkg/sig/data got',
                    choices=['ProcessInFile', 'ProcessAsFile', 'DSIDInFile'], default='ProcessAsFile')
parser.add_argument('--SigFS', type=str, help='Signal file structure that the input bkg/sig/data got',
                    choices=['ProcessInFile', 'ProcessAsFile', 'DSIDInFile'], default='DSIDInFile')
parser.add_argument('--BkgFS', type=str, help='Bkg file structure that the input bkg/sig/data got',
                    choices=['ProcessInFile', 'ProcessAsFile', 'DSIDInFile'], default='ProcessInFile')
parser.add_argument('--WeightFormula', type=str,
                    default='totweight*lumiScaling', help='Formula to calculate weight!')
parser.add_argument('--RequiredProcess', action='store_true',
                    help='If there is user required process list!')
parser.add_argument('--Config', type=str, default='../Config/',
                    help='Where the config files stored')
parser.add_argument('--SUSYInfo', type=str, default='../SUSYGrids/',
                    help='Where the SUSY grids information files stored')
parser.add_argument('--BKGInfo', type=str, default='../BKGs/',
                    help='Where the BKG information files stored')
parser.add_argument('--IgnoreData', action='store_true',
                    help='If we should ignore data')
parser.add_argument('--Debug', action='store_true', help='Open the debug mode')
options = parser.parse_args()

if options.Debug:
    logging.basicConfig(
        level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
else:
    logging.basicConfig(
        level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Print out the settings #
logger.info('>>> ... Get input options ... <<<')
for setting in dir(options):
    if not setting[0] == "_":
        logger.info("Setting: {: >20} {: >40}".format(
            setting, eval("options.%s" % setting)))

# Start to registrate user required process list
if options.RequiredProcess:
    Process_List = Utils.ProcessRegistrate(
        options.Config+"ProcessConfig.json", options.SUSYInfo, options.BKGInfo)
else:
    Process_List = {"bkg": {"all": ["all"]}, "sig": {
        "all": ["all"]}, "data": {"all": ["all"]}}

# Read signal/bkg/data into DataType_Dict = {process: {filepath&name: [PATH], TreeList: [TREE]}}
logger.info('>>> ... Get file list & process for bkg/sig/data ... <<<')

if not options.IgnoreData:
    logger.debug('>>> ... Getting Data file list information ... <<<')
    Data_Dict = InputClassfier.InputClassfier(
        options.InputData, options.DataFS, Process_List["data"])
    logger.debug('Data file list information: ')
    logger.debug("\n"+pprint.pformat(Data_Dict))

logger.debug('>>> ... Getting Bkg file list information ... <<<')

Bkg_Dict = Utils.InputClassfier(
    options.InputBkg, options.BkgFS, Process_List["bkg"])

logger.debug('Bkg file list information: ')
logger.debug("\n"+pprint.pformat(Bkg_Dict))

logger.debug('>>> ... Getting Signal file list information ... <<<')

Signal_Dict = Utils.InputClassfier(
    options.InputSignal, options.SigFS, Process_List["sig"])

logger.debug('Signal file list information: ')
logger.debug("\n"+pprint.pformat(Signal_Dict))

# Start to registrate selections
logger.info('>>> ... Start to registrate selections ... <<<')

# {var1: {logic: >/</=/!=/bool, value: VALUE}}
Selection_Dict = Utils.CutRegistrate(options.Config+"CutConfig.json")

logger.debug('Used selection: ')
logger.debug("\n"+pprint.pformat(Selection_Dict))

# Start to dealing with processes
logger.info('>>> ... Start to dealing with processes ... <<<')

if options.Function == 'FillHist':
    Hist_Dict = Utils.RegistrateHist(options.Config+"HistConfig.json")

    logger.info(
        '>>> ... Calling function {0} ... <<<'.format(options.Function))

    FuncStatus = Function.FillHist(
        Signal_Dict, Selection_Dict, options.WeightFormula, Hist_Dict, options.OutputDir)
    if not FuncStatus:
        logger.error('{0} function is not properly excuted for SIG! Abort!'.format(
            options.Function))
        sys.exit()

    FuncStatus = Function.FillHist(
        Bkg_Dict, Selection_Dict, options.WeightFormula, Hist_Dict, options.OutputDir)
    if not FuncStatus:
        logger.error('{0} function is not properly excuted for BKG! Abort!'.format(
            options.Function))
        sys.exit()

    logger.info(">>> ... Successful Run ... <<<")
