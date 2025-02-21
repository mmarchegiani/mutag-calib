# Analysis workflow for calibration of boosted jets with the mu-tagged method
Repository for the calibration of large-radius jets with the mu-tagged method based on the [PocketCoffea](https://pocketcoffea.readthedocs.io/en/latest/index.html) analysis workflow.

## Installation
This package requires PocketCoffea >=0.9.8 as specified in the requirements.
To install the `mutag_calib` package, run the following commands:

```bash
# Clone repository
git clone git@github.com:mmarchegiani/mutag-calib.git
cd mutag-calib
# Install micromamba
"${SHELL}" <(curl -L micro.mamba.pm/install.sh)
micromamba create -n mutag-calib python=3.11 -c conda-forge
micromamba activate mutag-calib
pip install -e .
```

## Datasets definition
The folder `datasets` contains the file `datasets_definitions_RunIISummer20UL.json` which contains the metadata of all the Run 2 datasets used for the calibration.
In order to perform the calibration with Run 3 data, **a new file containing the datasets definition of Run 3 datasets needs to be defined.** For more detailed instructions on how to do it, please follow [this guide](https://pocketcoffea.readthedocs.io/en/latest/datasets.html#datasets-handling)

## Workflows
The folder `workflows` contains different PocketCoffea workflows that are needed to perform the analysis.
Here is their description:

- `pt_reweighting.py`: defines the `ptReweightProcessor` to compute the MC-to-data reweighting based on the 3D map in jet ($p_T$, $\eta$, $\tau_{21}$). It needs to be run once to compute the 3D reweighting map, that is then saved and used as a parameter for the next workflows.
- `fatjet_base.py`: defines the `fatjetBaseProcessor` that applies the custom object preselection needed for the calibration, creates all the branches that are counting the number of muons within the AK8 jet and creates branches specific to the taggers. **For Run 3 analyses, the definition of the tagger branches might have to be redefined here.**
- `mutag_processor.py`: defines the `mutagAnalysisProcessor` on top of `fatjetBaseProcessor`. It applies the $p_T$ and $M_{SD}$ cuts on the AK8 jet collection and applies the 3D reweighting to MC.
- `mutag_oneMuAK8_processor.py`: defines the `mutagAnalysisOneMuonInAK8Processor` on top of `mutagAnalysisProcessor`. It applies the selection on AK8 jets based on the number of soft muons contained in the AK8 jet (>=1 soft muon within the AK8 jet).

## Analysis steps
### Step 1: compute 3D reweighting based on jet $p_T$, $\eta$, $\tau_{21}$
Run jobs on DATA, QCD, V+jets and top datasets:
```bash
pocket-coffea run --cfg mutag_calib/configs/pt_reweighting/ptreweighting_2018UL_RunIISummer20UL.py -o pt_reweighting_2018 -e dask@lxplus
```

Produce 3D reweighting map with:
```bash
python mutag_calib/scripts/compute_3d_reweighting.py -i pt_reweighting/output_all.coffea -o pt_reweighting_2018/3d_reweighting --test
```

### Step 2: Run jobs to produce fit templates in all the tagger categories

TO DO.

### Step 3: Produce fit shapes and combine datacards

TO DO.
