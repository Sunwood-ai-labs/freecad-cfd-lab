# Windows environment and runtime

[日本語の構築メモ](#windowsでの構築メモ) · [Repository home](../README.md)

This lab was run on Windows with FreeCAD 1.1.4, CfdOF commit
`a90f60c2313ceba09c236c81f0693d93357d1614` plus the supplied Qt6 patch,
ParaView 6.1.0, and a Linux OpenFOAM runtime in Podman/WSL.
The runtime contains OpenFOAM 2306, cfMesh-CfdOF 1.32, HiSA 1.13.4,
and Gmsh 4.15.2. Python helpers use `uv`; FreeCAD macros run inside
FreeCAD, and VTK renderers use ParaView's `pvpython.exe`.

## What the evidence covers

- [`original-runtime-verified.json`](../runtime/original-runtime-verified.json)
  records the original image's version/help checks on 2026-10-31.
- [`publication-runtime-verified.json`](../runtime/publication-runtime-verified.json)
  records a fresh check of that existing image on 2026-11-02.
- The base image's recorded digest was checked against the local Podman
  image store on 2026-11-02 and is pinned in the public `Containerfile`.
- The original build was interrupted; a resume recipe using 237 saved
  compilation objects finished with exit code 0. That machine-specific
  cache and its intermediate image are not distributed.
- **The public clean-build recipe has not been run end to end.** It is
  derived from the original recipe, with a pinned base and verified download
  manifest. A clean machine installation, dependency downloads, and a fresh
  rebuild remain unverified. The base digest pins the image, but subsequent
  `apt-get` packages are not a historical snapshot.

The current Windows Podman socket was unavailable during publication.
Direct `wsl.exe -d podman-machine-default -u root -- podman ...` access
worked, so the scripts use that route by default. This does not prove the
CfdOF GUI's Windows container connection works on another machine.

## Windows setup

1. Install [FreeCAD](https://www.freecad.org/),
   [Podman](https://podman.io/), [ParaView](https://www.paraview.org/),
   [uv](https://docs.astral.sh/uv/), and FFmpeg if rendering videos.
   Set up WSL and a Podman machine using those tools' instructions.
2. Install [CfdOF](https://github.com/jaheyns/CfdOF). The experiment's
   exact source revision is linked above; current versions may behave
   differently. Also use the CfdOF-required FreeCAD dependencies such as
   CfdOF's Plot support. The experiment used FreeCAD's built-in Plot and
   disabled a separate external Plot addon that conflicted with Qt6.
3. For that recorded revision on Qt6, review and apply
   [`CfdOF-Qt6-compatibility.patch`](../experiments/elbow/CfdOF-Qt6-compatibility.patch)
   to the installed CfdOF source. Run `git apply --check` before `git apply`
   from its repository root. The patch changes QProcess argument handling
   for Podman and uses a container-visible folder during dependency checks.
   Do not apply blindly to newer CfdOF revisions. Updating the addon may
   replace the patch.
4. Obtain/build the runtime below. In CfdOF preferences select the container
   runtime and ParaView executable, and choose your own writable output
   directory. Run CfdOF's dependency check. No local preferences or recovery
   files from the original machine are imported by this repository.
5. Open an experiment's `.FCStd` file. The final 3D case was run through WSL
   rather than relying on the GUI's container connection. Read the experiment
   notes before attempting any rerun: output directories are replaced, and
   CfdOF regeneration may overwrite the tuned OpenFOAM dictionaries.

## Download and build

Run from the repository root in PowerShell:

```powershell
.\runtime\Get-Dependencies.ps1
.\runtime\Build-Runtime.ps1 -Image localhost/freecad-cfd-lab:rebuild
.\runtime\Verify-Runtime.ps1 -Image localhost/freecad-cfd-lab:rebuild
```

`Get-Dependencies.ps1` checks each archive's SHA256 and size against
[`archive-manifest.json`](../runtime/archive-manifest.json). The SourceForge
`master` URLs are rolling downloads. If they change, verification fails;
do not silently replace the recorded hashes. Archives are downloaded locally
and are not committed to this repository.

The default WSL distribution is `podman-machine-default`. Override it with
`-WslDistribution YourDistribution` on build/verify. Use
`-WslDistribution ''` to call a working Windows `podman` CLI directly.
The build uses a separate default image tag, `localhost/freecad-cfd-lab:rebuild`.
Pass the image tag expected by your local scripts or adjust their image
parameter where supported; the original experiment tag is
`localhost/cfdof-openfoam:verified-20261030`.

The verification script starts disposable containers without network access
and checks executable versions and `-help`. It does not run CFD or prove
numerical equivalence of a rebuilt image. It writes local results under
`runtime/logs/`.

## Windowsでの構築メモ

確認済みの元環境は FreeCAD 1.1.4／CfdOF の上記コミット＋Qt6互換パッチ／
ParaView 6.1.0、WSL 内 Podman の OpenFOAM 2306 です。cfMesh-CfdOF 1.32、
HiSA 1.13.4、Gmsh 4.15.2 の版番号と help 起動は、公開準備時にも既存イメージで
確認しました。Windows 側の Podman ソケット接続は失敗したため、WSL から直接実行しています。

公開したビルド手順は**新規環境で全通し未検証**です。元実験では初回ビルドの中断後、
保存したコンパイル途中のデータから再開して完成しました。公開版にはそのキャッシュを含めず、
元レシピ・実体確認したベース digest・公式配布URLとSHA256を収録しています。

上の PowerShell コマンドは、依存アーカイブ取得→ビルド→版番号/help確認の順です。
ダウンロード内容が元実験のハッシュと異なれば停止します。最新版へ置き換えて同じ実験を
再現したことにはできません。初回取得、新規ビルド、他PCへの導入は未確認です。

FreeCAD の設定は自分の出力先・ParaView・コンテナ環境に合わせてください。
互換パッチは記録した CfdOF 用です。新しい版へ適用する際は差分を確認します。
3D の最終ケースは WSL 経由で実行しており、GUI でのケース再出力・再実行や
最終補助ラッパーの全通しは未検証です。再出力で独自の数値設定が変わる可能性があります。

## Upstream components and licenses

The repository supplies recipes and experiment artifacts, not bundled
third-party source archives or a container image. Each downloaded component
retains its own license. CfdOF and its derived compatibility patch use
LGPL-3.0; see the repository's third-party notices for attribution. Consult
the upstream sources for OpenFOAM, cfMesh-CfdOF, HiSA, Gmsh, FreeCAD,
ParaView, and the base image before redistributing their binaries.
