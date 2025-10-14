files=(
	datasets/datasets_definitions_DATA_BTagMu_run3.json
	datasets/datasets_definitions_QCD_MuEnriched_run3.json
	datasets/datasets_definitions_singletop_fullyhadronic.json
	datasets/datasets_definitions_singletop_s-channel.json
	datasets/datasets_definitions_singletop_semileptonic.json
	datasets/datasets_definitions_TTto4Q_run3.json
	datasets/datasets_definitions_VJets_run3.json
)

for cfg in "${files[@]}"; do
	pocket-coffea build-datasets --cfg "$cfg" -o -rs 'T[123]_(FR|IT|DE|BE|CH|UK|ES|UA|LV|HU|PT|FI)_\w+' -bs T1_DE_KIT_Disk -bs T1_FR_CCIN2P3_Disk -bs T1_US_FNAL_Disk -bs T1_RU_JINR_Disk
done
