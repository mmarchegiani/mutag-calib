import awkward as ak

import correctionlib

from config.fatjet_base.custom.parameters.pt_reweighting.pt_reweighting import pt_corrections, pteta_corrections

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
