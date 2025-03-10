from pocket_coffea.utils.configurator import Configurator
from pocket_coffea.lib.cut_definition import Cut
from pocket_coffea.lib.cut_functions import get_nObj_eq, get_nObj_min, get_HLTsel, get_nPVgood, goldenJson, eventFlags
from pocket_coffea.parameters.cuts import passthrough

from pocket_coffea.lib.weights.common.common import common_weights
from pocket_coffea.parameters.histograms import *
from mutag_calib.configs.fatjet_base.custom.cuts import get_ptmsd, get_nObj_minmsd, get_flavor
from mutag_calib.configs.fatjet_base.custom.functions import get_inclusive_wp
import mutag_calib.workflows.pt_reweighting as workflow
from mutag_calib.workflows.pt_reweighting import ptReweightProcessor
import numpy as np
import os

localdir = os.path.dirname(os.path.abspath(__file__))

# Loading default parameters
from pocket_coffea.parameters import defaults
default_parameters = defaults.get_default_parameters()
defaults.register_configuration_dir("config_dir", localdir+"/params")

parameters = defaults.merge_parameters_from_files(default_parameters,
                                                f"{localdir}/params/object_preselection.yaml",
                                                f"{localdir}/params/triggers.yaml",
                                                update=True)

samples = ["QCD_MuEnriched", "VJets", "SingleTop_ttbar", "DATA"]
subsamples = {}
for s in filter(lambda x: 'DATA' not in x, samples):
    subsamples[s] = {f"{s}_{f}" : [get_flavor(f)] for f in ['l', 'c', 'b', 'cc', 'bb']}

variables = {
    #**count_hist(name="nFatJetGood", coll="FatJetGood",bins=10, start=0, stop=10),
    #**count_hist(coll="FatJetGoodNMuon1",bins=10, start=0, stop=10),
    #**count_hist(coll="FatJetGoodNMuon2",bins=10, start=0, stop=10),
    #**count_hist(coll="FatJetGoodNMuonSJ1",bins=10, start=0, stop=10),
    #**count_hist(coll="FatJetGoodNMuonSJUnique1",bins=10, start=0, stop=10),
}

#collections = ["FatJetGoodNMuon1", "FatJetGoodNMuon2", "FatJetGoodNMuonSJ1", "FatJetGoodNMuonSJUnique1"]
collections = ["FatJetGood"]

for coll in collections:
    variables.update(**fatjet_hists(coll=coll))
    variables[f"{coll}_pt"] = HistConf([Axis(name=f"{coll}_pt", coll=coll, field="pt",
                                                    label=r"FatJet $p_{T}$ [GeV]", bins=list(range(350, 1010, 10)))])
    variables[f"{coll}_msoftdrop"] = HistConf([Axis(name=f"{coll}_msoftdrop", coll=coll, field="msoftdrop",
                                                           label=r"FatJet $m_{SD}$ [GeV]", bins=list(range(40, 410, 10)))])
    variables[f"{coll}_pt_eta"] = HistConf(
        [ Axis(name=f"{coll}_pos", coll=coll, field="pos", type="int", label=r"FatJet position", bins=2, start=0, stop=2),
          Axis(name=f"{coll}_pt", coll=coll, field="pt", type="variable", label=r"FatJet $p_{T}$ [GeV]",
               bins=[350., 400., 450., 500., 550., 600., 700., 800., 900., 2500.]),
          Axis(name=f"{coll}_eta", coll=coll, field="eta", type="variable", label=r"FatJet $\eta$",
               bins=[-5, -2, -1.75, -1.5, -1.25, -1, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 5]) ]
    )
    variables[f"{coll}_pt_eta_tau21"] = HistConf(
        [ Axis(name=f"{coll}_pos", coll=coll, field="pos", type="int", label=r"FatJet position", bins=2, start=0, stop=2),
          Axis(name=f"{coll}_pt", coll=coll, field="pt", type="variable", label=r"FatJet $p_{T}$ [GeV]",
               bins=[350., 400., 450., 500., 550., 600., 700., 800., 900., 2500.]),
          Axis(name=f"{coll}_eta", coll=coll, field="eta", type="variable", label=r"FatJet $\eta$",
               bins=[-5, -2, -1.75, -1.5, -1.25, -1, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 5]),
          Axis(name=f"{coll}_tau21", coll=coll, field="tau21", type="variable", label=r"FatJet $\tau_{21}$",
               bins=[0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1]) ]
    )
    variables[f"{coll}_pt_eta_tau21_bintau05"] = HistConf(
        [ Axis(name=f"{coll}_pos", coll=coll, field="pos", type="int", label=r"FatJet position", bins=2, start=0, stop=2),
          Axis(name=f"{coll}_pt", coll=coll, field="pt", type="variable", label=r"FatJet $p_{T}$ [GeV]",
               bins=[350., 400., 450., 500., 550., 600., 700., 800., 900., 2500.]),
          Axis(name=f"{coll}_eta", coll=coll, field="eta", type="variable", label=r"FatJet $\eta$",
               bins=[-5, -2, -1.75, -1.5, -1.25, -1, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 5]),
          Axis(name=f"{coll}_tau21", coll=coll, field="tau21", type="variable", label=r"FatJet $\tau_{21}$",
               bins=[0, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 1]) ]
    )

cfg = Configurator(
    parameters = parameters,
    datasets = {
        "jsons": ["datasets/MC_QCD_MuEnriched_RunIISummer20UL.json",
                  "datasets/MC_VJets_RunIISummer20UL.json",
                  "datasets/MC_top_RunIISummer20UL.json",
                  "datasets/DATA_BTagMu_RunIISummer20UL.json"],
        "filter" : {
            "samples": samples,
            "samples_exclude" : [],
            "year": ['2018']
        },
        "subsamples": subsamples
    },

    workflow = ptReweightProcessor,
    workflow_options = {},

    skim = [get_nPVgood(1),
            eventFlags,
            goldenJson,
            get_nObj_min(1, 200., "FatJet"),
            get_nObj_minmsd(1, 30., "FatJet"),
            get_nObj_min(2, 3., "Muon"),
            get_HLTsel()],

    preselections = [get_nObj_min(1, parameters.object_preselection["FatJet"]["pt"], "FatJetGood")],
    categories = {
        "inclusive" : [passthrough],
        "pt350msd40" : [get_ptmsd(350., 40.)],
        "pt350msd60" : [get_ptmsd(350., 60.)],
        "pt350msd80" : [get_ptmsd(350., 80.)],
        "pt350msd100" : [get_ptmsd(350., 100.)],
    },

    weights_classes = common_weights,
    weights = {
        "common": {
            "inclusive": ["genWeight","lumi","XS",
                          "pileup"],
            "bycategory" : {
            }
        },
        "bysample": {
        }
    },

    variations = {
        "weights": {
            "common": {
                "inclusive": [],
                "bycategory" : {
                }
            },
            "bysample": {
            }    
        },
        "shape": {
            "common": {
                "inclusive" : ["JES_Total_AK8PFPuppi", "JER_AK8PFPuppi"]
            }
        }
    },

    variables = variables,

    columns = {}
)

# Registering custom functions
import cloudpickle
cloudpickle.register_pickle_by_value(workflow)
