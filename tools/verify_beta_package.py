"""Fail CI if the signed distribution APK is debuggable, test-only or misidentified."""
import sys
from pathlib import Path


def verify(text):
    if "package: name='app.subloka.caption'" not in text:
        raise ValueError('Unexpected application identity')
    if 'application-debuggable' in text or 'application-testOnly' in text:
        raise ValueError('Debug/test APK cannot be distributed as beta')
    if 'launchable-activity:' not in text or 'application-icon-' not in text:
        raise ValueError('Missing launcher activity/icon')
    if "versionName='0.7.0-beta.1'" not in text:
        raise ValueError('Unexpected beta version')


if __name__ == '__main__':
    verify(Path(sys.argv[1]).read_text())
    print('Beta package identity, launcher and non-debug flags verified')
