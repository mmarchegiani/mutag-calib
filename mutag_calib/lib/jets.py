import copy
import importlib
import gzip
import cloudpickle

import awkward as ak
import numpy as np
import correctionlib

from pocket_coffea.parameters.object_preselection import object_preselection
from pocket_coffea.parameters.jec_config import JECjsonFiles

def jet_mutag_selection(events, Jet, finalstate):

    jets = events[Jet]
    cuts = object_preselection[finalstate][Jet]

    if Jet == "FatJet":
        njet_max = ak.max(ak.count(jets.pt, axis=1))
        # Select jets with a minimum number of subjets
        mask_nsubjet = (ak.count(jets.subjets.pt, axis=2) >= cuts["nsubjet"])
        # Select jets with a minimum number of mu-tagged subjets
        mask_nmusj = (nmusj >= cuts["nmusj"])
        # Apply di-muon pT ratio cut on FatJets
        mask_ptratio = (events.dimuon.pt / events.FatJet.pt < cuts["dimuon_pt_ratio"])
        mask_ptratio = ak.where( ak.is_none(mask_ptratio), ak.zeros_like(events.FatJet.pt, dtype=bool), mask_ptratio )
        for mask in [mask_nsubjet, mask_nmusj, mask_ptratio]:
            mask_good_jets = mask_good_jets & ak.pad_none(mask, njet_max)
        mask_good_jets = mask[~ak.is_none(mask, axis=1)]

    return jets[mask_good_jets], mask_good_jets
