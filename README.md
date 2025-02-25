# Analysis workflow for calibration of boosted jets with the mu-tagged method
Repository for the calibration of large-radius jets with the mu-tagged method based on the [PocketCoffea](https://pocketcoffea.readthedocs.io/en/latest/index.html) analysis workflow.

## Installation
This package requires PocketCoffea >=0.9.8 as specified in the requirements.
The recommended running mode is to use the PocketCoffea singularity image available in `/cvmfs/unpacked.cern.ch/gitlab-registry.cern.ch/cms-analysis/general`.
In order to run the mu-tagged method analysis written in PocketCoffea, we create a virtual environment and install both the `PocketCoffea` and `mutag-calib` packages,
by running the following commands:

```bash

# Clone locally the PocketCoffea and mutag-calib repositories
git clone git@github.com:PocketCoffea/PocketCoffea.git
git clone git@github.com:mmarchegiani/mutag-calib.git
cd PocketCoffea

#Enter the Singularity image
apptainer shell --bind /afs -B /cvmfs/cms.cern.ch \
         --bind /tmp  --bind /eos/cms/ -B /etc/sysconfig/ngbauth-submit \
         -B ${XDG_RUNTIME_DIR}  --env KRB5CCNAME="FILE:${XDG_RUNTIME_DIR}/krb5cc"  \
         /cvmfs/unpacked.cern.ch/gitlab-registry.cern.ch/cms-analysis/general/pocketcoffea:lxplus-el9-stable

# Create a local virtual environment using the packages defined in the apptainer image
python -m venv --system-site-packages myenv

# Activate the environment
source myenv/bin/activate

# Install PocketCoffea in EDITABLE mode
pip install -e .[dev]

# Install mutag-calib in EDITABLE mode
cd -
cd mutag-calib
pip install -e .
```

Now the environment is setup. In order to use this environment in the future, just run:
```bash
# Enter the Singularity image
apptainer shell --bind /afs -B /cvmfs/cms.cern.ch \
         --bind /tmp  --bind /eos/cms/ -B /etc/sysconfig/ngbauth-submit \
         -B ${XDG_RUNTIME_DIR}  --env KRB5CCNAME="FILE:${XDG_RUNTIME_DIR}/krb5cc"  \
         /cvmfs/unpacked.cern.ch/gitlab-registry.cern.ch/cms-analysis/general/pocketcoffea:lxplus-el9-stable
# Activate the environment
source myenv/bin/activate
```

> **Tip:** You can create an alias for the `apptainer shell` command to enter the Singularity image and save it in your `~/.bashrc` file to avoid typing it every time. Add the following line to your `~/.bashrc`:
> ```bash
> alias sing='apptainer shell --bind /afs -B /cvmfs/cms.cern.ch --bind /tmp --bind /eos/cms/ -B /etc/sysconfig/ngbauth-submit -B ${XDG_RUNTIME_DIR} --env KRB5CCNAME="FILE:${XDG_RUNTIME_DIR}/krb5cc" /cvmfs/unpacked.cern.ch/gitlab-registry.cern.ch/cms-analysis/general/pocketcoffea:lxplus-el9-stable'
> ```
> Then, you can simply type `sing` to enter the Singularity image.

## Workflows
The folder `workflows` contains different PocketCoffea workflows that are needed to perform the analysis.
Here is their description:

- `pt_reweighting.py`: defines the `ptReweightProcessor` to compute the MC-to-data reweighting based on the 3D map in jet ($p_T$, $\eta$, $\tau_{21}$). It needs to be run once to compute the 3D reweighting map, that is then saved and used as a parameter for the next workflows.
- `fatjet_base.py`: defines the `fatjetBaseProcessor` that applies the custom object preselection needed for the calibration, creates all the branches that are counting the number of muons within the AK8 jet and creates branches specific to the taggers. **For Run 3 analyses, the definition of the tagger branches might have to be redefined here.**
- `mutag_processor.py`: defines the `mutagAnalysisProcessor` on top of `fatjetBaseProcessor`. It applies the $p_T$ and $M_{SD}$ cuts on the AK8 jet collection and applies the 3D reweighting to MC.
- `mutag_oneMuAK8_processor.py`: defines the `mutagAnalysisOneMuonInAK8Processor` on top of `mutagAnalysisProcessor`. It applies the selection on AK8 jets based on the number of soft muons contained in the AK8 jet (>=1 soft muon within the AK8 jet).

## Analysis steps
### Step 0: produce datasets definitions
The folder `datasets` contains the file `datasets_definitions_RunIISummer20UL.json` which contains the metadata of all the Run 2 datasets used for the calibration.
In order to perform the calibration with Run 3 data, **a new file containing the datasets definition of Run 3 datasets needs to be defined.**

Datasets to be included:

- MC
    - QCD_MuEnriched
    - V+jets
    - Single top
    - ttbar
- Data
    - BTagMu

To create json datasets:
```bash
pocket-coffea build-datasets --cfg datasets/datasets_definitions_RunIISummer20UL.json -o
```

Restricting the dataset source in Europe (recommended for working from lxplus):
```bash
pocket-coffea build-datasets --cfg datasets/datasets_definitions_RunIISummer20UL.json -o -rs 'T[123]_(FR|IT|DE|BE|CH|UK)_\w+'
```

For more detailed instructions on how to create datasets in PocketCoffea, please follow [this guide](https://pocketcoffea.readthedocs.io/en/latest/datasets.html#datasets-handling).

Once the json datasets are created, the configuration files have to be updated to run on the newly defined datasets.

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
