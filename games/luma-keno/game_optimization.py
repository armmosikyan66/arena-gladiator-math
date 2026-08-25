"""Keno uses exact hypergeometric LUT weights. Do not run the Rust optimizer."""


class OptimizationSetup:
    def __init__(self, game_config: object):
        self.game_config = game_config
        self.game_config.opt_params = {}
