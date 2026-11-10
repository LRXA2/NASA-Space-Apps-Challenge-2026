# Step 2 — Directional route labels

This step will explain how one terrain tensor receives expected answers such as:

```text
north → south: passable
east → west: blocked
overall class: marginal
```

We will cover conservative, nominal and permissive slope scenarios; connected
corridors; the `operable`, `marginal`, `non_operable` and `unknown` meanings; and
why the current labels are provisional.

Implementation reference: [`route_labels.py`](../../labels/route_labels.py).

Finish [`01_data`](../01_data/README.md) before continuing here.

