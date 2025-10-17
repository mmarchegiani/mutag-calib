import yaml
import numpy as np
from coffea.util import load
import awkward as ak
import matplotlib.pyplot as plt
import mplhep as hep
hep.style.use("CMS")

def get_pt_quantiles(h, category='inclusive', quantiles=[0.25, 0.5, 0.75]):
    """
    Calculate quantiles of the pT distribution from a hist.Hist histogram.
    
    Parameters
    ----------
    h : hist.Hist
        Histogram with category and pT axes
    category : str
        Category to select from the 'cat' axis
    quantiles : list of float
        Quantile values to calculate (between 0 and 1)
        
    Returns
    -------
    dict
        Dictionary mapping quantile values to pT values
        
    Examples
    --------
    >>> quantiles = get_pt_quantiles(hist_obj, 'inclusive', [0.25, 0.5, 0.75, 0.9])
    >>> print(f"Median pT: {quantiles[0.5]:.1f} GeV")
    """
    # Select the category
    h_cat = h[{'cat': category}]
    
    # Get bin values (counts/weights) and edges
    values = h_cat.values()
    edges = h_cat.axes[0].edges
    
    # Calculate bin centers for interpolation
    centers = (edges[:-1] + edges[1:]) / 2
    
    # Calculate cumulative distribution
    cumsum = np.cumsum(values)
    total = cumsum[-1]
    
    if total == 0:
        raise ValueError(f"Empty histogram for category '{category}'")
    
    # Normalize to get CDF
    cdf = cumsum / total
    
    # Interpolate to find quantile values
    results = {}
    for q in quantiles:
        if q < 0 or q > 1:
            raise ValueError(f"Quantile {q} must be between 0 and 1")
        
        # Find the pT value corresponding to this quantile
        pt_value = np.interp(q, cdf, centers)
        results[q] = pt_value
    
    return results

def print_quantiles(h, category='inclusive', quantiles=[0.25, 0.5, 0.75, 0.9, 0.95, 0.99]):
    """
    Print quantiles in a nicely formatted way.
    
    Parameters
    ----------
    h : hist.Hist
        Histogram with category and pT axes
    category : str
        Category to select from the 'cat' axis
    quantiles : list of float
        Quantile values to calculate
    """
    q_vals = get_pt_quantiles(h, category, quantiles)
    
    print(f"pT quantiles for category '{category}':")
    print("-" * 40)
    for q, pt in q_vals.items():
        print(f"{q*100:5.1f}th percentile: {pt:7.1f} GeV")
    
    return q_vals


# Example usage:
# quantiles = get_pt_quantiles(hist_2022_preEE, 'inclusive', [0.5, 0.9, 0.95])
# print(f"Median: {quantiles[0.5]:.1f} GeV")
# print(f"90th percentile: {quantiles[0.9]:.1f} GeV")
#
# Or use the print function:
# print_quantiles(hist_2022_preEE, 'pt300msd100')

filename = "/eos/user/m/mmarcheg/BTV/mutag-calib/ptreweighting_run3_withJEC/output_all.coffea"
o = load(filename)
h_data = o["variables"]["FatJetGood_pt"]["DATA_BTagMu"]

dataset_dict = {
    "2022_preEE" : ["DATA_BTagMu_2022_preEE_EraC", "DATA_BTagMu_2022_preEE_EraD"],
    "2022_postEE" : ["DATA_BTagMu_2022_postEE_EraE", "DATA_BTagMu_2022_postEE_EraF", "DATA_BTagMu_2022_postEE_EraG"],
    "2023_preBPix" : ["DATA_BTagMu_2023_preBPix_EraCv1", "DATA_BTagMu_2023_preBPix_EraCv2", "DATA_BTagMu_2023_preBPix_EraCv3", "DATA_BTagMu_2023_preBPix_EraCv4"],
    "2023_postBPix" : ["DATA_BTagMu_2023_postBPix_EraD"]
}

histos = {}
for year, datasets_byyear in dataset_dict.items():
    h_data_byyear = sum(h_data[dataset] for dataset in datasets_byyear)
    histos[year] = h_data_byyear

quantiles = {}
cat = "inclusive"
for year, histo in histos.items():
    quantiles[year] = get_pt_quantiles(histo, category=cat, quantiles=[0.34, 0.67, 1.0])

# Save quantiles to a YAML file
filename = "pt_quantiles_run3.yaml"
with open(filename, "w") as f:
    yaml.dump(quantiles, f)

# Print quantiles
for year, histo in histos.items():
    print(f"\nQuantiles for year {year}:")
    print_quantiles(histo, category=cat, quantiles=[0.34, 0.67, 1.0])

# Plotting the pT distributions with quantile lines
fig, ax = plt.subplots(1, 1, figsize=[10,10])
chosen_quantiles = [350, 425]
for year, histo in histos.items():
    histo[{"cat" : "inclusive"}].plot1d(ax=ax, label=f"Data ({year})")
for q, linestyle, q_perc in zip(chosen_quantiles, ["dashed", "dotted"], [34, 67]):
    ax.vlines(q, 0, 175000., color="gray", linestyle=linestyle, label=f"{q_perc}% quantile ({q} GeV)")
ax.legend()
hep.cms.text(
    "Preliminary",
    #fontsize=self.style.fontsize,
    #loc=self.style.experiment_label_loc,
    ax=ax,
)
filename = "quantiles.png"
print(f"Saving quantile plot to {filename}")
plt.savefig(filename, dpi=300)
