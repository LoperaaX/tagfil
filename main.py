"""
main.py — Punto de entrada de InfoFile

Modos de uso:

  1. Sin argumentos → lanza el tray + ventana principal
         py main.py

  2. Desde el menú contextual de Windows:
         py main.py --file "C:\ruta\archivo.pdf"
     → Abre el diálogo de descripción para ese archivo.

  3. CLI para desarrollo y pruebas:
         py main.py add "C:\archivo.pdf" --desc "Descripción" --tags usb seguridad
         py main.py search "usb"
         py main.py get "C:\archivo.pdf"
         py main.py delete "C:\archivo.pdf"
         py main.py stats
         py main.py suggest-name "C:\archivo.pdf" --type factura --entity ACME --date 2026-06-15 --seq 14
         py main.py menu --install
         py main.py menu --uninstall
         py main.py menu --status
"""

import argparse
import sys

from config import get_logger, APP_NAME, APP_VERSION

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# Helpers de salida CLI
# ──────────────────────────────────────────────

def _ok(msg: str) -> None:
    print(f"OK  {msg}")

def _err(msg: str) -> None:
    print(f"ERR {msg}", file=sys.stderr)

def _print_file(f: dict) -> None:
    tags   = ", ".join(f["tags"]) if f["tags"] else "—"
    exists = ""
    if f.get("file_exists") is not None:
        exists = " [existe]" if f["file_exists"] else " [no encontrado]"
    print(f"  {f['name']}{exists}")
    print(f"    Ruta : {f['path']}")
    print(f"    Desc : {f['description'] or '—'}")
    print(f"    Tags : {tags}")
    print(f"    Mod  : {f['updated_at']}")
    print()


# ──────────────────────────────────────────────
# Modo --file (menú contextual de Windows)
# ──────────────────────────────────────────────

def _run_dialog(file_path: str) -> None:
    """
    Abre el diálogo PyQt6 para editar descripción.
    Fallback a terminal si PyQt6 no está instalado.
    """
    from pathlib import Path
    path = Path(file_path)
    if not path.exists():
        logger.warning(f"Ruta no encontrada en disco: {path}")

    try:
        from PyQt6.QtWidgets import QApplication
        from dialogs import DescriptionDialog

        app = QApplication.instance() or QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(True)
        dialog = DescriptionDialog(str(path))
        dialog.exec()

    except ImportError:
        logger.info("PyQt6/dialogs no disponible — usando fallback terminal")
        _dialog_terminal(str(path))


def _dialog_terminal(path: str) -> None:
    """Diálogo mínimo por terminal (fallback sin PyQt6)."""
    import database as db
    db.init_db()
    existing = db.get_file(path)

    print(f"\n{'─' * 50}")
    print(f"  {APP_NAME} — Agregar / editar descripción")
    print(f"{'─' * 50}")
    print(f"  Archivo : {path}")
    if existing:
        print(f"  Desc    : {existing['description'] or '—'}")
        print(f"  Tags    : {', '.join(existing['tags']) or '—'}")

    print()
    desc     = input("  Nueva descripción (Enter para mantener): ").strip()
    tags_raw = input("  Tags separadas por coma (Enter para mantener): ").strip()

    if existing and not desc:
        desc = existing["description"]
    tags = (
        [t.strip() for t in tags_raw.split(",") if t.strip()]
        if tags_raw
        else (existing["tags"] if existing else [])
    )

    if not desc and not tags:
        print("\n  Sin cambios.")
        return

    db.upsert_file(path=path, description=desc, tags=tags)
    print(f"\n  Guardado correctamente.")
    print(f"{'─' * 50}\n")


# ──────────────────────────────────────────────
# Modo GUI (sin argumentos)
# ──────────────────────────────────────────────

def _run_gui() -> int:
    """Lanza la app completa con tray y ventana principal."""
    try:
        from PyQt6.QtWidgets import QApplication
        from tray import TrayApp
    except ImportError:
        _err("PyQt6 no está instalado. Instálalo con:  py -m pip install PyQt6")
        return 1

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)   # seguir corriendo aunque se cierre la ventana
    app.setStyle("Fusion")
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    from security import ensure_single_instance, focus_existing_window
    if not ensure_single_instance():
        focus_existing_window()
        return 0

    tray = TrayApp()
    tray.show()

    # Abrir la ventana principal al arrancar
    tray.open_window()

    logger.info(f"{APP_NAME} {APP_VERSION} iniciado")
    return app.exec()


# ──────────────────────────────────────────────
# Comandos CLI
# ──────────────────────────────────────────────

def cmd_add(args) -> int:
    import database as db
    db.init_db()
    tags    = args.tags or []
    file_id = db.upsert_file(path=args.path, description=args.desc, tags=tags)
    _ok(f"Guardado (id={file_id}): {args.path}")
    return 0


def cmd_search(args) -> int:
    import database as db
    db.init_db()
    results = db.search(args.query)
    if not results:
        print(f"  Sin resultados para: '{args.query}'")
        return 0
    print(f"\n  {len(results)} resultado(s) para '{args.query}':\n")
    for f in results:
        _print_file(f)
    return 0


def cmd_get(args) -> int:
    import database as db
    db.init_db()
    f = db.get_file(args.path)
    if not f:
        _err(f"No registrado: {args.path}")
        return 1
    print()
    _print_file(f)
    return 0


def cmd_delete(args) -> int:
    import database as db
    db.init_db()
    deleted = db.delete_file(args.path)
    if deleted:
        _ok(f"Eliminado: {args.path}")
    else:
        _err(f"No encontrado: {args.path}")
        return 1
    return 0


