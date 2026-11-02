# Third-party notices

The MIT license at the repository root covers original project code, documentation,
models and visualizations, subject to the exceptions below. Upstream tools and
derived assets retain their respective licenses. This project is independent of
the FreeCAD, CfdOF, OpenFOAM and ParaView projects.

## CfdOF demo and compatibility patch

The Elbow experiment is based on the official CfdOF Elbow demonstration.
The Qt6 compatibility patch modifies CfdOF code; it is not relicensed under MIT.

- Upstream: <https://github.com/jaheyns/CfdOF>
- Recorded source commit: `a90f60c2313ceba09c236c81f0693d93357d1614`
- License: GNU Lesser General Public License v3.0; see
  [the bundled upstream license](experiments/elbow/LICENSE.CfdOF).
- Scope: upstream-derived Elbow model/demo material and
  `experiments/elbow/CfdOF-Qt6-compatibility.patch`.
- Modified files and local adaptations are recorded in the packaging manifest.

Generated CfdOF/OpenFOAM case headers may contain upstream copyright/license
notices. Those notices remain applicable to those files, including release data.

## External runtime

FreeCAD, CfdOF, OpenFOAM, cfMesh, HiSA, Gmsh, ParaView/VTK and FFmpeg are
external dependencies. Their binaries and source distributions are not vendored
in this repository. Follow each upstream license when obtaining or redistributing
them. Runtime download sources and checksums are recorded in `runtime/`.

Screenshots show the tools used in the experiment. Their interface artwork and
trademarks remain the property of their respective owners. Windows fonts are
referenced by the original renderers and are not redistributed.
