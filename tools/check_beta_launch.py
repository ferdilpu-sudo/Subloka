"""CI-only clean-emulator launch check for the signed release APK. Never uninstalls."""
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


def adb(*args):
    return subprocess.check_output(['adb', *args], text=True, timeout=60)


if __name__ == '__main__':
    # Refuse physical devices and pre-existing installations/data.
    if adb('shell', 'getprop', 'ro.kernel.qemu').strip() != '1':
        raise SystemExit('This check requires a clean CI emulator')
    existing = subprocess.run(['adb', 'shell', 'pm', 'path', 'app.subloka.caption'], capture_output=True, text=True, timeout=30)
    if existing.returncode not in (0, 1):
        raise SystemExit('Cannot inspect emulator package state')
    if 'package:' in existing.stdout:
        raise SystemExit('Package already installed; refusing to reuse device data')
    installed = adb('install', sys.argv[1])
    if 'Success' not in installed:
        raise SystemExit(installed)
    adb('shell', 'am', 'start', '-W', '-n', 'app.subloka.caption/app.subloka.MainActivity')
    for attempt in range(15):
        adb('shell', 'uiautomator', 'dump', '/sdcard/beta-window.xml')
        raw = adb('shell', 'cat', '/sdcard/beta-window.xml')
        nodes = ET.fromstring(raw).iter('node')
        labels = [n.attrib.get('text', '') for n in nodes]
        if 'Belum ada proyek' in labels and 'Proyek baru' in labels:
            if any('Traveling' in text or 'Prototipe' in text for text in labels):
                raise SystemExit('Prototype content appeared on first launch')
            print('PASS: signed release opens to empty projects with New Project action')
            break
        if attempt == 14:
            raise SystemExit('Release did not reach expected first-launch screen')
        time.sleep(1)
