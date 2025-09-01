from pocket_coffea.utils.configurator import Configurator
from pocket_coffea.lib.cut_definition import Cut
from pocket_coffea.lib.cut_functions import get_nObj_eq, get_nObj_min, get_HLTsel, get_nPVgood, goldenJson, eventFlags
from pocket_coffea.parameters.cuts import passthrough
from pocket_coffea.lib.categorization import CartesianSelection, MultiCut

from pocket_coffea.lib.weights.common.common import common_weights
from pocket_coffea.parameters.histograms import *
import mutag_calib
from mutag_calib.configs.fatjet_base.custom.cuts import get_ptmsd, get_ptmsd_window, get_nObj_minmsd, get_flavor, get_ptbin
from mutag_calib.configs.fatjet_base.custom.functions import get_inclusive_wp
from mutag_calib.configs.fatjet_base.custom.weights import SF_trigger_prescale, SF_ptetatau21_reweighting
import mutag_calib.workflows.mutag_oneMuAK8_processor as workflow
from mutag_calib.workflows.mutag_oneMuAK8_processor import mutagAnalysisOneMuonInAK8Processor
import os

localdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Loading default parameters
from pocket_coffea.parameters import defaults
default_parameters = defaults.get_default_parameters()
defaults.register_configuration_dir("config_dir", localdir+"/params")

parameters = defaults.merge_parameters_from_files(default_parameters,
                                                f"{localdir}/params/object_preselection.yaml",
                                                f"{localdir}/params/triggers_run3.yaml",
                                                f"{localdir}/params/triggers_prescales_run3.yaml",
                                                f"{localdir}/params/ptetatau21_reweighting.yaml",
                                                f"{localdir}/params/mutag_calibration.yaml",
                                                update=True)

samples = ["QCD_MuEnriched", "VJets", "TTto4Q","TWminus", "TWplus", "DATA_BTagMu"]
subsamples = {}
for s in filter(lambda x: 'DATA_BTagMu' not in x, samples):
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
                                                    label=r"FatJet $p_{T}$ [GeV]", bins=list(range(300, 1010, 10)))]
    )
    variables[f"{coll}_msoftdrop"] = HistConf([Axis(name=f"{coll}_msoftdrop", coll=coll, field="msoftdrop",
                                                           label=r"FatJet $m_{SD}$ [GeV]", bins=list(range(40, 410, 10)))]
    )
    variables[f"{coll}_tau21"] = HistConf([Axis(name=f"{coll}_tau21", coll=coll, field="tau21",
                                                           label=r"FatJet $\tau_{21}$", bins=[0, 0.20, 0.25, 0.30, 0.35, 
                                                           0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 1])]
    )
    variables[f"{coll}_logsumcorrSVmass"] = HistConf(
        [ Axis(coll="FatJetGood", field="logsumcorrSVmass", label=r"log($\sum({m^{corr}_{SV}})$)", bins=42, start=-2.4, stop=6) ]
    ),
    variables[f"{coll}_logsumcorrSVmass_tau21"] = HistConf(
            [ Axis(coll="FatJetGood", field="logsumcorrSVmass", label=r"log($\sum({m^{corr}_{SV}})$)", bins=42, start=-2.4, stop=6),
              Axis(coll="FatJetGood", field="tau21", label=r"$\tau_{21}$", type="variable", bins=[0, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 1]) ]
        ),

# Build cartesian selection category for fatjets
taggers = parameters["mutag_calibration"]["taggers"]

# Note: Here we assume that the pt binning and WPs are the same for all the eras!
# To be changed in the future if the WP is a function of the data taking year
pt_binning = parameters["mutag_calibration"]["pt_binning"]["2022_preEE"]
wp_dict = parameters["mutag_calibration"]["wp"]["2022_preEE"]

common_cats = {
    "inclusive" : [passthrough],
    "pt300msd40" : [get_ptmsd(300., 40.)],
    "pt300msd60" : [get_ptmsd(300., 60.)],
    "pt300msd80" : [get_ptmsd(300., 80.)],
    "pt300msd100" : [get_ptmsd(300., 100.)],
    "pt300msd80to170" : [get_ptmsd_window(300., 80., 170.)],
}

msd = 40.

cuts_pt = []
cuts_names_pt = []
for pt_low, pt_high in pt_binning.values():
    cuts_pt.append(get_ptbin(pt_low, pt_high))
    cuts_names_pt.append(f'Pt-{pt_low}to{pt_high}')
cuts_tagger = []
cuts_names_tagger = []
for tagger in taggers:
    for wp, wp_value in wp_dict[tagger].items():
        for region in ["pass", "fail"]:
            cuts_tagger.append(get_inclusive_wp(tagger, wp_value, region))
            cuts_names_tagger.append(f"msd{int(msd)}{tagger}{region}{wp}wp")

multicuts = [
    MultiCut(name="tagger",
             cuts=cuts_tagger,
             cuts_names=cuts_names_tagger),
    MultiCut(name="pt",
             cuts=cuts_pt,
             cuts_names=cuts_names_pt),
]

cfg = Configurator(
    parameters = parameters,
    datasets = {
        "jsons": ["datasets/MC_QCD_MuEnriched_run3.json",
                  "datasets/MC_VJets_run3.json",
                  "datasets/MC_TTto4Q_run3.json",
                  "datasets/MC_SingleTop_semileptonic_run3.json",
                  "datasets/MC_SingleTop_fullyhadronic_run3.json",
                  "datasets/DATA_BTagMu_run3.json"
                  ],
        "filter" : {
            "samples": samples,
            "samples_exclude" : [],
            "year": [
                '2022_preEE',
                '2022_postEE',
                '2023_preBPix',
                '2023_postBPix'
            ]
        },
        "subsamples": subsamples
    },

    workflow = mutagAnalysisOneMuonInAK8Processor,
    workflow_options = {},

    skim = [get_nPVgood(1),
            eventFlags,
            goldenJson,
            get_nObj_min(1, 200., "FatJet"),
            get_nObj_minmsd(1, 30., "FatJet"),
            get_nObj_min(2, 3., "Muon"),
            get_HLTsel()],

    preselections = [get_nObj_min(1, parameters.object_preselection["FatJet"]["pt"], "FatJetGood")],
    categories = CartesianSelection(multicuts=multicuts, common_cats=common_cats),

    weights_classes = common_weights + [SF_trigger_prescale + SF_ptetatau21_reweighting],
    weights = {
        "common": {
            "inclusive": ["genWeight","lumi","XS","sf_trigger_prescale",
                          "pileup", "sf_ptetatau21_reweighting"],
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
                # "inclusive" : ["JES_Total_AK8PFPuppi", "JER_AK8PFPuppi"]
                "inclusive" : []
            }
        }
    },

    variables = variables,

    columns = {}
)

# Registering custom functions
import cloudpickle
cloudpickle.register_pickle_by_value(workflow)
cloudpickle.register_pickle_by_value(mutag_calib)
