"""Estado de la vista de escena (sin dependencias de Qt)."""

class ViewState:
    def __init__(self):
        self.scene_model = None
        self.selected_ids = []
        self.grid_size = 32
        self.show_grid = True
        self.snap_enabled = False
        self.snap_size = 32

    def set_scene_model(self, scene_model):
        self.scene_model = scene_model

    def set_selected(self, ids):
        self.selected_ids = list(ids or [])

    def current_id(self):
        return self.selected_ids[0] if self.selected_ids else None