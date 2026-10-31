"""Panel Project: árbol de archivos y rejilla de assets (estilo Unity/Godot)."""
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QFileDialog, QTabWidget, QListView, QLabel,
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QSize, QMimeData
from PyQt6.QtGui import QIcon, QPixmap, QStandardItemModel, QStandardItem, QDrag

from IDE.ui.proyect.config import HIDDEN_ENTRIES, IMAGE_EXT, ICON_SIZE
from IDE.ui.proyect.logic import rename_file, move_file, delete_file, list_dir
from IDE.ui.proyect.mod import ProjectState

# --- Widget de Árbol para arrastrar archivos ---
class AssetTree(QTreeWidget):
    def startDrag(self, supported_actions):
        items = self.selectedItems()
        if not items:
            return
        path = items[0].data(0, Qt.ItemDataRole.UserRole)
        if not path or not os.path.isfile(path):
            return
        drag = QDrag(self)
        data = QMimeData()
        data.setUrls([QUrl.fromLocalFile(path)])
        drag.setMimeData(data)
        drag.exec(Qt.DropAction.CopyAction)


class ProjectPanel(QWidget):
    # Señales que envía al MainWindow
    sceneRequested = pyqtSignal(str)   # Para abrir una escena al hacer doble clic
    assetRequested = pyqtSignal(str)   # Para usar un sprite al hacer doble clic
    assetsImported = pyqtSignal()      # Cuando se importa un asset

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.state = ProjectState(project)
        self._icons = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Barra de botones superior
        bar = QHBoxLayout()
        bar.setContentsMargins(4, 4, 4, 0)
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.reload)
        btn_import = QPushButton("Import Asset…")
        btn_import.clicked.connect(self._import_sprite)
        bar.addWidget(btn_refresh)
        bar.addWidget(btn_import)
        bar.addStretch()
        layout.addLayout(bar)

        # Pestañas (Árbol vs Rejilla)
        self.tabs = QTabWidget()
        
        # 1. Pestaña Árbol (Archivos)
        self.tree = AssetTree()
        self.tree.setHeaderHidden(True)
        self.tree.setIconSize(QSize(20, 20))
        self.tree.itemDoubleClicked.connect(self._on_tree_click)
        self.tabs.addTab(self.tree, "Hierarchy")
        
        # 2. Pestaña Rejilla (Assets/Sprites)
        self.grid = QListView()
        self.grid.setViewMode(QListView.ViewMode.IconMode)
        self.grid.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.grid.setSpacing(10)
        self.grid.setResizeMode(QListView.ResizeMode.Adjust)
        self.grid.setMovement(QListView.Movement.Static)
        self.grid.setUniformItemSizes(True)
        self.grid.doubleClicked.connect(self._on_grid_click)
        self.tabs.addTab(self.grid, "Assets")

        layout.addWidget(self.tabs)
        
        # Cargar contenido inicial
        self.reload()

    def reload(self):
        """Reconstruye el árbol y la rejilla desde el disco."""
        self.tree.clear()
        self._icons.clear()

        # --- 1. Llenar el Árbol ---
        root = QTreeWidgetItem([self.project.name])
        root.setData(0, Qt.ItemDataRole.UserRole, self.project.folder)
        self.tree.addTopLevelItem(root)
        self._populate_tree(root, self.project.folder)

        # --- 2. Llenar la Rejilla de Assets ---
        model = QStandardItemModel()
        sprites_dir = self.project.sprites_dir()
        if os.path.isdir(sprites_dir):
            for name in sorted(os.listdir(sprites_dir)):
                if name.lower().endswith(IMAGE_EXT):
                    full_path = os.path.join(sprites_dir, name)
                    pm = QPixmap(full_path)
                    if not pm.isNull():
                        icon = QIcon(pm.scaled(ICON_SIZE, ICON_SIZE, 
                                     Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation))
                        item = QStandardItem(icon, name)
                        item.setData(full_path, Qt.ItemDataRole.UserRole)
                        item.setEditable(False)
                        model.appendRow(item)
        self.grid.setModel(model)

    def _populate_tree(self, parent_item, folder):
        for name in list_dir(folder, HIDDEN_ENTRIES):
            full = os.path.join(folder, name)
            child = QTreeWidgetItem([name])
            child.setData(0, Qt.ItemDataRole.UserRole, full)
            
            # Asignar icono según extensión
            if os.path.isdir(full):
                child.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_DirIcon))
                parent_item.addChild(child)
                self._populate_tree(child, full)
            else:
                if name.lower().endswith(IMAGE_EXT):
                    child.setIcon(0, QIcon(full)) # Qt cargará la imagen
                elif name.endswith(".uron.json") or name.endswith(".uron.prefab"):
                    child.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_FileIcon))
                parent_item.addChild(child)

    def _on_tree_click(self, item, col):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not path or not os.path.isfile(path):
            return
        
        if self.state.is_scene(path):
            self.sceneRequested.emit(path)
        elif self.state.is_image(path):
            self.assetRequested.emit(path)

    def _on_grid_click(self, index):
        path = index.data(Qt.ItemDataRole.UserRole)
        if path and self.state.is_image(path):
            self.assetRequested.emit(path)

    def _import_sprite(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Sprite", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if not path:
            return
        try:
            self.project.import_asset(path, "sprites")
            self.reload()
            self.assetsImported.emit()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Import Error", str(e))