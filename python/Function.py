import logging
import sys
import ROOT
import argparse
import os
import pprint
import math
import ctypes
from tqdm import tqdm
import Utils
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def FillHist(Process_Dict, Selection_Dict, WeightFormula, Hist_Dict, OutputDir):
    Status = True  # return true/false if function works well/bad
    for process in Process_Dict:
        # Create output file!
        if not os.path.exists(OutputDir):
            logger.warning("output path did not exist! Will create one!")
            os.makedirs(OutputDir)
        tag = sys._getframe().f_code.co_name
        OutFile = ROOT.TFile(
            "{0}/{1}_{2}_Hist.root".format(OutputDir, process, tag), "RECREATE")
        logger.info('>>> ... Creating ROOT file {0} ... <<<'.format(
            OutFile.GetName()))

        process_status = False
        Variable_List = {}
        Special_Cut = {}
        # Start to open files & find vars
        FileList = Process_Dict[process]['FileList']
        TreeList = Process_Dict[process]['TreeList']
        for Tree in TreeList:
            Chain = ROOT.TChain(Tree)
            for file in FileList:
                Chain.Add(file)
            for Branch in Chain.GetListOfBranches():
                # Each varialb initialed with nan value
                Variable_List[Branch.GetName()] = []

            for cut in Selection_Dict.keys():  # Check if there is any special/wrong cuts
                if cut not in Variable_List:
                    Special_Cut[cut] = Selection_Dict[cut]
                    del Selection_Dict[cut]

            for var in Hist_Dict.keys():
                if var not in Variable_List:
                    logger.warning("{0} is not a normal variable, got formula {1}".format(
                        var, Hist_Dict[var]["type"][1].replace("formula=", "")))

            logger.info('>>> ... Excuting {0}/{1} events ... <<<'.format(process, Tree))
            # Start to excute events
            # range in 0 -> len()-1
            for event in tqdm(range(Chain.GetEntries()), desc="Processing {0}...".format(process)):
                Chain.GetEntry(event)
                WantedEvent = True
                for Branch in Chain.GetListOfBranches():
                    if not WantedEvent:
                        continue
                    # clear up varialbe list for each new event
                    Variable_List[Branch.GetName()] = []
                    # Just in case there is a vector stored in branches
                    for itr in range(Branch.GetLeaf(Branch.GetName()).GetLen()):
                        Variable_List[Branch.GetName()].append(
                            Branch.GetLeaf(Branch.GetName()).GetValue(itr))

                    # Apply cuts on event:
                    if Branch.GetName() in Selection_Dict:
                        PassCut = Utils.ApplyCut(
                            Variable_List[Branch.GetName()], Selection_Dict[Branch.GetName()])
                        if not PassCut:
                            WantedEvent = False
                            logger.debug('Dumping event {0}: not pass {1}! need {2}{3}, got {4}'.format(event, Branch.GetName(), Selection_Dict[Branch.GetName(
                            )]['logic'], Selection_Dict[Branch.GetName()]['value'], Variable_List[Branch.GetName()][0]))  # For now it can't handle well with vector variables

                # Some special treatment at event level e.g: Event weight calculation or other event level selection:
                if PassCut:
                    EventWeight = Utils.EventLevelCalculator(
                        Variable_List, WeightFormula)[0]

                    if len(Special_Cut) > 0:
                        for cut in Special_Cut.keys():
                            PassCut = Utils.ApplySpecialCut(
                                Variable_List, Special_Cut[cut]) 
                        if not PassCut:
                            WantedEvent = False
                            logger.debug('Dumping event {0}: not pass {1}! need {2}{3}.'.format(event, cut, Special_Cut[cut]['logic'], Special_Cut[cut]['value']))

                # Start to fill the event
                if WantedEvent:
                    for var in Hist_Dict.keys():
                        if Hist_Dict[var]["type"][1] == 'flat':
                            Hist_Dict[var]['HIST'].Fill(
                                Variable_List[var][0], EventWeight)
                        elif "formula=" in Hist_Dict[var]["type"][1]:
                            NewValue = Utils.EventLevelCalculator(
                                Variable_List, Hist_Dict[var]["type"][1].replace("formula=", ""))
                            Hist_Dict[var]['HIST'].Fill(
                                NewValue[0], EventWeight)

            logger.info(">>> ... Writting hists into {0} ... <<<".format(
                OutFile.GetName()))
            OutFile.cd()
            for var in Hist_Dict.keys():
                Hist_Dict[var]['HIST'].Write()
        OutFile.Close()
        process_status = True
        if not process_status:
            Status = False
    return Status
