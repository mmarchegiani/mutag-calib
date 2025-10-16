# Example script to run the uncertainty breakdown
# Note: Taken from Run 2 calibration. Needs to be readapted for Run 3

combine -M MultiDimFit -d model_combined.root --saveWorkspace --name _msd40particleNetMD_Xbb_QCDHwp_Pt-450to500 --algo=singles --cminDefaultMinimizerStrategy 2 --robustFit=1 --redefineSignalPOIs=b_bb,c_cc,l --setParameters r=1,l=1 --freezeParameters r,l --rMin 1 --rMax 1 --robustHesse=1 --stepSize=0.001 --X-rtd=MINIMIZER_analytic --X-rtd MINIMIZER_MaxCalls=9999999 --cminFallbackAlgo Minuit2,Migrad,0:0.2 --X-rtd FITTER_NEW_CROSSING_ALGO --X-rtd FITTER_NEVER_GIVE_UP --X-rtd FITTER_BOUND
combine higgsCombine_msd40particleNetMD_Xbb_QCDHwp_Pt-450to500.MultiDimFit.mH120.root -M MultiDimFit -n .scan.total --algo grid --snapshotName MultiDimFit --redefineSignalPOIs=b_bb --setParameters r=1 --freezeParameters r --setParameterRanges b_bb=0.5,2:c_cc=0.5,2:l=0.5,2
combine higgsCombine_msd40particleNetMD_Xbb_QCDHwp_Pt-450to500.MultiDimFit.mH120.root -M MultiDimFit -n .freeze.JER --algo grid --snapshotName MultiDimFit --redefineSignalPOIs=b_bb --setParameters r=1 --freezeParameters r,JER --setParameterRanges b_bb=0.5,2:c_cc=0.5,2:l=0.5,2

combine higgsCombine_msd40particleNetMD_Xbb_QCDHwp_Pt-450to500.MultiDimFit.mH120.root -M MultiDimFit -n .freeze.psWeight_isr --algo grid --snapshotName MultiDimFit --redefineSignalPOIs=b_bb --setParameters r=1 --freezeParameters r,JER,psWeight_isr --setParameterRanges b_bb=0.5,2:c_cc=0.5,2:l=0.5,2

combine higgsCombine_msd40particleNetMD_Xbb_QCDHwp_Pt-450to500.MultiDimFit.mH120.root -M MultiDimFit -n .freeze.psWeight_fsr --algo grid --snapshotName MultiDimFit --redefineSignalPOIs=b_bb --setParameters r=1 --freezeParameters r,JER,psWeight_isr,psWeight_fsr --setParameterRanges b_bb=0.5,2:c_cc=0.5,2:l=0.5,2

combine higgsCombine_msd40particleNetMD_Xbb_QCDHwp_Pt-450to500.MultiDimFit.mH120.root -M MultiDimFit -n .freeze.JES_Total --algo grid --snapshotName MultiDimFit --redefineSignalPOIs=b_bb --setParameters r=1 --freezeParameters r,JER,psWeight_isr,psWeight_fsr,JES_Total --setParameterRanges b_bb=0.5,2:c_cc=0.5,2:l=0.5,2

combine higgsCombine_msd40particleNetMD_Xbb_QCDHwp_Pt-450to500.MultiDimFit.mH120.root -M MultiDimFit -n .freeze.QCDFlvCompos --algo grid --snapshotName MultiDimFit --redefineSignalPOIs=b_bb --setParameters r=1 --freezeParameters r,JER,psWeight_isr,psWeight_fsr,JES_Total,QCDFlvCompos --setParameterRanges b_bb=0.5,2:c_cc=0.5,2:l=0.5,2

