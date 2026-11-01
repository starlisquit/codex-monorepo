"""Render Flux substitutions with Flux itself; settings are non-secret cluster inputs."""
from pathlib import Path
import os
import subprocess
import yaml

class LiteralDumper(yaml.SafeDumper):pass
LiteralDumper.add_representer(str,lambda dumper,value:dumper.represent_scalar('tag:yaml.org,2002:str',value,style='|' if '\n' in value else None))

FLUX=os.environ.get('FLUX_BIN','flux')
KUSTOMIZE=os.environ.get('KUSTOMIZE_BIN','kustomize')
def example_variables():
 return yaml.safe_load((Path(__file__).resolve().parents[3]/'docs/runbooks/examples/cluster-settings.example.yaml').read_text())['data']

def variables_for(run):
 p=Path(run)/'flux-system/cluster-settings.yaml'
 values={'var_substitution_enabled':'true'}
 if not p.exists():values.update(example_variables())
 if p.exists():
  obj=yaml.safe_load(p.read_text())
  if obj.get('kind')!='ConfigMap':raise ValueError('cluster-settings.yaml must contain a ConfigMap')
  data=obj.get('data',{})
  if any(not isinstance(v,str) for v in data.values()):raise ValueError('Cluster settings must be strings')
  values.update(data)
 return values

def substitute(text,variables=None):
 env=os.environ.copy();env.update(example_variables() if variables is None else variables)
 return subprocess.check_output([FLUX,'envsubst','--strict'],input=text,text=True,env=env)

def build(path,variables=None):
 text=subprocess.check_output([KUSTOMIZE,'build',str(path)],text=True)
 objects=[o for o in yaml.safe_load_all(text) if o]
 disabled=[o for o in objects if o.get('metadata',{}).get('annotations',{}).get('kustomize.toolkit.fluxcd.io/substitute')=='disabled']
 active=[o for o in objects if o not in disabled]
 rendered=substitute(yaml.dump_all(active,Dumper=LiteralDumper,sort_keys=False),variables) if active else ''
 return disabled+[o for o in yaml.safe_load_all(rendered) if o]

if __name__ == '__main__':
 import argparse
 parser=argparse.ArgumentParser(description='Run native Flux envsubst using non-secret cluster ConfigMap settings')
 parser.add_argument('--run',type=Path,required=True)
 parser.add_argument('--input',type=Path,required=True)
 args=parser.parse_args()
 print(substitute(args.input.read_text(),variables_for(args.run)),end='')
