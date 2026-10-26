"""Fail CI if the signed distribution APK is debuggable, test-only or misidentified."""
import sys
import re
import zipfile
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


def verify_native_libraries(text, apk_path):
    expected = {"arm64-v8a", "x86_64"}
    match = re.search(r"^native-code:(.*)$", text, re.MULTILINE)
    advertised = set(re.findall(r"'([^']+)'", match.group(1))) if match else set()
    if advertised != expected:
        raise ValueError('Unexpected or missing advertised native ABIs')
    with zipfile.ZipFile(apk_path) as apk:
        names = set(apk.namelist())
        packaged = {n.split('/')[1] for n in names if n.startswith('lib/') and n.endswith('.so')}
        if packaged != expected:
            raise ValueError('Unexpected or missing packaged native ABIs')
        for abi in expected:
            for engine in ('libsubloka_asr.so', 'libsubloka_translation.so'):
                path = f'lib/{abi}/{engine}'
                if path not in names or apk.getinfo(path).file_size == 0:
                    raise ValueError(f'Missing or empty engine: {path}')


if __name__ == '__main__':
    verify(Path(sys.argv[1]).read_text())
    verify_native_libraries(Path(sys.argv[1]).read_text(), sys.argv[2])
    print('Beta package identity, launcher, non-debug flags and native ABI coverage verified')
