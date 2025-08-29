import awkward as ak

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

def sf_trigger_prescale(events, year, params):
    '''Trigger prescale factor'''
    # Here we assume that both BTagMu_AK4Jet300_Mu5 and BTagMu_AK8Jet170_DoubleMu5 triggers have a prescale of 1
    sf = ak.ones_like(events)
    pass_unprescaled_triggers = events.HLT["BTagMu_AK4Jet300_Mu5"] | events.HLT["BTagMu_AK8Jet170_DoubleMu5"]
    sf = ak.where(events.HLT["BTagMu_AK8Jet300_Mu5"] & (~pass_unprescaled_triggers), 1. / params["HLT_triggers_prescales"][year]["BTagMu"]["BTagMu_AK8Jet300_Mu5"], sf)
    sf = ak.where(events.HLT["BTagMu_AK8DiJet170_Mu5"] & (~events.HLT["BTagMu_AK8Jet300_Mu5"]) & (~pass_unprescaled_triggers), 1. / params["HLT_triggers_prescales"][year]["BTagMu"]["BTagMu_AK8DiJet170_Mu5"], sf)

    return sf

