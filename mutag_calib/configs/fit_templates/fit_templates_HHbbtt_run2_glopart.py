"""
Run 2 UL GloParT fit templates for HH->bbtt scale factors.

Uses globalParT3_XbbVsQCDTopW tagger (Xbb vs. QCD+top+Xqq+Xcs) with WP 0.369 (nine score > 0.2).
Runs on NanoAODv15 reprocessed Run 2 UL samples.

IMPORTANT: Before running, ensure:
  1. globalParT3_Xbb field exists in Run 2 NanoAODv15 files (Step 0 verification)
  2. Dataset JSONs have been built: pocket-coffea build-datasets --cfg datasets/datasets_definitions_*_run2.json -o ...
  3. pT reweighting maps exist (Step 4): FatJetGood_pt_eta_tau21_{year}_reweighting.json

Usage:
  pocket-coffea run --cfg mutag_calib/configs/fit_templates/fit_templates_HHbbtt_run2_glopart.py \\
    -o fit_templates_HHbbtt_run2_glopart -e dask@lxplus \\
    --custom-run-options mutag_calib/configs/params/run_options.yaml --process-separately
"""

from pocket_coffea.utils.configurator import Configurator
from pocket_coffea.lib.cut_definition import Cut
from pocket_coffea.lib.cut_functions import get_nObj_eq, get_nObj_min, get_HLTsel, get_nPVgood, goldenJson, eventFlags
from pocket_coffea.parameters.cuts import passthrough
from pocket_coffea.lib.categorization import CartesianSelection, MultiCut

from pocket_coffea.lib.calibrators.common.common import JetsCalibrator
from mutag_calib.lib.calibrators import FixedJetsSoftdropMassCalibrator as JetsSoftdropMassCalibrator
from pocket_coffea.lib.weights.common.common import common_weights
from pocket_coffea.parameters.histograms import *
import mutag_calib
from mutag_calib.configs.fatjet_base.custom.cuts import get_ptglopartmass, get_ptglopartmass_window, get_nObj_minmsd, get_flavor, get_ptbin, get_globalParT3massbin
from mutag_calib.configs.fatjet_base.custom.functions import get_inclusive_wp, get_tagger_window
from mutag_calib.configs.fatjet_base.custom.weights import SF_trigger_prescale
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
                                                f"{localdir}/params/jets_calibration.yaml",
                                                f"{localdir}/params/triggers_run2.yaml",
                                                f"{localdir}/params/triggers_prescales_run2.yaml",
                                                f"{localdir}/params/ptetatau21_reweighting_HHbbtt_run2.yaml",
                                                f"{localdir}/params/mutag_calibration_HHbbtt_run2.yaml",
                                                f"{localdir}/params/plotting_style.yaml",
                                                update=True)

# AK8PFPuppi JEC/JER for Run 2 NanoAODv15 is set in params/jets_calibration.yaml
# (official cms-griddata.cern.ch Run2-<year>-UL-NanoAODv15 catalog).
# Run 2 AK4 corrections come from PocketCoffea's AK4PFchs defaults; there is no
# Run 2 AK4PFPuppi in the defaults and nothing binds it to a collection here.

samples = [
    "QCD_MuEnriched",
    "QCD_Madgraph",
    "VJets",
    "TTto4Q",
    "SingleTop",
    "DATA_BTagMu"
]
subsamples = {}
for s in filter(lambda x: 'DATA_BTagMu' not in x, samples):
    subsamples[s] = {f"{s}_{f}" : [get_flavor(f)] for f in ['l', 'c', 'b', 'cc', 'bb']}

variables = {}

collections = ["FatJetGood"]

