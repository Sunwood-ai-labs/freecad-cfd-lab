"""Open the saved velocity visualization in the ParaView GUI."""
from pathlib import Path
root = Path(__file__).resolve().parent.parent
(root / 'paraview-gui-started.txt').write_text(str(root), encoding='utf-8')
try:
    from paraview.simple import LoadState, GetActiveView, Render
    LoadState(str(root / 'Elbow-velocity.pvsm'))
    Render(GetActiveView())
    (root / 'paraview-gui-loaded.txt').write_text(
        'ParaView GUI loaded Elbow-velocity.pvsm and completed Render().\n',
        encoding='utf-8',
    )
except Exception:
    import traceback
    (root / 'paraview-gui-error.txt').write_text(traceback.format_exc(), encoding='utf-8')
    raise
