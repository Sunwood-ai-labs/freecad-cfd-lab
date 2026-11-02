from pathlib import Path
import json
import FreeCAD as App
OUT=Path(__file__).resolve().parent.parent
doc=next(d for d in App.listDocuments().values() if d.FileName.replace('\\','/').endswith('family-house-airflow/Family-House-CFD.FCStd'))
solver=doc.getObject('Solver') or next(o for o in doc.Objects if 'ParallelCores' in o.PropertiesList)
num=json.loads((OUT/'setup.json').read_text(encoding='utf-8'))['numerics']
solver.Parallel=True;solver.ParallelCores=8;solver.PurgeWrite=num.get('purge_write',3);solver.SteadyWriteInterval=num.get('write_interval',100)
solver.URelaxation=num['relaxation_U'];solver.pRelaxation=num['relaxation_p'];solver.TurbulenceRelaxation=num['relaxation_turbulence']
if 'VelocityAdvectionOverride' not in solver.PropertiesList: solver.addProperty('App::PropertyString','VelocityAdvectionOverride','CFDReproduction')
solver.VelocityAdvectionOverride='bounded Gauss upwind (first order; applied by source/prepare scripts)'
if 'NonOrthogonalCorrectorsOverride' not in solver.PropertiesList: solver.addProperty('App::PropertyInteger','NonOrthogonalCorrectorsOverride','CFDReproduction')
solver.NonOrthogonalCorrectorsOverride=1
analysis=doc.getObject('CfdAnalysis')
for name in ['NeedsMeshRewrite','NeedsMeshRerun','NeedsCaseRewrite']:
    if name in analysis.PropertiesList:setattr(analysis,name,False)
doc.recompute();doc.save()
valid={o.Name:o.Shape.isValid() for o in doc.Objects if hasattr(o,'Shape') and not o.Shape.isNull()}
result={'native_file':str(OUT/'Family-House-CFD.FCStd'),'valid_shapes':valid,'all_shapes_valid':all(valid.values()),'air_solids':len(doc.AirDomain.Shape.Solids),'air_volume_m3':doc.AirDomain.Shape.Volume/1e9,'solver_parallel_cores':solver.ParallelCores,'note':'OpenFOAM case uses first-order and nonorthogonal overrides. GUI case rewriting without source scripts resets those template values.'}
(OUT/'native-cfd-validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
