"""
Launcher script to start the CASE-MTH Web Application Dashboard.
Starts local Flask HTTP server on http://localhost:5000 and opens browser.
"""

import sys
import os
import webbrowser
import time

def start_server():
    print("==========================================================================")
    print("   CASE-MTH INTERACTIVE WEB APPLICATION DASHBOARD LAUNCHER")
    print("==========================================================================")
    print(" [*] Target URL  : http://localhost:5000")
    print(" [*] Architecture: 128 Heterogeneous Compute Nodes (Edge, Private, Public)")
    print(" [*] Telemetry   : Borg, Alibaba PAI, DataCo Traces + 24-Hour Carbon Curves")
    print("--------------------------------------------------------------------------")

    from app import app

    # Open browser automatically after 1.5 seconds
    try:
        webbrowser.open("http://localhost:5000")
    except Exception as e:
        print(f" [!] Note: Could not auto-open browser ({e}). Access URL manually.")

    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    start_server()
