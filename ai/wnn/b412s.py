"""Snips MLP epoch sensitivity (post-hoc sensitivity check, NOT the pre-registered baseline)."""
import numpy as np, json, b412, b468
Xtr, Ytr, Xte, Yte, NC = b468.Xtr, b468.Ytr, b468.Xte, b468.Yte, b468.NC
for ep in (100, 200, 400):
    accs = [b412.mlp_acc(Xtr, Ytr, Xte, Yte, NC, ep, s) for s in (0, 1)]
    print(json.dumps({'snips_mlp_epochs': ep, 'acc': round(float(np.mean(accs)), 4)}), flush=True)
print('DONE', flush=True)
