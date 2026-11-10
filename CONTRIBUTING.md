# Contributing

The point of this repo is to be *falsifiable*. Corrections with a source are the most
valuable thing you can contribute; corrections without one are opinions.

## Good contributions

- **A better source** for any figure in `data/components.json`. Change the value and
  update `source` and `kind`. If it moves a headline conclusion, say so in the PR.
- **Measured data.** If you have dyno or on-road numbers, add them under `data/` with
  a description of the rig, and wire them in as an alternative to the estimate.
- **A modelling error.** Show the arithmetic.

## Rules

1. Every number added to `data/components.json` needs `kind` and `source`.
   `kind` is one of `literature`, `datasheet`, `estimate`.
2. `estimate` values are allowed — but they must be labelled as such. Do not upgrade
   an estimate's tag because it "seems right".
3. If a declared `range` exists, the nominal value must sit inside it. The test suite
   enforces this.
4. Run before pushing:

   ```bash
   python3 -m unittest discover -s tests -v
   python3 analysis/model.py > docs/model-output.txt
   ```

   Commit the regenerated `docs/model-output.txt` with any change that affects output,
   so diffs show what the numbers did.

## Changing a conclusion

If new data reverses a headline finding, rewrite the affected README sections rather
than leaving stale prose next to fresh numbers. A repo that argues a position while its
own model says otherwise is worse than no repo.
