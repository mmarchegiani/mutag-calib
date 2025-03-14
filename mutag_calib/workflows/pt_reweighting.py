import os
from collections import defaultdict

import awkward as ak
import numpy as np
import hist
from coffea.util import save, load

import correctionlib, rich
import correctionlib.convert

from pocket_coffea.utils.configurator import Configurator
from pocket_coffea.lib.categorization import StandardSelection
from mutag_calib.lib.sv import *
from mutag_calib.configs.fatjet_base.custom.cuts import get_ptmsd, mutag_fatjet_sel, mutag_subjet_sel
from mutag_calib.workflows.fatjet_base import fatjetBaseProcessor


class ptReweightProcessor(fatjetBaseProcessor):
    def __init__(self, cfg: Configurator):
        super().__init__(cfg)
        self.pt_eta_2d_maps = [
            'FatJetGood_pt_eta',
            #'FatJetGoodNMuon1_pt_eta',
            #'FatJetGoodNMuon2_pt_eta',
            #'FatJetGoodNMuonSJ1_pt_eta',
            #'FatJetGoodNMuonSJUnique1_pt_eta',
        ]
        self.pt_eta_tau21_3d_maps = [
            'FatJetGood_pt_eta_tau21', 'FatJetGood_pt_eta_tau21_bintau05',
            #'FatJetGoodNMuon1_pt_eta_tau21', 'FatJetGoodNMuon1_pt_eta_tau21_bintau05',
            #'FatJetGoodNMuon2_pt_eta_tau21', 'FatJetGoodNMuon2_pt_eta_tau21_bintau05',
            #'FatJetGoodNMuonSJ1_pt_eta_tau21', 'FatJetGoodNMuonSJ1_pt_eta_tau21_bintau05',
            #'FatJetGoodNMuonSJUnique1_pt_eta_tau21', 'FatJetGoodNMuonSJUnique1_pt_eta_tau21_bintau05',
        ]
        for histname in self.pt_eta_2d_maps + self.pt_eta_tau21_3d_maps:
            if not histname in self.cfg.variables.keys():
                raise Exception(f"'{histname}' is not present in the histogram keys.")

    def load_metadata_extra(self):
        super().load_metadata_extra()
        if self._isMC:
            expected_shape_variations = {"JES_Total_AK8PFPuppi", "JER_AK8PFPuppi"}
            for sample, variations in self.cfg.available_shape_variations.items():
                if not self.cfg.samples_metadata[sample]['isMC']: continue
                if not (set(variations) == expected_shape_variations):
                    missing_shape_variations = {var for var in expected_shape_variations if not var in variations}
                    raise Exception(f"Incorrect configuration of the shape variations. Missing: {missing_shape_variations}")

    def apply_object_preselection(self, variation):
        super().apply_object_preselection(variation)

        pt_min = 350.
        msd = 40.
        cuts_fatjet = {"pt350msd40" : [get_ptmsd(pt_min, msd)]}
        selection_fatjet = StandardSelection(cuts_fatjet)
        selection_fatjet.prepare(
            events=self.events,
            processor_params=self.params
        )
        mask_fatjet = selection_fatjet.get_mask("pt350msd40")

        # Apply (pt, msd) cuts
        self.events["FatJetGood"] = self.events.FatJetGood[mask_fatjet]

        # Restrict analysis to leading and subleading jets only
        self.events["FatJetGood"] = self.events.FatJetGood[ak.local_index(self.events.FatJetGood, axis=1) < 2]

        # Label leading and subleading AK8 jets BEFORE muon tagging selection
        # Leading: pos=0, Subleading: pos=1
        self.events["FatJetGood"] = ak.with_field(self.events["FatJetGood"], ak.local_index(self.events["FatJetGood"], axis=1), "pos")

        # Build 4 distinct AK8 jet collections with 4 different muon tagging scenarios
        cuts_mutag = {
            "FatJetGoodNMuon1" : [get_ptmsd(pt_min, msd), mutag_fatjet_sel(nmu=self.params.object_preselection["FatJet"]["nmu"])],
            #"FatJetGoodNMuon2" : [get_ptmsd(pt_min, msd), mutag_fatjet_sel(nmu=2)],
            #"FatJetGoodNMuonSJ1" : [get_ptmsd(pt_min, msd), mutag_subjet_sel(unique_matching=False)],
            #"FatJetGoodNMuonSJUnique1" : [get_ptmsd(pt_min, msd), mutag_subjet_sel(unique_matching=True)],
        }
        selection_mutag = StandardSelection(cuts_mutag)
        selection_mutag.prepare(
            events=self.events,
            processor_params=self.params
        )
        self.events["FatJetGood"] = self.events.FatJetGood[selection_mutag.get_mask("FatJetGoodNMuon1")]
        #self._ak8jet_collections = list(cuts_mutag.keys())
        #for coll in self._ak8jet_collections:
        #    mask_mutag = selection_mutag.get_mask(coll)

        #    # Apply muon tagging to AK8 jet collection
        #    self.events[coll] = self.events.FatJetGood[mask_mutag]

    def define_common_variables_after_presel(self, variation):

        for coll in ["FatJetGood"]:

            Xbb = self.events[coll].particleNetMD_Xbb
            Xcc = self.events[coll].particleNetMD_Xcc
            QCD = self.events[coll].particleNetMD_QCD
            fatjet_fields = {
                "particleNetMD_Xbb_QCD" : Xbb / (Xbb + QCD),
                "particleNetMD_Xcc_QCD" : Xcc / (Xcc + QCD),
            }

            for field, value in fatjet_fields.items():
                self.events[coll] = ak.with_field(self.events[coll], value, field)
