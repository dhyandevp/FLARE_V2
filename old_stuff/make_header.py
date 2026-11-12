# Rebuilds FLARE_V2_ESP32_Local/dashboard_html.h from dashboard.html
# Run from the FLARE_V2 folder:  python make_header.py
import os
here = os.path.dirname(os.path.abspath(__file__))
html = open(os.path.join(here, "dashboard.html"), encoding="utf-8").read()
out = os.path.join(here, "FLARE_V2_ESP32_Local", "dashboard_html.h")
open(out, "w", encoding="utf-8").write(
    "// AUTO-GENERATED from dashboard.html - edit dashboard.html, not this file.\n"
    "#pragma once\n#include <pgmspace.h>\n\n"
    'const char DASHBOARD_HTML[] PROGMEM = R"FLAREHTML(' + html + ')FLAREHTML";\n')
print("wrote", out, len(html.encode()), "bytes")
