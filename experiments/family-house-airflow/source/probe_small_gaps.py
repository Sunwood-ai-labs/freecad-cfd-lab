from pathlib import Path
import argparse
import json
import vtk

ROOT=Path(__file__).resolve().parents[3]
parser=argparse.ArgumentParser();parser.add_argument('--case',type=Path,default=ROOT/'experiments/family-house-airflow/case');args=parser.parse_args()
reader=vtk.vtkOpenFOAMReader()
reader.SetFileName(str(args.case/'pv.foam'))
reader.UpdateInformation();reader.DisableAllCellArrays();reader.DisableAllPatchArrays()
reader.SetPatchArrayStatus('internalMesh',1);reader.Update()
grid=reader.GetOutput().GetBlock(0)
assert grid is not None and grid.GetNumberOfCells()>0, 'No mesh loaded; no point result can be interpreted'
locator=vtk.vtkStaticCellLocator();locator.SetDataSet(grid);locator.BuildLocator()
points={
    'washer_west_150mm_gap':[2.275,8.55,1.5],
    'washer_west_150mm_gap_low':[2.275,8.55,.9],
    'washer_south_air':[2.675,8.1,1.5],
    'dryer_top_air':[2.675,8.55,2.5],
    'linen_top_air':[3.25,5.55,2.55],
    'linen_north_aisle':[3.25,5.9,1.5],
    'wc_basin_south_50mm_gap':[4.525,5.325,.85],
    'wc_toilet_north_50mm_gap':[4.9,7.075,.95],
    'wc_toilet_east_air':[5.2,6.7,.95],
}
result={name:{'point_m':p,'fluid':bool(locator.FindCell(p)>=0)} for name,p in points.items()}
print(json.dumps(result,indent=2))
Path(__file__).with_name('small-gap-probes.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
