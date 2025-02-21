from pocket_coffea.lib.weights_manager import WeightCustom
from config.fatjet_base.custom.scale_factors import pt_reweighting, pteta_reweighting

pt_weight = WeightCustom(
    name="pt_reweighting",
    function= lambda events, size, metadata, shape_variation: [("pt_reweighting", pt_reweighting(events, metadata['year']))]
)

pteta_weight = WeightCustom(
    name="pteta_reweighting",
    function= lambda events, size, metadata, shape_variation: [("pteta_reweighting", pteta_reweighting(events, metadata['year']))]
)
