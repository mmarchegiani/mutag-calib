import numpy as np

def lepton_selection_noniso(events, Lepton, params):

    leptons = events[Lepton]
    cuts = params.object_preselection[Lepton]
    # Requirements on pT and eta
    passes_eta = (np.abs(leptons.eta) < cuts["eta"])
    passes_pt = (leptons.pt > cuts["pt"])

    if Lepton == "Electron":
        # Requirements on SuperCluster eta, isolation and id
        etaSC = np.abs(leptons.deltaEtaSC + leptons.eta)
        passes_SC = np.invert((etaSC >= 1.4442) & (etaSC <= 1.5660))
        passes_iso = leptons.pfRelIso03_all < cuts["iso"]
        passes_id = (leptons[cuts['id']] == True)

        good_leptons = passes_eta & passes_pt & passes_SC & passes_iso & passes_id

    elif Lepton == "Muon":
        # Requirements on isolation and id
        # N.B.: INVERTED ISOLATION REQUIREMENT FOR MUON TAGGING !!!
        passes_iso = leptons.pfRelIso04_all > cuts["iso"]
        passes_id = (leptons[cuts['id']] == True)

        good_leptons = passes_eta & passes_pt & passes_iso & passes_id

    return leptons[good_leptons]