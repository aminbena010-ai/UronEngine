# 🚀 URON Engine

**URON Engine** es un motor de desarrollo de videojuegos 2D completo, escrito en **Python** y diseñado con una arquitectura modular y limpia. Incluye su propio **IDE visual** (inspirado en Unity/Godot) y un **Runtime** basado en Pygame y OpenGL.

---

## ✨ Características

- 🎨 **IDE Visual**: Editor de escenas con jerarquía, inspector, panel de proyecto y consola.
- 🧩 **Sistema ECS**: Componentes modulares (`Transform`, `SpriteRenderer`, `RigidBody`, etc.).
- 🕹️ **Scripting**: Crea comportamientos personalizados en Python heredando de `UronScript`.
- ⚡ **Física 2D**: Colisiones AABB/OBB, círculos, triggers y raycasts.
- 🎥 **Cámara 2D**: Seguimiento suave de objetivos y transiciones.
- 📦 **Empaquetado**: Exporta tu juego a un único ejecutable con PyInstaller.
- 🖥️ **UI Moderna**: Tema oscuro, gizmos de transformación y drag & drop.

---

## 📂 Estructura del Proyecto

```text
UronEngine/
├── IDE/               # El editor visual (PyQt6)
│   ├── logic/         # Lógica del editor (Undo/Redo, herramientas)
│   └── ui/            # Paneles (Hierarchy, Inspector, View, etc.)
├── runtime/           # El motor de ejecución (Pygame + OpenGL)
├── uron/              # El núcleo del motor
│   ├── api/           # API para scripts (Input, Audio, Draw)
│   ├── build/         # Empaquetador (PyInstaller)
│   ├── core/          # Componentes, escenas, física, proyecto
│   ├── math/          # Vectores y utilidades matemáticas
│   └── render/        # Cámara y proyecciones
├── script/            # Scripts de instalación y automatización
├── main.py            # Punto de entrada del IDE
├── init.sh            # Arranca el IDE
└── requirements.txt   # Dependencias del sistema
```

---

## 🛠️ Requisitos

- **Python 3.10+**
- **uv** (gestor de paquetes y entornos ultrarrápido)
- **Linux** (probado en Ubuntu/Debian; también funciona en Windows/Mac con ajustes mínimos).

---

## 🚀 Instalación

1. **Clona el repositorio:**
   ```bash
   git clone https://github.com/tu-usuario/UronEngine.git
   cd UronEngine
   ```

2. **Ejecuta el script de instalación:**
   ```bash
   ./script/install.sh
   ```
   *(Este script crea el entorno virtual con `uv` e instala todas las dependencias del `requirements.txt`).*

---

## 🎮 Uso

### Iniciar el IDE
```bash
./init.sh
```

### Crear un proyecto nuevo
1. Abre el IDE.
2. Haz clic en **"New Project"**.
3. Elige una carpeta y un nombre.
4. ¡Empieza a crear tu juego!

### Crear un script
1. En la carpeta de tu proyecto, crea un archivo en `scripts/mi_script.py`.
2. Escribe tu clase:
   ```python
   from uron.api import UronScript

   class MiScript(UronScript):
       velocidad = 300.0

       def start(self):
           print("¡Hola desde URON!")

       def update(self, dt):
           # Mover el objeto con WASD
           mov_x = self.input.axis("a", "d")
           mov_y = self.input.axis("w", "s")
           if mov_x or mov_y:
               pos = self.transform.get("position")
               self.transform.set("position", [
                   pos[0] + mov_x * self.velocidad * dt,
                   pos[1] + mov_y * self.velocidad * dt
               ])
   ```
3. En el IDE, haz clic derecho sobre un objeto en el Hierarchy y selecciona **"Add Script"**.
4. ¡Dale a Play!

### Empaquetar tu juego
1. Ve a **File -> Build Game**.
2. Elige la carpeta de salida.
3. Haz clic en **"Build"**.
4. Obtendrás un ejecutable en la carpeta `build/`.

---

## 🧪 Pruebas

Para ejecutar las pruebas del motor (si has añadido alguna):
```bash
uv run pytest
```

---

## 📜 Licencia

Este proyecto está bajo la licencia **MIT**. Puedes usarlo, modificarlo y distribuirlo libremente.

---

## 🙌 Contribuciones

Las contribuciones son bienvenidas. Si encuentras un bug o quieres añadir una funcionalidad, abre un **Issue** o envía un **Pull Request**.

---

**¡Feliz desarrollo con URON Engine!** 🎮🚀
