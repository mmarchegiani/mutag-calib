"""Workaround subclass for PocketCoffea's JetsSoftdropMassCalibrator.

PocketCoffea has a case bug in common.py line 371: it checks for
"2016_preVFP"/"2016_postVFP" (lowercase) but actual year labels are
"2016_PreVFP"/"2016_PostVFP" (mixed case). This causes 2016 to incorrectly
select AK4PFPuppi instead of AK4PFchs for subjet corrections.

This subclass overrides `initialize` with the fixed case check.
Remove this once PocketCoffea is patched upstream.
"""

import copy
from pocket_coffea.lib.calibrators.common.common import JetsSoftdropMassCalibrator
from pocket_coffea.lib.jets import msoftdrop_correction


class FixedJetsSoftdropMassCalibrator(JetsSoftdropMassCalibrator):
    """JetsSoftdropMassCalibrator with fixed 2016 year label case."""

    def initialize(self, events):
        # Copied from PocketCoffea's JetsSoftdropMassCalibrator.initialize
        # with the ONLY change being the case fix on the 2016 year check.

        # Load the calibration of each jet type requested by the parameters
        for jet_type, jet_coll_name in self.jet_calib_param.collection[self.year].items():
            # Calibrate only AK8 jets
            if jet_type in ["AK8PFPuppi"]:
                # Define the subjet type for the correction of subjets
                # FIX: Use correct case "2016_PreVFP"/"2016_PostVFP"
                if self.year in ["2016_PreVFP", "2016_PostVFP", "2017", "2018"]:
                    subjet_type = "AK4PFchs"
                else:
                    subjet_type = "AK4PFPuppi"
            else:
                print("WARNING: JetsSoftdropMassCalibrator only supports AK8PFPuppi jets for softdrop mass calibration." +
                      f" Jet type {jet_type} will be skipped.")
                continue

            # Check if the collection is enables in the parameters
            if self.isMC:
                if (self.jet_calib_param.apply_jec_msoftdrop_MC[self.year][jet_type] == False):
                    # If the collection is not enabled, we skip it
                    continue
            else:
                if self.jet_calib_param.apply_jec_msoftdrop_Data[self.year][jet_type] == False:
                    # If the collection is not enabled, we skip it
                    continue

            # register the collection as calibrated by this calibrator
            self.calibrated_collections.append(jet_coll_name)

            # N.B.: since the correction is applied to the subjets of the AK8 jet, the parameters for AK4 jets are passed
            self.jets_calibrated[jet_coll_name] = msoftdrop_correction(
                calib_params=self.jet_calib_param.jet_types[subjet_type][self._year],
                variations=self.jet_calib_param.variations[subjet_type][self._year],
                events=events,
                subjet_type = subjet_type,   # AK4PFPuppi (approximation: the subjets are corrected with AK4 jet corrections)
                jet_coll_name=jet_coll_name, # AK8PFPuppi
                chunk_metadata={
                    "year": self._year,
                    "isMC": self.metadata["isMC"],
                    "era": self.metadata["era"] if "era" in self.metadata else None,
                },
                jec_syst=self.do_variations
            )
            # Add to the list of the types calibrated
            self.jets_calibrated_types.append(jet_type)

        assert len(self.jets_calibrated_types) > 0, "No jet types were calibrated in JetsSoftdropMassCalibrator. Please check the configuration."

        # Prepare the list of available variations
        # For this we just read from the parameters
        available_jet_variations = []

        # N.B.: JES variations are not yet implemented for msoftdrop
        self._variations = list(sorted(set(available_jet_variations)))  # remove duplicates
