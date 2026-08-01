#!/usr/bin/env python3
"""Build PLC/HMI flash-media upgrade kits with a PySide6 interface."""

from __future__ import annotations

import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


SERIES = ("C-Series", "E-Series", "MCP")


@dataclass(frozen=True)
class BuildSelection:
    series: str
    zld: Path
    znx: Path


def write_hgauto(path: Path, series: str, znx_name: str) -> None:
    title = f"Upgrade {series} HMI"
    comment = f"{series} Heat Pump HMI Upgrade utility"
    text = (
        "[AUTORUN]\n"
        "item=1\n"
        "button_command=Enable\n"
        "button_runall=Disable\n"
        "language=European\n"
        "[COMMAND_1]\n"
        "command=PRO_DOWNLOAD\n"
        f'src_path="B:\\{znx_name}"\n'
        "reset_keep_device=Enable\n"
        "plc_run=Enable\n"
        f'title="{title}"\n'
        "[COMMENT]\n"
        f'comment="{comment}"\n'
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def write_autoexec(path: Path, zld_name: str) -> None:
    text = (
        "[COMMON_SETTING]\n"
        "loading_direction=download\n"
        "[PROGRAM_DOWNLOAD]\n"
        f'src_file="{zld_name}"\n'
        "onetime_upload=false\n"
        "auto_start=true\n"
        "keep_output=false\n"
        "clear_data=false\n"
        "clear_error=false\n"
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def recipe_models(root: Path, series: str) -> list[Path]:
    recipe_root = root / "ALLUNIT_RECIPES" / series
    if not recipe_root.is_dir():
        return []
    return sorted(
        (item for item in recipe_root.iterdir() if item.is_dir()),
        key=lambda item: item.name.casefold(),
    )


def validate_project(root: Path, selection: BuildSelection) -> list[Path]:
    errors = []
    models = recipe_models(root, selection.series)
    template = root / "templates" / f"{selection.series}-README-INSTRUCTIONS.pdf"
    if not models:
        errors.append(f"No model folders found for {selection.series}.")
    if not template.is_file():
        errors.append(f"Missing instruction file: {template}")
    if not selection.zld.is_file() or selection.zld.suffix.casefold() != ".zld":
        errors.append(f"Invalid PLC file for {selection.series}: {selection.zld}")
    if not selection.znx.is_file() or selection.znx.suffix.casefold() != ".znx":
        errors.append(f"Invalid HMI file for {selection.series}: {selection.znx}")
    if errors:
        raise ValueError("\n".join(errors))
    return models


def add_tree_to_zip(archive: zipfile.ZipFile, source: Path, archive_root: str) -> None:
    for item in sorted(source.rglob("*")):
        relative = item.relative_to(source)
        archive_name = Path(archive_root) / relative
        if item.is_dir():
            archive.writestr(archive_name.as_posix().rstrip("/") + "/", b"")
        else:
            archive.write(item, archive_name.as_posix())


def verify_kit(kit: Path, model: str, zld_name: str, znx_name: str) -> None:
    required = (
        kit / "README-INSTRUCTIONS.pdf",
        kit / "USB_Media" / znx_name,
        kit / "USB_Media" / "hgauto.ini",
        kit / "SD_CARD" / "FCDATA01" / "PROGRAM" / zld_name,
        kit / "SD_CARD" / "FCDATA01" / "autoexec.ini",
        kit / model,
    )
    missing = [str(path.relative_to(kit)) for path in required if not path.exists()]
    if missing:
        raise RuntimeError("Package validation failed; missing: " + ", ".join(missing))

    hgauto = (kit / "USB_Media" / "hgauto.ini").read_text(encoding="utf-8")
    autoexec = (kit / "SD_CARD" / "FCDATA01" / "autoexec.ini").read_text(
        encoding="utf-8"
    )
    if f'B:\\{znx_name}' not in hgauto:
        raise RuntimeError(f"hgauto.ini does not reference {znx_name}")
    if f'src_file="{zld_name}"' not in autoexec:
        raise RuntimeError(f"autoexec.ini does not reference {zld_name}")


def build_series(root: Path, selection: BuildSelection, replace: bool = False) -> list[Path]:
    models = validate_project(root, selection)
    output = root / f"{selection.series}-OUTPUT"
    template = root / "templates" / f"{selection.series}-README-INSTRUCTIONS.pdf"
    output.mkdir(parents=True, exist_ok=True)
    results = []

    for recipe in models:
        kit_name = f"{recipe.name}_upgrade_kit"
        final_kit = output / kit_name
        final_zip = output / f"{kit_name}.zip"
        if (final_kit.exists() or final_zip.exists()) and not replace:
            raise FileExistsError(f"Output already exists for {selection.series}: {kit_name}")

        with tempfile.TemporaryDirectory(prefix="flash-kit-", dir=output) as temp_name:
            temp_root = Path(temp_name)
            kit = temp_root / kit_name
            usb = kit / "USB_Media"
            program = kit / "SD_CARD" / "FCDATA01" / "PROGRAM"
            usb.mkdir(parents=True)
            program.mkdir(parents=True)

            shutil.copy2(template, kit / "README-INSTRUCTIONS.pdf")
            shutil.copy2(selection.znx, usb / selection.znx.name)
            shutil.copy2(selection.zld, program / selection.zld.name)
            shutil.copytree(recipe, kit / recipe.name)
            write_hgauto(usb / "hgauto.ini", selection.series, selection.znx.name)
            write_autoexec(program.parent / "autoexec.ini", selection.zld.name)
            verify_kit(kit, recipe.name, selection.zld.name, selection.znx.name)

            temp_zip = temp_root / f"{kit_name}.zip"
            with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as archive:
                add_tree_to_zip(archive, kit, kit_name)

            with zipfile.ZipFile(temp_zip, "r") as archive:
                bad_file = archive.testzip()
                if bad_file:
                    raise RuntimeError(f"ZIP validation failed at {bad_file}")

            if replace:
                if final_kit.is_dir():
                    shutil.rmtree(final_kit)
                elif final_kit.exists():
                    final_kit.unlink()
                if final_zip.exists():
                    final_zip.unlink()
            shutil.move(str(kit), final_kit)
            shutil.move(str(temp_zip), final_zip)
            results.append(final_zip)
    return results


class SeriesRow:
    def __init__(self, series: str, changed) -> None:
        self.series = series
        self.enabled = QCheckBox(series)
        self.enabled.toggled.connect(changed)
        self.zld = QComboBox()
        self.znx = QComboBox()
        self.zld.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.znx.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.zld_browse = QPushButton("Browse...")
        self.znx_browse = QPushButton("Browse...")
        self.models = QLabel("0 models")

    def set_active(self, active: bool) -> None:
        for widget in (self.zld, self.znx, self.zld_browse, self.znx_browse):
            widget.setEnabled(active)

    @staticmethod
    def selected_path(combo: QComboBox) -> Path:
        data = combo.currentData()
        return Path(data) if data else Path()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Flash Media Upgrade Kit Builder")
        self.resize(980, 680)

        self.root_edit = QComboBox()
        self.root_edit.setEditable(True)
        self.root_edit.addItem(str(Path.cwd()), str(Path.cwd()))
        self.root_button = QPushButton("Select project root...")
        self.source_edit = QComboBox()
        self.source_edit.setEditable(True)
        self.source_edit.addItem(str(Path.cwd()), str(Path.cwd()))
        self.source_button = QPushButton("Select release files folder...")
        self.scan_button = QPushButton("Rescan")
        self.replace = QCheckBox("Replace existing packages")
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.build_button = QPushButton("Generate selected packages")

        paths = QFormLayout()
        root_line = QHBoxLayout()
        root_line.addWidget(self.root_edit, 1)
        root_line.addWidget(self.root_button)
        paths.addRow("Project root:", root_line)
        source_line = QHBoxLayout()
        source_line.addWidget(self.source_edit, 1)
        source_line.addWidget(self.source_button)
        source_line.addWidget(self.scan_button)
        paths.addRow("Release files:", source_line)

        group = QGroupBox("Packages")
        grid = QGridLayout(group)
        grid.addWidget(QLabel("Code base"), 0, 0)
        grid.addWidget(QLabel("PLC program (.zld)"), 0, 1)
        grid.addWidget(QLabel("HMI project (.ZNX)"), 0, 3)
        grid.addWidget(QLabel("Models"), 0, 5)
        self.rows = {}
        for number, series in enumerate(SERIES, 1):
            row = SeriesRow(series, self.update_state)
            self.rows[series] = row
            grid.addWidget(row.enabled, number, 0)
            grid.addWidget(row.zld, number, 1)
            grid.addWidget(row.zld_browse, number, 2)
            grid.addWidget(row.znx, number, 3)
            grid.addWidget(row.znx_browse, number, 4)
            grid.addWidget(row.models, number, 5)
            row.zld_browse.clicked.connect(
                lambda checked=False, r=row: self.select_file(r.zld, "PLC programs (*.zld)")
            )
            row.znx_browse.clicked.connect(
                lambda checked=False, r=row: self.select_file(r.znx, "HMI projects (*.ZNX *.znx)")
            )

        bottom = QHBoxLayout()
        bottom.addWidget(self.replace)
        bottom.addStretch()
        bottom.addWidget(self.build_button)
        layout = QVBoxLayout()
        layout.addLayout(paths)
        layout.addWidget(group)
        layout.addWidget(QLabel("Build log:"))
        layout.addWidget(self.log, 1)
        layout.addLayout(bottom)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.root_button.clicked.connect(self.select_root)
        self.source_button.clicked.connect(self.select_source)
        self.scan_button.clicked.connect(self.scan)
        self.build_button.clicked.connect(self.build)
        self.root_edit.currentTextChanged.connect(self.refresh_models)
        self.scan()
        self.update_state()

    def project_root(self) -> Path:
        return Path(self.root_edit.currentText()).expanduser().resolve()

    def source_root(self) -> Path:
        return Path(self.source_edit.currentText()).expanduser().resolve()

    def select_root(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Select FMU project root")
        if chosen:
            self.root_edit.setEditText(chosen)
            self.source_edit.setEditText(chosen)
            self.scan()

    def select_source(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Select release files folder")
        if chosen:
            self.source_edit.setEditText(chosen)
            self.scan()

    def select_file(self, combo: QComboBox, file_filter: str) -> None:
        chosen, unused = QFileDialog.getOpenFileName(
            self, "Select release file", str(self.source_root()), file_filter
        )
        if chosen:
            self.add_and_select(combo, Path(chosen))

    @staticmethod
    def add_and_select(combo: QComboBox, path: Path) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == str(path):
                combo.setCurrentIndex(index)
                return
        combo.addItem(path.name, str(path))
        combo.setCurrentIndex(combo.count() - 1)

    def scan(self) -> None:
        source = self.source_root()
        zlds = []
        znxs = []
        if source.is_dir():
            for path in source.iterdir():
                if path.is_file() and path.suffix.casefold() == ".zld":
                    zlds.append(path.resolve())
                elif path.is_file() and path.suffix.casefold() == ".znx":
                    znxs.append(path.resolve())
        for row in self.rows.values():
            current_zld = row.zld.currentData()
            current_znx = row.znx.currentData()
            row.zld.clear()
            row.znx.clear()
            for path in sorted(zlds, key=lambda item: item.name.casefold()):
                row.zld.addItem(path.name, str(path))
            for path in sorted(znxs, key=lambda item: item.name.casefold()):
                row.znx.addItem(path.name, str(path))
            for combo, old in ((row.zld, current_zld), (row.znx, current_znx)):
                if old:
                    index = combo.findData(old)
                    if index >= 0:
                        combo.setCurrentIndex(index)
        self.refresh_models()
        self.log.appendPlainText(
            f"Scanned {source}: {len(zlds)} PLC file(s), {len(znxs)} HMI file(s)."
        )

    def refresh_models(self) -> None:
        root = self.project_root()
        for series, row in self.rows.items():
            models = recipe_models(root, series)
            row.models.setText(f"{len(models)}: " + ", ".join(item.name for item in models))

    def update_state(self) -> None:
        selected = False
        for row in self.rows.values():
            row.set_active(row.enabled.isChecked())
            selected = selected or row.enabled.isChecked()
        self.build_button.setEnabled(selected)

    def selections(self) -> list[BuildSelection]:
        selections = []
        for series, row in self.rows.items():
            if row.enabled.isChecked():
                selections.append(
                    BuildSelection(
                        series=series,
                        zld=row.selected_path(row.zld),
                        znx=row.selected_path(row.znx),
                    )
                )
        return selections

    def build(self) -> None:
        root = self.project_root()
        selections = self.selections()
        try:
            counts = []
            for selection in selections:
                models = validate_project(root, selection)
                counts.append(f"{selection.series}: {len(models)} package(s)")
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, "Cannot generate packages", str(error))
            return

        summary = "\n".join(counts)
        answer = QMessageBox.question(
            self,
            "Generate packages?",
            f"{summary}\n\nOutput will be written below:\n{root}",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.build_button.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            total = 0
            for selection in selections:
                self.log.appendPlainText(f"Building {selection.series}...")
                QApplication.processEvents()
                archives = build_series(root, selection, self.replace.isChecked())
                total += len(archives)
                for archive in archives:
                    self.log.appendPlainText(f"Created: {archive}")
            QMessageBox.information(
                self, "Packages complete", f"Created and verified {total} package(s)."
            )
        except Exception as error:
            self.log.appendPlainText(f"ERROR: {error}")
            QMessageBox.critical(self, "Build failed", str(error))
        finally:
            QApplication.restoreOverrideCursor()
            self.update_state()


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
