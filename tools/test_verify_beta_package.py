import unittest
import io
import zipfile
from verify_beta_package import verify, verify_native_libraries


class BetaPackageTest(unittest.TestCase):
    def test_rejects_debug_wrong_package_and_missing_icon(self):
        good = "package: name='app.subloka.caption' versionName='0.7.0-beta.1'\nlaunchable-activity: name='app.subloka.MainActivity'\napplication-icon-160:'res/icon.xml'\n"
        verify(good)
        for bad in (good + 'application-debuggable', good + 'application-testOnly',
                    good.replace('app.subloka.caption', 'app.other'),
                    good.replace('application-icon-', 'missing-')):
            with self.assertRaises(ValueError): verify(bad)


    def test_rejects_dependency_only_abi_and_missing_engine(self):
        text = "native-code: 'arm64-v8a' 'x86_64'\n"
        entries = {f'lib/{abi}/{engine}': b'fixture' for abi in ('arm64-v8a', 'x86_64')
                   for engine in ('libsubloka_asr.so', 'libsubloka_translation.so')}

        def archive(values):
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, 'w') as apk:
                for name, content in values.items(): apk.writestr(name, content)
            stream.seek(0)
            return stream

        verify_native_libraries(text, archive(entries))
        for bad in ({**entries, 'lib/armeabi-v7a/libtranslate_jni.so': b'dependency'},
                    {k: v for k, v in entries.items() if k != 'lib/arm64-v8a/libsubloka_asr.so'},
                    {**entries, 'lib/x86_64/libsubloka_translation.so': b''}):
            with self.assertRaises(ValueError): verify_native_libraries(text, archive(bad))
        with self.assertRaises(ValueError):
            verify_native_libraries(text.replace("'x86_64'", "'x86'"), archive(entries))


if __name__ == '__main__': unittest.main()
