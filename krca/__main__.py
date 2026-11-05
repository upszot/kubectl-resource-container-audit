#!/usr/bin/env python3
# krca/__main__.py - Punto de entrada principal de KRCA

import sys

from . import __version__, analyze_resources, parse_args, show_help


def main(argv=None):
    """Función principal del punto de entrada."""
    if argv is not None:
        sys.argv = [sys.argv[0], *argv]

    args = None
    try:
        # Manejo básico para --help y --version
        if len(sys.argv) == 1:
            show_help()
            return 0

        if "--help" in sys.argv or "-h" in sys.argv:
            show_help()
            return 0

        if "--version" in sys.argv:
            print(f"kubectl-resource-container-audit v{__version__}")
            return 0

        # Parsear argumentos y ejecutar análisis
        args = parse_args()
        return analyze_resources(args)

    except KeyboardInterrupt:
        print("\nOperación cancelada por el usuario", file=sys.stderr)
        return 1
    except SystemExit:
        # argparse sale con SystemExit; se respeta su código
        raise
    except Exception as e:
        print(f"Error inesperado: {str(e)}", file=sys.stderr)
        if args and getattr(args, "debug", False):
            import traceback

            traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
