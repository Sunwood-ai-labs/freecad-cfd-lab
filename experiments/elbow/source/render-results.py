"""Run with ParaView's pvpython.exe to reproduce the saved result images."""
from pathlib import Path
import json
import math
import paraview.simple as pv

root = Path(__file__).resolve().parent.parent
pv._DisableFirstRenderCameraReset()
reader = pv.OpenFOAMReader(FileName=str(root / 'case' / 'pv.foam'))
reader.CaseType = 'Reconstructed Case'
reader.MeshRegions = ['internalMesh']
reader.CellArrays = ['U', 'p']
reader.Createcelltopointfiltereddata = 1
reader.UpdatePipelineInformation()
last_time = float(reader.TimestepValues[-1])
reader.UpdatePipeline(last_time)
cell_count = reader.GetDataInformation().GetNumberOfCells()
scene = pv.GetAnimationScene()
scene.UpdateAnimationUsingDataTimeSteps()
scene.AnimationTime = last_time

section = pv.Slice(Input=reader)
section.SliceType = 'Plane'
section.SliceType.Origin = [32.0, 29.75, 2.5]
section.SliceType.Normal = [0.0, 0.0, 1.0]
section.UpdatePipeline(last_time)

# OpenFOAM's incompressible p is kinematic pressure. rho = 1.20 kg/m^3
# in the FreeCAD sample; multiplying by rho gives gauge pressure in Pa.
pressure = pv.Calculator(Input=section)
pressure.ResultArrayName = 'Pressure_Pa'
pressure.Function = '1.20*p'
pressure.UpdatePipeline(last_time)

view = pv.GetActiveViewOrCreate('RenderView')
view.ViewSize = [1400, 1100]
view.UseColorPaletteForBackground = 0
view.Background = [0.065, 0.085, 0.12]
view.OrientationAxesVisibility = 0
view.CameraParallelProjection = 1
view.CameraPosition = [32.0, 29.75, 200.0]
view.CameraFocalPoint = [32.0, 29.75, 2.5]
view.CameraViewUp = [0.0, 1.0, 0.0]
view.CameraParallelScale = 42.0
view.ViewTime = last_time

display = pv.Show(pressure, view)
display.Representation = 'Surface'
title = pv.Text()
title.Text = 'ELBOW FLOW | VELOCITY'
title_display = pv.Show(title, view)
title_display.WindowLocation = 'Upper Left Corner'
title_display.FontSize = 23
title_display.Color = [0.94, 0.96, 1.0]
caption = pv.Text()
caption.Text = f'FreeCAD + CfdOF + OpenFOAM | 2D steady laminar demo\n{cell_count:,} cells | final iteration {last_time:g} | demonstration only'
caption_display = pv.Show(caption, view)
caption_display.WindowLocation = 'Lower Left Corner'
caption_display.FontSize = 13
caption_display.Color = [0.75, 0.81, 0.89]

pv.ColorBy(display, ('POINTS', 'U', 'Magnitude'))
velocity_lut = pv.GetColorTransferFunction('U')
velocity_lut.ApplyPreset('Viridis', True)
display.RescaleTransferFunctionToDataRange(False, True)
display.SetScalarBarVisibility(view, True)
velocity_bar = pv.GetScalarBar(velocity_lut, view)
velocity_bar.Title = 'Speed [m/s]'
velocity_bar.ComponentTitle = ''
velocity_bar.TitleFontSize = 18
velocity_bar.LabelFontSize = 15
velocity_bar.TitleColor = [0.94, 0.96, 1.0]
velocity_bar.LabelColor = [0.94, 0.96, 1.0]
pv.Render(view)
pv.SaveScreenshot(str(root / 'velocity.png'), view, ImageResolution=[1400, 1100])
pv.SaveState(str(root / 'Elbow-velocity.pvsm'))

velocity_range = list(section.PointData.GetArray('U').GetRange(-1))
pressure_range = list(pressure.PointData.GetArray('Pressure_Pa').GetRange())
assert all(math.isfinite(v) for v in velocity_range + pressure_range)

display.SetScalarBarVisibility(view, False)
pv.ColorBy(display, ('POINTS', 'Pressure_Pa'))
pressure_lut = pv.GetColorTransferFunction('Pressure_Pa')
pressure_lut.ApplyPreset('Cool to Warm (Extended)', True)
display.RescaleTransferFunctionToDataRange(False, True)
display.SetScalarBarVisibility(view, True)
pressure_bar = pv.GetScalarBar(pressure_lut, view)
pressure_bar.Title = 'Gauge pressure [Pa]'
pressure_bar.ComponentTitle = ''
pressure_bar.TitleFontSize = 18
pressure_bar.LabelFontSize = 15
pressure_bar.TitleColor = [0.94, 0.96, 1.0]
pressure_bar.LabelColor = [0.94, 0.96, 1.0]
title.Text = 'ELBOW FLOW | PRESSURE'
pv.Render(view)
pv.SaveScreenshot(str(root / 'pressure.png'), view, ImageResolution=[1400, 1100])
summary = {
    'iteration': last_time,
    'cells': cell_count,
    'speed_point_range_m_per_s': velocity_range,
    'gauge_pressure_point_range_Pa': pressure_range,
    'density_kg_per_m3': 1.2,
    'pressure_conversion': 'p_Pa = rho * OpenFOAM_kinematic_p',
    'scope': 'Official CfdOF Elbow example; integration demonstration, not accuracy validation',
}
(root / 'result-summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps(summary))
