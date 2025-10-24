from mutag_calib.workflows.mutag_processor import mutagAnalysisProcessor
from pocket_coffea.lib.categorization import StandardSelection
from mutag_calib.lib.sv import *
from mutag_calib.configs.fatjet_base.custom.cuts import mutag_fatjet_sel


class mutagAnalysisOneMuonInAK8Processor(mutagAnalysisProcessor):

    def apply_object_preselection(self, variation):
        super().apply_object_preselection(variation)

        mask_name = "FatJetGoodNMuon1"
        cuts_mutag = {
            mask_name : [mutag_fatjet_sel(nmu=self.params.object_preselection["FatJet"]["nmu"])],
        }
        selection_mutag = StandardSelection(cuts_mutag)
        selection_mutag.prepare(
            events=self.events,
            processor_params=self.params,
            year=self._year,
            sample=self._sample,
            isMC=self._isMC,
        )
        mask_mutag = selection_mutag.get_mask(mask_name)

        # Apply muon tagging asking for at least one muon inside the AK8 jet
        self.events["FatJetGood"] = self.events.FatJetGood[mask_mutag]

    def fill_column_accumulators(self, variation):
        pass
