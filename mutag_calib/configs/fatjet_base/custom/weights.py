from pocket_coffea.lib.weights.weights import WeightLambda
from mutag_calib.configs.fatjet_base.custom.scale_factors import pt_reweighting, pteta_reweighting, sf_ptetatau21_reweighting, sf_trigger_prescale

pt_weight = WeightLambda.wrap_func(
    name="pt_reweighting",
    function= lambda events, size, metadata, shape_variation: [("pt_reweighting", pt_reweighting(events, metadata['year']))]
)

pteta_weight = WeightLambda.wrap_func(
    name="pteta_reweighting",
    function= lambda events, size, metadata, shape_variation: [("pteta_reweighting", pteta_reweighting(events, metadata['year']))]
)

SF_trigger_prescale = WeightLambda.wrap_func(
    name="sf_trigger_prescale",
    function=lambda params, metadata, events, size, shape_variations:
        sf_trigger_prescale(events, metadata['year'], params),
    has_variations=False,
    )

SF_ptetatau21_reweighting = WeightLambda.wrap_func(
    name="sf_ptetatau21_reweighting",
    function=lambda params, metadata, events, size, shape_variations:
        sf_ptetatau21_reweighting(events, metadata['year'], params),
    has_variations=True
)
