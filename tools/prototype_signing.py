"""Owner-held prototype APK signing. Never print or commit the signing bundle."""
import argparse
import base64
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import secrets

ALIAS = 'subloka-prototype'
SECRET = 'SUBLOKA_PROTOTYPE_SIGNING'
REPO = 'ferdilpu-sudo/Subloka'


def keytool():
    candidates = [shutil.which('keytool')]
    for root in [os.environ.get('JAVA_HOME'), r'C:\Program Files\Android\Android Studio\jbr']:
        if root:
            candidates.append(str(Path(root) / 'bin' / ('keytool.exe' if os.name == 'nt' else 'keytool')))
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise RuntimeError('JDK keytool not found. Install JDK or set JAVA_HOME, then retry.')


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def certificate(store, password):
    env = dict(os.environ, SUBLOKA_KEY_PASSWORD=password)
    return run([keytool(), '-exportcert', '-alias', ALIAS, '-keystore', str(store),
                '-storepass:env', 'SUBLOKA_KEY_PASSWORD'], env=env, stdout=subprocess.PIPE).stdout


def validate(bundle, directory):
    store = directory / 'key.p12'
    store.write_bytes(base64.b64decode(bundle['keystore'], validate=True))
    store.chmod(0o600)
    digest = hashlib.sha256(certificate(store, bundle['password'])).hexdigest()
    if digest != bundle['certificate_sha256']:
        raise RuntimeError('Signing certificate does not match saved fingerprint.')
    return store


def setup(args):
    folder = args.directory.expanduser().resolve()
    bundle_path = folder / 'prototype-signing.json'
    remote_exists = False
    if args.upload:
        if not shutil.which('gh'):
            raise RuntimeError('Install GitHub CLI and run gh auth login, then retry. No key created.')
        result = run(['gh', 'secret', 'list', '--repo', REPO, '--json', 'name'],
                     stdout=subprocess.PIPE, text=True)
        remote_exists = any(x['name'] == SECRET for x in json.loads(result.stdout))
        if remote_exists and not bundle_path.exists():
            raise RuntimeError('Repository already has a key. Restore your original signing bundle; refusing to rotate it.')
    folder.mkdir(parents=True, exist_ok=True)
    if not bundle_path.exists():
        password = secrets.token_urlsafe(32)
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / 'key.p12'
            env = dict(os.environ, SUBLOKA_KEY_PASSWORD=password)
            run([keytool(), '-genkeypair', '-noprompt', '-storetype', 'PKCS12',
                 '-keystore', str(store), '-alias', ALIAS, '-keyalg', 'RSA', '-keysize', '3072',
                 '-validity', '10000', '-dname', 'CN=SubLoka Prototype',
                 '-storepass:env', 'SUBLOKA_KEY_PASSWORD', '-keypass:env', 'SUBLOKA_KEY_PASSWORD'], env=env)
            bundle = {'keystore': base64.b64encode(store.read_bytes()).decode('ascii'),
                      'password': password,
                      'certificate_sha256': hashlib.sha256(certificate(store, password)).hexdigest()}
            with bundle_path.open('x', encoding='utf-8') as f:
                json.dump(bundle, f)
            bundle_path.chmod(0o600)
    bundle = json.loads(bundle_path.read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory() as tmp:
        validate(bundle, Path(tmp))
    if args.upload:
        run(['gh', 'secret', 'set', SECRET, '--repo', REPO],
            input=json.dumps(bundle).encode('utf-8'))
        print('Signing secret uploaded. Run Android CI manually on the prototype branch.')
    print('Certificate SHA256:', bundle['certificate_sha256'])
    print('Keep a private backup of:', bundle_path)
    print('Never commit/share this file or replace this key for future updates.')


def verify_signer_fingerprint(output, expected):
    # Build Tools 37 labels scheme-specific signers (e.g. V3.0 Signer:),
    # whereas older tools print Signer #1. Never match public-key/stamp hashes.
    digests = re.findall(
        r'^(?:V[1-4](?:\.\d+)? )?Signer\b[^\r\n]* certificate SHA-256 digest: ([0-9a-fA-F]{64})\s*$',
        output, re.MULTILINE)
    if not digests or {value.lower() for value in digests} != {expected.lower()}:
        raise RuntimeError('Signed APK certificate mismatch or missing signer digest; no artifact published.')


def sign(args):
    raw = os.environ.get(SECRET)
    if not raw:
        raise RuntimeError('Missing SUBLOKA_PROTOTYPE_SIGNING; refusing temporary-key fallback.')
    bundle = json.loads(raw)
    if args.output.exists():
        raise RuntimeError('Output already exists; use a fresh output path.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        store = validate(bundle, directory)
        candidate = directory / 'signed.apk'
        env = dict(os.environ, SUBLOKA_KEY_PASSWORD=bundle['password'])
        run([args.apksigner, 'sign', '--ks', str(store), '--ks-key-alias', ALIAS,
             '--ks-pass', 'env:SUBLOKA_KEY_PASSWORD', '--key-pass', 'env:SUBLOKA_KEY_PASSWORD',
             '--out', str(candidate), str(args.apk)], env=env)
        result = run([args.apksigner, 'verify', '--verbose', '--print-certs', str(candidate)],
                     stdout=subprocess.PIPE, text=True)
        verify_signer_fingerprint(result.stdout, bundle['certificate_sha256'])
        shutil.copyfile(candidate, args.output)
        digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
        args.output.with_suffix('.verification.txt').write_text(
            result.stdout + '\nAPK SHA256: ' + digest + '\n', encoding='utf-8')
        print('Verified stable prototype APK:', args.output)
        print('Certificate SHA256:', bundle['certificate_sha256'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('setup')
    create.add_argument('--directory', type=Path, default=Path.home() / '.subloka-signing')
    create.add_argument('--upload', action='store_true', help='Upload the private bundle as an encrypted repository Actions secret')
    signing = commands.add_parser('sign')
    signing.add_argument('--apk', type=Path, required=True)
    signing.add_argument('--output', type=Path, required=True)
    signing.add_argument('--apksigner', required=True)
    args = parser.parse_args()
    try:
        (setup if args.command == 'setup' else sign)(args)
    except (RuntimeError, ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, 'Signing failed: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
