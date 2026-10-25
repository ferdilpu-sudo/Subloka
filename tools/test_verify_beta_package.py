import unittest
from verify_beta_package import verify


class BetaPackageTest(unittest.TestCase):
    def test_rejects_debug_wrong_package_and_missing_icon(self):
        good = "package: name='app.subloka.caption' versionName='0.7.0-beta.1'\nlaunchable-activity: name='app.subloka.MainActivity'\napplication-icon-160:'res/icon.xml'\n"
        verify(good)
        for bad in (good + 'application-debuggable', good + 'application-testOnly',
                    good.replace('app.subloka.caption', 'app.other'),
                    good.replace('application-icon-', 'missing-')):
            with self.assertRaises(ValueError): verify(bad)


if __name__ == '__main__': unittest.main()
