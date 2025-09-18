import awkward as ak
import numpy as np
import os

import correctionlib

#from mutag_calib.configs.fatjet_base.custom.parameters.pt_reweighting.pt_reweighting import pt_corrections, pteta_corrections

def pt_reweighting(events, year):
    '''Reweighting scale factor based on the leading fatjet pT'''
    cat = 'pt350msd40'
    cset = correctionlib.CorrectionSet.from_file(pt_corrections[year])
    pt_corr = cset[f'pt_corr_{year}']

    '''In case the jet pt is higher than 1500 GeV, the pt is padded to 0
    and a correction SF of 1 is returned.'''
    pt = events.FatJetGood.pt[:,0]
    pt = ak.where(pt < 1500, pt, 0)

    return pt_corr.evaluate(cat, pt)

def pteta_reweighting(events, year):
    '''Reweighting scale factor based on the leading fatjet pT'''
    cat = 'pt350msd40'
    cset = correctionlib.CorrectionSet.from_file(pteta_corrections[year])
    pteta_corr = cset[f'pt_eta_2D_corr_{year}']

    '''In case the jet pt is higher than 1500 GeV, the pt is padded to 0
    and a correction SF of 1 is returned.'''
    pt  = events.FatJetGood.pt[:,0]
    eta = events.FatJetGood.eta[:,0]
    pt = ak.where(pt < 1500, pt, 0)

    return pteta_corr.evaluate(cat, pt, eta)

def sf_trigger_prescale(events, year, isMC, params):
    '''Trigger prescale factor extracted from the JSON files dumped by the script `dump_prescale.py`
    taken from the BTVNanoCommissioning repository.'''

    if isMC:
        raise Exception("Prescale weights are applicable only to data.")

    trigbools = {
        "BTagMu_AK8DiJet170_Mu5": events.HLT["BTagMu_AK8DiJet170_Mu5"],
        "BTagMu_AK8Jet300_Mu5": events.HLT["BTagMu_AK8Jet300_Mu5"],
        "BTagMu_AK8Jet170_DoubleMu5": events.HLT["BTagMu_AK8Jet170_DoubleMu5"],
        "BTagMu_AK4Jet300_Mu5": events.HLT["BTagMu_AK4Jet300_Mu5"]
    }

    psweight = ak.ones_like(events.event, dtype=np.float32)

    for trigger, trigbool in trigbools.items():
        psfile = params["HLT_triggers_prescales"][year]["BTagMu"][trigger]
        if not os.path.isfile(psfile):
            raise NotImplementedError(
                f"Prescale weights not available for {trigger} in {year}. Please run `scripts/dump_prescale.py`."
            )
        pseval = correctionlib.CorrectionSet.from_file(psfile)
        thispsweight = pseval["prescaleWeight"].evaluate(
            events.run,
            f"HLT_{trigger}",
            ak.values_astype(events.luminosityBlock, np.float32),
        )
        psweight = ak.where(trigbool, thispsweight, psweight)

    return psweight

def sf_ptetatau21_reweighting(events, year, params):
    '''Correction of jets observable by a 3D reweighting based on (pT, eta, tau21).
    The function returns the nominal, up and down weights, where the up/down variations are computed considering the statistical uncertainty on data and MC.'''


    cset = correctionlib.CorrectionSet.from_file(params["ptetatau21_reweighting"][year])
    key = list(cset.keys())[0]
    corr = cset[key]

    cat = "inclusive"
    nfatjet  = ak.num(events.FatJetGood.pt)
    pos = ak.flatten(ak.local_index(events.FatJetGood.pt))
    pt = ak.flatten(events.FatJetGood.pt)
    eta = ak.flatten(events.FatJetGood.eta)
    tau21 = ak.flatten(events.FatJetGood.tau21)

    weight = {}
    for var in ["nominal", "statUp", "statDown"]:
        w = corr.evaluate(cat, var, pos, pt, eta, tau21)
        weight[var] = ak.unflatten(w, nfatjet)

    return weight["nominal"], weight["statUp"], weight["statDown"]
