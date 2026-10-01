"""Small CUDA diagnostic; no driver reset, package installation or model loading."""
import json
import subprocess
import sys
result={}
try:
    proc=subprocess.run(['nvidia-smi','--query-gpu=name,driver_version,memory.total','--format=csv,noheader'],capture_output=True,text=True,timeout=15)
    result['nvidia_smi']={'exit_code':proc.returncode,'stdout':proc.stdout.strip(),'stderr':proc.stderr.strip()}
except (OSError,subprocess.TimeoutExpired) as exc:
    result['nvidia_smi']={'error':str(exc)}
try:
    import torch
    result['torch']=torch.__version__; result['torch_cuda']=torch.version.cuda
    result['cuda_available']=torch.cuda.is_available()
    result['allocation_sum']=torch.ones(4,device='cuda').sum().item()
    torch.cuda.synchronize(); result['cuda_allocation']='passed'
except Exception as exc:
    result['cuda_allocation']='failed'; result['error']=type(exc).__name__+': '+str(exc)
print(json.dumps(result,indent=2))
sys.exit(0 if result['cuda_allocation']=='passed' else 1)
