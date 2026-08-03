# TagFil Project Structure

This is the target structure for keeping the app easy to grow while preserving
the current desktop, Explorer, SQLite, and future cloud integration pieces.

```text
TagFil/
  main.py                    # CLI and desktop entry point
  requirements.txt
  TagFil.spec                # PyInstaller build config
  version_info.txt

  assets/
    icon.ico

  tagfil/
    __init__.py
    main_window.py           # Main PyQt window shell
    sidebar.py
    theme.py

    pages/                   # Full application views
      resumen.py
      archivos.py
      etiquetas.py
      buscar.py
      configuracion.py
      papelera.py

    widgets/                 # Reusable PyQt widgets
      neon_icon.py
      search_worker.py
      theme_selector.py
      toggle_switch.py
      ui_helpers.py

  core/                      # Recommended next move
    __init__.py
    config.py                # App constants and paths
    database.py              # SQLite schema and queries
    naming.py                # Short filename generation
    security.py              # Validation, sanitization, single instance

  explorer/                  # Recommended next move
    context_menu.py          # HKCU context menu registration
    metadata.py              # ADS and desktop.ini bridge
    shell_extension.py       # Build/register overlay extension

  integrations/              # Recommended future area
    microsoft_graph.py       # OneDrive and SharePoint Graph client
    sync.py                  # Sync orchestration and conflict handling

  ShellExtension/            # .NET Explorer overlay source
  docs/
    PROJECT_STRUCTURE.md
```

## Migration Order

1. Keep `main.py` at the root until packaging is stable.
2. Move UI-only modules into `tagfil/` first. This is already mostly done.
3. Move `config.py`, `database.py`, and `security.py` into `core/` only after
   updating imports and PyInstaller hidden imports.
4. Move Explorer integration files into `explorer/` after confirming the
   context menu and overlay registration still work.
5. Add `integrations/` when OneDrive/SharePoint work begins. Use Microsoft
   Graph as the source for cloud metadata; keep ADS as a local Explorer cache.

## Naming Notes

Use `TagFil` for user-facing product names, logs, registry labels, and packaged
output. The current .NET overlay project still uses `InfoFileOverlay`; rename it
in a dedicated change because COM registration and Explorer overlay identifiers
are sensitive.
