# Example script to run maximum likelihood fit to extract the SF

combine -M FitDiagnostics -d workspace.root --saveWorkspace --name .msd-80to170_Pt-300toInf_particleNet_XbbVsQCD-HHbbtt --cminDefaultMinimizerStrategy 2 --robustFit=1 --saveShapes --saveWithUncertainties --saveOverallShapes --redefineSignalPOIs=r,SF_c,SF_light --setParameters r=1,l=1 --freezeParameters l --robustHesse=1 --stepSize=0.001 --X-rtd=MINIMIZER_analytic --X-rtd MINIMIZER_MaxCalls=9999999 --cminFallbackAlgo Minuit2,Migrad,0:0.2 --X-rtd FITTER_NEW_CROSSING_ALGO --X-rtd FITTER_NEVER_GIVE_UP --X-rtd FITTER_BOUND

