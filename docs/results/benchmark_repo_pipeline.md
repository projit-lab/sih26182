# Repo Synthetic Benchmark Pipeline

This is the repo's own synthetic benchmark (validation/). The deck's 84.3% / p=2.5e-12 come from data_scarcity_validation.py, which is not in this repo.

## Command
`python -m validation.robustness_check`

## Results
```
Running across 5 different random seeds to check this isn't a lucky draw...

  Seed   SP-Top1 (Mix)   ER-Top1 (Mix)   SP-Top3 (Mix)   ER-Top3 (Mix)    SP-MRR (Mix)    ER-MRR (Mix)
     1           0.633           0.862           0.945           0.945           0.790           0.909
     2           0.720           0.881           0.941           0.975           0.832           0.926
     3           0.670           0.878           0.948           0.930           0.816           0.916
     4           0.708           0.912           0.973           0.991           0.836           0.948
     5           0.717           0.775           0.933           0.992           0.832           0.885

--- Direct (Easy) Cases ---
  Seed   SP-Top1 (Dir)   ER-Top1 (Dir)   SP-Top3 (Dir)   ER-Top3 (Dir)    SP-MRR (Dir)    ER-MRR (Dir)
     1           0.901           0.930           1.000           1.000           0.948           0.962
     2           0.903           0.952           1.000           1.000           0.946           0.970
     3           0.908           0.892           1.000           0.954           0.951           0.932
     4           0.806           0.955           0.955           1.000           0.886           0.975
     5           0.767           0.900           0.967           1.000           0.871           0.950

Mean ± Std on MIXER-routed cases across 5 seeds:
  SP : Top1=0.690 ± 0.034, Top3=0.948 ± 0.014, MRR=0.821 ± 0.017
  ER : Top1=0.862 ± 0.046, Top3=0.967 ± 0.025, MRR=0.917 ± 0.020

Mean ± Std on DIRECT cases across 5 seeds:
  SP : Top1=0.857 ± 0.059, Top3=0.984 ± 0.019, MRR=0.921 ± 0.035
  ER : Top1=0.926 ± 0.026, Top3=0.991 ± 0.018, MRR=0.958 ± 0.016

Mean gap (ER - SP Top1) on mixer-routed cases across 5 seeds: +0.172  (std: 0.061)

--- Paired significance test (McNemar) on seed=42 run for a concrete p-value ---
{'ER_right_SP_wrong': 24, 'SP_right_ER_wrong': 2, 'both_right': 82, 'both_wrong': 4, 'mcnemar_chi2': 16.96153846153846, 'p_value': 3.814477782715375e-05}
```
