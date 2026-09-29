# Attribution Engine Scaling

| N | nodes | edges | factorize s | per-query ms | peak MB | CG per-query ms |
|---|-------|-------|-------------|--------------|---------|-----------------|
| 200 | 200 | 396 | 0.0056 | 0.19 | 0.1 | 2.14 |
| 2000 | 2000 | 3996 | 0.0796 | 1.56 | 1.7 | 3.71 |
| 20000 | 20000 | 39996 | 43.9672 | 171.66 | 20.5 | 65.69 |

## System Info
- CPU: AMD64 Family 25 Model 116 Stepping 1, AuthenticAMD
- Python: 3.13.5
- NumPy: 2.5.3
- SciPy: 1.18.1
- NetworkX: 3.6.1
