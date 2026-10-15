"""Bounded diagnostic counters for the reference IR executor, not a JIT tier."""
import interp


class ExecutionProfile:
    """Count function/block entries without retaining user argument values."""
    def __init__(self, max_sites=1024):
        if type(max_sites) is not int or not 1 <= max_sites <= 65536:
            raise ValueError("profile max_sites must be 1..65536")
        self.max_sites = max_sites
        self.sites = {}
        self.dropped_events = 0

    def _record(self, key, types=None):
        if key not in self.sites:
            if len(self.sites) >= self.max_sites:
                self.dropped_events = min(2147483647, self.dropped_events + 1)
                return
            self.sites[key] = {"count": 0}
        site = self.sites[key]
        site["count"] = min(2147483647, site["count"] + 1)
        if types is not None:
            variants = site.setdefault("argument_types", [])
            if types not in variants:
                if len(variants) < 8:
                    variants.append(types)
                else:
                    site["megamorphic"] = True

    def enter(self, function, frame):
        types = [interp.tname(frame.vars[name]) for name in function["params"]]
        self._record((function["name"], "entry", ""), types)

    def block(self, function, label):
        self._record((function["name"], "block", label))

    def snapshot(self):
        return {"version": 1, "mode": "reference-ir-profile-not-jit",
                "max_sites": self.max_sites, "dropped_events": self.dropped_events,
                "sites": [{"function": key[0], "kind": key[1], "label": key[2],
                           **{name: ([list(v) for v in value] if name == "argument_types" else value)
                              for name, value in site.items()}}
                          for key, site in sorted(self.sites.items())]}