for coll in collections:
    variables.update(**fatjet_hists(coll=coll))
    variables[f"{coll}_pt"] = HistConf([Axis(name=f"{coll}_pt", coll=coll, field="pt",
                                                    label=r"FatJet $p_{T}$ [GeV]", bins=list(range(300, 1010, 10)))]
    )
    variables[f"{coll}_msoftdrop"] = HistConf([Axis(name=f"{coll}_msoftdrop", coll=coll, field="msoftdrop",
                                                           label=r"FatJet $m_{SD}$ [GeV]", bins=list(range(0, 410, 10)))]
    )
    variables[f"{coll}_msoftdrop_raw"] = HistConf([Axis(name=f"{coll}_msoftdrop_raw", coll=coll, field="msoftdrop_raw",
                                                           label=r"FatJet $m_{SD}$ [GeV]", bins=list(range(0, 410, 10)))]
    )
    variables[f"{coll}_tau21"] = HistConf([Axis(name=f"{coll}_tau21", coll=coll, field="tau21",
                                                           label=r"FatJet $\tau_{21}$", bins=[0, 0.20, 0.25, 0.30, 0.35,
                                                           0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 1])]
    )
    variables[f"{coll}_globalParT3_XbbVsQCDTopW"] = HistConf(
        [ Axis(name=f"{coll}_globalParT3_XbbVsQCDTopW", coll=coll, field="globalParT3_XbbVsQCDTopW",
               label=r"GloParT $X_{bb}$ vs QCD+top+Xqq+Xcs", bins=100, start=0, stop=1) ]
    )
    variables[f"{coll}_globalParT3_mass"] = HistConf(
        [ Axis(name=f"{coll}_globalParT3_mass", coll=coll, field="globalParT3_mass",
               label=r"FatJet GloParT regressed mass [GeV]", bins=list(range(0, 410, 10))) ]
    )
    variables[f"{coll}_logsumcorrSVmass"] = HistConf(
        [ Axis(coll="FatJetGood", field="logsumcorrSVmass", label=r"log($\sum({m^{corr}_{SV}})$)", bins=42, start=-2.4, stop=6) ]
    )
    variables[f"{coll}_logsumcorrSVmass_tau21"] = HistConf(
        [ Axis(coll="FatJetGood", field="logsumcorrSVmass", label=r"log($\sum({m^{corr}_{SV}})$)", bins=42, start=-2.4, stop=6),
          Axis(coll="FatJetGood", field="tau21", label=r"$\tau_{21}$", type="variable", bins=[0, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 1]) ]
    )

# Build dictionary of workflow options
workflow_options = {
    "histograms_to_reweigh" : {
        "by_pos" : {
            "all" : [name for name in variables.keys() if name.startswith("FatJetGood_") and not name.endswith(("_1", "_2"))]
        }
    }
}

# Use only GloParT tagger for Run 2 (same as 2024)
# IMPORTANT: Do NOT add globalParT3_XbbVsQCDTopW to global taggers list in YAML
taggers = ["globalParT3_XbbVsQCDTopW"]

# Years to process — must share the same pt_binning.
# 2017/2018 use [300,400,450,inf], 2016 uses [300,350,425,inf].
# Run years with different binning as separate jobs.
year_filter = [
    # '2018',
    # '2017',
    '2016_PostVFP',
    '2016_PreVFP'
]

pt_binning = parameters["mutag_calibration"]["pt_binning"][year_filter[0]]
wp_dict = parameters["mutag_calibration"]["wp"][year_filter[0]]
mass_binning = parameters["mutag_calibration"]["globalParT3mass_binning"][year_filter[0]]

common_cats = {
    "inclusive" : [passthrough],
    # "pt300globalParT3mass50" : [get_ptglopartmass(300., 50.)],
    "pt300globalParT3mass80to170" : [get_ptglopartmass_window(300., 80., 170.)],
}

# Define cuts to select bins in pt
cuts_pt = []
cuts_names_pt = []
for pt_low, pt_high in pt_binning:
    cuts_pt.append(get_ptbin(pt_low, pt_high))
    cuts_names_pt.append(f'Pt-{pt_low}to{pt_high}')

# Define cuts to select bins in GloParT regressed mass
cuts_mass = []
cuts_names_mass = []
for mass_low, mass_high in mass_binning:
    cuts_mass.append(get_globalParT3massbin(mass_low, mass_high))
    cuts_names_mass.append(f'globalParT3mass-{mass_low}to{mass_high}')