combine higgsCombine_msd40particleNetMD_Xbb_QCDHwp_Pt-450to500.MultiDimFit.mH120.root -M MultiDimFit -n .freeze.pileup --algo grid --snapshotName MultiDimFit --redefineSignalPOIs=b_bb --setParameters r=1 --freezeParameters r,JER,psWeight_isr,psWeight_fsr,JES_Total,QCDFlvCompos,pileup --setParameterRanges b_bb=0.5,2:c_cc=0.5,2:l=0.5,2

combine higgsCombine_msd40particleNetMD_Xbb_QCDHwp_Pt-450to500.MultiDimFit.mH120.root -M MultiDimFit -n .freeze.frac_bb --algo grid --snapshotName MultiDimFit --redefineSignalPOIs=b_bb --setParameters r=1 --freezeParameters r,JER,psWeight_isr,psWeight_fsr,JES_Total,QCDFlvCompos,pileup,frac_bb --setParameterRanges b_bb=0.5,2:c_cc=0.5,2:l=0.5,2

combine higgsCombine_msd40particleNetMD_Xbb_QCDHwp_Pt-450to500.MultiDimFit.mH120.root -M MultiDimFit -n .freeze.frac_l --algo grid --snapshotName MultiDimFit --redefineSignalPOIs=b_bb --setParameters r=1 --freezeParameters r,JER,psWeight_isr,psWeight_fsr,JES_Total,QCDFlvCompos,pileup,frac_bb,frac_l --setParameterRanges b_bb=0.5,2:c_cc=0.5,2:l=0.5,2

combine higgsCombine_msd40particleNetMD_Xbb_QCDHwp_Pt-450to500.MultiDimFit.mH120.root -M MultiDimFit -n .freeze.frac_cc --algo grid --snapshotName MultiDimFit --redefineSignalPOIs=b_bb --setParameters r=1 --freezeParameters r,JER,psWeight_isr,psWeight_fsr,JES_Total,QCDFlvCompos,pileup,frac_bb,frac_l,frac_cc --setParameterRanges b_bb=0.5,2:c_cc=0.5,2:l=0.5,2

combine higgsCombine_msd40particleNetMD_Xbb_QCDHwp_Pt-450to500.MultiDimFit.mH120.root -M MultiDimFit -n .freeze.lumi --algo grid --snapshotName MultiDimFit --redefineSignalPOIs=b_bb --setParameters r=1 --freezeParameters r,JER,psWeight_isr,psWeight_fsr,JES_Total,QCDFlvCompos,pileup,frac_bb,frac_l,frac_cc,lumi --setParameterRanges b_bb=0.5,2:c_cc=0.5,2:l=0.5,2

python /work/mmarcheg/BTVNanoCommissioning/scripts/fit/plot1DScanWithOutput.py higgsCombine.scan.total.MultiDimFit.mH120.root --main-label "Total Uncert." --others higgsCombine.freeze.JER.MultiDimFit.mH120.root:JER:2 higgsCombine.freeze.psWeight_isr.MultiDimFit.mH120.root:psWeight_isr:3 higgsCombine.freeze.psWeight_fsr.MultiDimFit.mH120.root:psWeight_fsr:4 higgsCombine.freeze.JES_Total.MultiDimFit.mH120.root:JES_Total:5 higgsCombine.freeze.QCDFlvCompos.MultiDimFit.mH120.root:QCDFlvCompos:6 higgsCombine.freeze.pileup.MultiDimFit.mH120.root:pileup:7 higgsCombine.freeze.frac_bb.MultiDimFit.mH120.root:frac_bb:8 higgsCombine.freeze.frac_l.MultiDimFit.mH120.root:frac_l:9 higgsCombine.freeze.frac_cc.MultiDimFit.mH120.root:frac_cc:10 higgsCombine.freeze.lumi.MultiDimFit.mH120.root:lumi:11 --output breakdown --y-max 10 --y-cut 40 --breakdown "JER,psWeight_isr,psWeight_fsr,JES_Total,QCDFlvCompos,pileup,frac_bb,frac_l,frac_cc,lumi,stat" --POI b_bb

