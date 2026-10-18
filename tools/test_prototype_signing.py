"""Certificate parsing regressions; signature verification must still exit successfully."""
import unittest
from prototype_signing import verify_signer_fingerprint

DIGEST = '295b1bbcebb8419c8361b077e41b913410207ee3ecb3bc0da3acf150c8e1c325'


class SignerFingerprintTest(unittest.TestCase):
    def test_supported_signer_labels(self):
        for label in ['Signer #1', 'Signer (minSdkVersion=33, maxSdkVersion=2147483647)',
                      'V3.0 Signer: (minSdkVersion=26, maxSdkVersion=2147483647)',
                      'V3.1 Signer: (minSdkVersion=33, maxSdkVersion=2147483647)',
                      'V2 Signer #1']:
            with self.subTest(label=label):
                verify_signer_fingerprint(f'{label} certificate SHA-256 digest: {DIGEST}\n', DIGEST)

    def test_repeated_scheme_same_certificate_and_uppercase(self):
        verify_signer_fingerprint(f'Signer #1 certificate SHA-256 digest: {DIGEST}\n'
                                  f'V3.0 Signer: certificate SHA-256 digest: {DIGEST.upper()}\r\n', DIGEST)

    def test_rejects_different_or_extra_signer(self):
        wrong = f'Signer #2 certificate SHA-256 digest: {"a" * 64}\n'
        for output in [wrong, f'Signer #1 certificate SHA-256 digest: {DIGEST}\n' + wrong]:
            with self.assertRaises(RuntimeError):
                verify_signer_fingerprint(output, DIGEST)

    def test_rejects_missing_truncated_and_non_certificate_hashes(self):
        for output in ['', f'Signer #1 public key SHA-256 digest: {DIGEST}\n',
                       f'Source Stamp Signer certificate SHA-256 digest: {DIGEST}\n',
                       f'Signer #1 certificate SHA-256 digest: {DIGEST[:-1]}\n']:
            with self.subTest(output=output), self.assertRaises(RuntimeError):
                verify_signer_fingerprint(output, DIGEST)


if __name__ == '__main__':
    unittest.main()
