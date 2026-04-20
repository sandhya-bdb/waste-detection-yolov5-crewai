import torch

_orig_load = torch.load


def _safe_load(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _orig_load(*args, **kwargs)


torch.load = _safe_load

import detect

opt = detect.parse_opt()
detect.main(opt)
