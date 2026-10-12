"""Build local por sistema operacional; não publica, não instala e não acessa a placa."""

import ast
import json
import shutil
import subprocess
import sys
import zipfile
from importlib.metadata import distribution
from pathlib import Path


def collect_system_notices(destination: Path, root: Path) -> None:
    if sys.platform != "linux":
        return
    if shutil.which("dpkg-query") is None:
        raise SystemExit(
            "A receita Linux usa Ubuntu/dpkg para coletar avisos das bibliotecas nativas."
        )
    table = ast.literal_eval(
        (root / "build/pyinstaller/MuscleMonitor/Analysis-00.toc").read_text(encoding="utf-8")
    )
    system_paths = set()

    def find_binaries(value):
        if not isinstance(value, (list, tuple)):
            return
        if (
            len(value) == 3
            and isinstance(value[1], str)
            and value[2] == "BINARY"
            and value[1].startswith(("/usr/lib/", "/lib/"))
        ):
            system_paths.add(value[1])
        for item in value:
            find_binaries(item)

    find_binaries(table)
    manifest = {}
    for name in sorted(system_paths):
        found = subprocess.run(
            ["dpkg-query", "-S", "*/" + Path(name).name],
            capture_output=True,
            text=True,
            check=False,
        )
        owners = set()
        for row in found.stdout.splitlines():
            if ": " not in row:
                continue
            package = row.split(": ", 1)[0].split(":", 1)[0]
            notice = Path("/usr/share/doc") / package / "copyright"
            if notice.is_file():
                target = destination / "system" / package / "copyright"
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(notice, target)
                owners.add(package)
        if not owners:
            raise SystemExit(f"Aviso da biblioteca nativa não encontrado: {name}")
        manifest[Path(name).name] = sorted(owners)
    common = Path("/usr/share/common-licenses")
    if common.is_dir():
        shutil.copytree(common, destination / "system/common-licenses", dirs_exist_ok=True)
    (destination / "system-libraries.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


def collect_licenses(destination: Path, root: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name in (
        "PySide6-Essentials",
        "shiboken6",
        "numpy",
        "pyqtgraph",
        "pyserial",
        "colorama",
        "pyinstaller",
    ):
        package = distribution(name)
        manifest[name] = package.version
        for path in package.files or ():
            if not any(word in str(path).lower() for word in ("license", "copying", "copyright")):
                continue
            source = Path(package.locate_file(path))
            if source.is_file():
                # Paths are distribution-relative; never reproduce ../ entries outside notices.
                relative = Path(*[p for p in path.parts if p not in ("..", ".")])
                target = destination / name / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
    (destination / "versions.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (destination / "PYTHON-LICENSE.txt").write_text(license_text(), encoding="utf-8")
    archive = root / "third_party/upstream-notices.zip"
    with zipfile.ZipFile(archive) as notices:
        for item in notices.infolist():
            target = (destination / "upstream" / item.filename).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError("Caminho de licença fora do diretório esperado")
            notices.extract(item, destination / "upstream")
    shutil.copyfile(root / "third_party/README.md", destination / "UPSTREAM-SOURCES.md")


def license_text() -> str:
    # Python's installed license printer knows platform-specific license locations.
    import builtins

    printer = builtins.license
    printer._Printer__setup()
    return "\n".join(printer._Printer__lines) + "\n"


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    if sys.version_info[:2] != (3, 12):
        raise SystemExit("Use Python 3.12 para gerar este pacote.")
    if not (root / "third_party/upstream-notices.zip").exists():
        raise SystemExit("Arquivo de avisos upstream ausente; build não pode ser distribuído.")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onedir",
            "--windowed",
            "--noupx",
            "--name",
            "MuscleMonitor",
            "--paths",
            str(root / "src"),
            "--distpath",
            str(root / "dist"),
            "--workpath",
            str(root / "build/pyinstaller"),
            "--specpath",
            str(root / "build"),
            "--exclude-module",
            "PyQt5",
            "--exclude-module",
            "PyQt6",
            "--exclude-module",
            "PySide2",
            "--exclude-module",
            "pytest",
            "--exclude-module",
            "_pytest",
            "--exclude-module",
            "psutil",
            "--exclude-module",
            "mypy",
            "--exclude-module",
            "ruff",
            "--exclude-module",
            "pip",
            "--exclude-module",
            "setuptools",
            "--exclude-module",
            "numpy.testing",
            "--exclude-module",
            "numpy.f2py",
            "--exclude-module",
            "PySide6.QtTest",
            "--exclude-module",
            "readline",
            str(root / "scripts/entrypoint.py"),
        ],
        cwd=root,
        check=True,
    )
    target = root / "dist/MuscleMonitor"
    collect_licenses(target / "_internal/licenses", root)
    collect_system_notices(target / "_internal/licenses", root)
    shutil.copyfile(root / "README.md", target / "README.md")
    shutil.copytree(root / "docs", target / "docs", dirs_exist_ok=True)
    print(f"Pacote local pronto em {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
