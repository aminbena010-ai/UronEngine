"""Sistema de dibujo inmediato (HUD y debug) para los scripts."""

class _Draw:
    def __init__(self):
        self._queue = []

    def _add(self, kind, args, kwargs):
        self._queue.append((kind, args, kwargs))

    def clear(self):
        self._queue.clear()

    def consume(self):
        queue = self._queue
        self._queue = []
        return queue

    def rect(self, x, y, w, h, color="#ffffff", fill=True, width=2, screen=False, rotation=0.0):
        self._add("rect", (x, y, w, h), {
            "color": color, "fill": fill, "width": width,
            "screen": screen, "rotation": rotation})

    def circle(self, x, y, radius, color="#ffffff", fill=True, width=2, screen=False, segments=32):
        self._add("circle", (x, y, radius), {
            "color": color, "fill": fill, "width": width,
            "screen": screen, "segments": segments})

    def line(self, x1, y1, x2, y2, color="#ffffff", width=2, screen=False):
        self._add("line", (x1, y1, x2, y2), {
            "color": color, "width": width, "screen": screen})

    def text(self, text, x, y, size=18, color="#ffffff", screen=True, align="left"):
        self._add("text", (str(text), x, y), {
            "size": size, "color": color, "screen": screen, "align": align})

draw = _Draw()