# Define cuts to select bins in tagger WPs.
# Exclusive tiers: Loose-fail=(-Inf,L), Loose-pass=Medium-fail=[L,M),
# Medium-pass=Tight-fail=[M,T), Tight-pass=[T,Inf)
wp_tiers = ["Loose", "Medium", "Tight"]
cuts_tagger = []
cuts_names_tagger = []
for tagger in taggers:
    edges = ["-Inf"] + [wp_dict[tagger][tier] for tier in wp_tiers] + ["Inf"]
    for i, tier in enumerate(wp_tiers):
        fail_low, fail_high = edges[i], edges[i + 1]
        pass_low, pass_high = edges[i + 1], edges[i + 2]
        cuts_tagger.append(get_tagger_window(tagger, fail_low, fail_high))
        cuts_names_tagger.append(f"{tagger}-{tier}-fail")
        cuts_tagger.append(get_tagger_window(tagger, pass_low, pass_high))
        cuts_names_tagger.append(f"{tagger}-{tier}-pass")

# Define multicuts for pt, GloParT mass and tagger WPs
multicuts = [
    MultiCut(name="globalParT3mass",
             cuts=cuts_mass,
             cuts_names=cuts_names_mass),
    MultiCut(name="pt",
             cuts=cuts_pt,
             cuts_names=cuts_names_pt),
    MultiCut(name="tagger",
             cuts=cuts_tagger,
             cuts_names=cuts_names_tagger),
]

cfg = Configurator(
    parameters = parameters,
    datasets = {
        "jsons": ["datasets/MC_QCD_MuEnriched_run2_redirector.json",
                  "datasets/MC_QCD_Madgraph_run2_redirector.json",
                  "datasets/MC_VJets_run2_redirector.json",
                  "datasets/MC_TTto4Q_run2_redirector.json",
                  "datasets/MC_singletop_run2_redirector.json",
                  "datasets/DATA_BTagMu_run2_redirector.json"],
        "filter" : {
            "samples": samples,
            "samples_exclude" : [],
            "year": year_filter
        },
        "subsamples": subsamples
    },

    workflow = mutagAnalysisOneMuonInAK8Processor,
    workflow_options = workflow_options,

    skim = [get_nPVgood(1),
            eventFlags,
            goldenJson,
            get_nObj_min(1, 200., "FatJet"),
            get_nObj_minmsd(1, 30., "FatJet"),
            get_nObj_min(1, 3., "Muon"),
            get_HLTsel()],

    preselections = [get_nObj_min(1, parameters.object_preselection["FatJet"]["pt"], "FatJetGood")],
    categories = CartesianSelection(multicuts=multicuts, common_cats=common_cats),

    weights_classes = common_weights + [SF_trigger_prescale],
    weights = {
        "common": {
            "inclusive": ["genWeight","lumi","XS","sf_trigger_prescale",
                          "pileup"],
            "bycategory" : {
            }
        },
        "bysample": {
            "QCD_Madgraph": {
                "inclusive": ["sf_partonshower_isr", "sf_partonshower_fsr"],
                "bycategory" : {
                }
            },
            "VJets": {
                "inclusive": ["sf_partonshower_isr", "sf_partonshower_fsr"],
                "bycategory" : {
                }
            },
            "TTto4Q": {
                "inclusive": ["sf_partonshower_isr", "sf_partonshower_fsr"],
                "bycategory" : {
                }
            },
            "SingleTop": {
                "inclusive": ["sf_partonshower_isr", "sf_partonshower_fsr"],
                "bycategory" : {
                }
            }
        }
    },

    calibrators = [JetsCalibrator, JetsSoftdropMassCalibrator],
    variations = {
        "weights": {
            "common": {
                "inclusive": ["pileup"],
                "bycategory" : {
                }
            },
            "bysample": {
                "QCD_Madgraph": {
                    "inclusive": ["sf_partonshower_isr", "sf_partonshower_fsr"],
                    "bycategory": {
                    }
                },
                "VJets": {
                    "inclusive": ["sf_partonshower_isr", "sf_partonshower_fsr"],
                    "bycategory": {
                    }
                },
                "TTto4Q": {
                    "inclusive": ["sf_partonshower_isr", "sf_partonshower_fsr"],
                    "bycategory": {
                    }
                },
                "SingleTop": {
                    "inclusive": ["sf_partonshower_isr", "sf_partonshower_fsr"],
                    "bycategory": {
                    }
                }
            }
        },
        "shape": {
            "common": {
                "inclusive" : ["jet_calibration"]
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
