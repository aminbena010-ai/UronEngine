"""Lógica de la consola (filtros)."""
def filter_lines(lines, text):
    if not text: return list(lines)
    t = text.lower()
    return [l for l in lines if t in l.lower()]