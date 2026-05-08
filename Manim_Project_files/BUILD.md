# Build Manim Studio

Run this from the project source directory:

```bash
./build_app.sh
```

The compiled application is written to:

```text
../dist/Manim Studio/
```

Launch it with:

```bash
"../dist/Manim Studio/Manim Studio"
```

The build uses PyInstaller and the local Python environment. Manim still depends on system multimedia/rendering tools such as FFmpeg and any LaTeX packages required by your scenes.
