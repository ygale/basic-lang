from basic.expr import *

class LV(LookupVar):
    scalars: dict[str, float] = {
        'A': 2.0, 'B': 5.0, 'C': 3.0}
    arrays: dict[str, list[float]] = {
        'D': [7.0, 248.0, 9.0]}
    def lookup_scalar(self, v: VarName) -> float:
        return self.scalars[v]
    def lookup_array(self, a: ArrayElt) -> float:
        return self.arrays[a.name][int(a.subscr)]
lv = LV()