def cmd_stats(args) -> int:
    import database as db
    db.init_db()
    s = db.get_stats()
    print(f"\n  {APP_NAME} — Estadísticas")
    print(f"  {'─' * 30}")
    print(f"  Archivos registrados : {s['total_files']}")
    print(f"  Con descripción      : {s['files_with_desc']}")
    print(f"  Sin descripción      : {s['files_without_desc']}")
    print(f"  Tags únicas          : {s['total_tags']}")
    print()
    return 0


def cmd_suggest_name(args) -> int:
    from core.naming import suggest_short_path

    try:
        suggested = suggest_short_path(
            original_path=args.path,
            document_type=args.type,
            entity=args.entity,
            document_date=args.date,
            sequence=args.seq,
            qualifier=args.qualifier or "",
        )
    except ValueError as e:
        _err(str(e))
        return 1

    print(str(suggested.name if args.name_only else suggested))
    return 0


def cmd_menu(args) -> int:
    from context_menu import install, uninstall, is_installed, _COMMAND
    if args.install:
        ok = install()
        _ok("Menú contextual instalado") if ok else _err("Error al instalar")
        return 0 if ok else 1
    if args.uninstall:
        ok = uninstall()
        _ok("Menú contextual desinstalado") if ok else _err("Error al desinstalar")
        return 0 if ok else 1
    if args.status:
        installed = is_installed()
        print(f"  Estado  : {'Instalado' if installed else 'No instalado'}")
        print(f"  Comando : {_COMMAND}")
        return 0
    return 0


def cmd_security_check(args) -> int:
    import database as db
    from security import run_security_audit

    db.init_db()
    findings = run_security_audit()
    status_label = {
        "ok": "OK ",
        "info": "INFO",
        "warn": "WARN",
        "error": "ERR",
    }

    print(f"\n  {APP_NAME} — Auditoría de seguridad")
    print(f"  {'-' * 38}")
    worst = 0
    weights = {"ok": 0, "info": 0, "warn": 1, "error": 2}
    for item in findings:
        status = item["status"]
        worst = max(worst, weights.get(status, 1))
        print(f"  {status_label.get(status, status.upper()):<4} {item['check']:<18} {item['detail']}")
    print()
    return 1 if worst >= 2 else 0


# ──────────────────────────────────────────────
# Parser
# ──────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=APP_NAME.lower(),
        description=f"{APP_NAME} {APP_VERSION} — Descripciones inteligentes para tus archivos",
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {APP_VERSION}")
    parser.add_argument(
        "--file", metavar="RUTA",
        help="Abrir diálogo de descripción para un archivo o carpeta",
    )

    sub = parser.add_subparsers(dest="command", metavar="COMANDO")

    p_add = sub.add_parser("add", help="Agregar o actualizar descripción")
    p_add.add_argument("path", metavar="RUTA")
    p_add.add_argument("--desc", metavar="TEXTO", default="")
    p_add.add_argument("--tags", metavar="TAG", nargs="*")
    p_add.set_defaults(func=cmd_add)

    p_search = sub.add_parser("search", help="Buscar archivos")
    p_search.add_argument("query", metavar="TEXTO")
    p_search.set_defaults(func=cmd_search)

    p_get = sub.add_parser("get", help="Ver metadatos de un archivo")
    p_get.add_argument("path", metavar="RUTA")
    p_get.set_defaults(func=cmd_get)

    p_del = sub.add_parser("delete", help="Eliminar metadatos de un archivo")
    p_del.add_argument("path", metavar="RUTA")
    p_del.set_defaults(func=cmd_delete)

    p_stats = sub.add_parser("stats", help="Estadísticas de la base de datos")
    p_stats.set_defaults(func=cmd_stats)

    p_suggest = sub.add_parser("suggest-name", help="Sugerir nombre corto para un archivo")
    p_suggest.add_argument("path", metavar="RUTA")
    p_suggest.add_argument("--type", required=True, metavar="TIPO", help="Tipo documental: factura, contrato, informe, etc.")
    p_suggest.add_argument("--entity", required=True, metavar="ENTIDAD", help="Cliente, proveedor, area o proyecto")
    p_suggest.add_argument("--seq", required=True, type=int, metavar="N", help="Consecutivo del documento")
    p_suggest.add_argument("--date", metavar="FECHA", help="Fecha o ano del documento")
    p_suggest.add_argument("--qualifier", metavar="TEXTO", default="", help="Texto corto opcional, por ejemplo area o sede")
    p_suggest.add_argument("--name-only", action="store_true", help="Mostrar solo el nombre, sin carpeta")
    p_suggest.set_defaults(func=cmd_suggest_name)

    p_menu = sub.add_parser("menu", help="Gestionar el menú contextual de Windows")
    mg = p_menu.add_mutually_exclusive_group(required=True)
    mg.add_argument("--install",   action="store_true")
    mg.add_argument("--uninstall", action="store_true")
    mg.add_argument("--status",    action="store_true")
    p_menu.set_defaults(func=cmd_menu)

    p_sec = sub.add_parser("security-check", help="Auditoría rápida de seguridad")
    p_sec.set_defaults(func=cmd_security_check)

    return parser


# ──────────────────────────────────────────────
# Entrada principal
# ──────────────────────────────────────────────

def main() -> int:
    parser = build_parser()
    args   = parser.parse_args()

    # Modo menú contextual
    if args.file:
        logger.info(f"Modo diálogo: {args.file}")
        _run_dialog(args.file)
        return 0

    # Comando CLI
    if hasattr(args, "func"):
        logger.info(f"Comando CLI: {args.command}")
        return args.func(args)

    # Sin argumentos → lanzar GUI completa
    logger.info("Modo GUI")
    return _run_gui()


if __name__ == "__main__":
    sys.exit(main())
