#!/bin/bash
# Environment checker for DaVinci Resolve MCP

echo "=== DaVinci Resolve MCP — Environment Check ==="
echo ""

# macOS
echo "macOS: $(sw_vers -productVersion)"
echo "Arch:  $(uname -m)"
echo ""

# Python
echo "Python: $(python3 --version 2>&1)"
echo "Path:   $(which python3)"
echo ""

# Resolve
RESOLVE_APP="/Applications/DaVinci Resolve/DaVinci Resolve.app"
if [ -d "$RESOLVE_APP" ]; then
    VERSION=$(mdls -name kMDItemVersion "$RESOLVE_APP" | awk -F'"' '{print $2}')
    echo "Resolve: v${VERSION}"
else
    echo "Resolve: NOT FOUND"
fi

# Resolve running?
if pgrep -x "DaVinci Resolve" > /dev/null; then
    echo "Status:  RUNNING"
else
    echo "Status:  NOT RUNNING"
fi
echo ""

# Scripting API
API_PATH="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
if [ -d "$API_PATH" ]; then
    echo "Scripting API: Found"
else
    echo "Scripting API: NOT FOUND"
fi

# fusionscript.so
FUSION_LIB="$RESOLVE_APP/Contents/Libraries/Fusion/fusionscript.so"
if [ -f "$FUSION_LIB" ]; then
    echo "fusionscript.so: Found"
else
    echo "fusionscript.so: NOT FOUND"
fi

echo ""
echo "=== Check complete ==="
