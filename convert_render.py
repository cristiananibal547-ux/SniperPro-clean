from pathlib import Path
p = Path("render_start.py")
if not p.exists():
    print("NO_EXISTE_RENDER_START_PY")
else:
    backup = p.with_suffix(".py.bak")
    backup.write_bytes(p.read_bytes())
    b = p.read_bytes()
    for enc in ("utf-8-sig","utf-8","latin-1","cp1252"):
        try:
            s = b.decode(enc)
            print("OK_DECODificado_como:", enc)
            # ensure coding header
            lines = s.splitlines()
            if not lines:
                s = "# -*- coding: utf-8 -*-\n" + s
            elif not lines[0].startswith("# -*- coding:"):
                s = "# -*- coding: utf-8 -*-\n" + s
            p.write_text(s, encoding="utf-8")
            print("Reescrito en UTF-8. Backup creado:", backup.name)
            break
        except Exception:
            pass
    else:
        print("NO_PUDO_DECODIFICAR_AUTOMATICO")
