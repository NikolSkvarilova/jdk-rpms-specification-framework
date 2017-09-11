from outputControl import logging_access as la
import sys
import re
import utils.core.base_xtest as bt
import config.global_config as gc
import config.runtime_config as rc
import utils
from utils.mock.mock_executor import DefaultMock
from utils.test_utils import log_failed_test, rename_default_subpkg, get_arch, two_lists_diff, get_32bit_id_in_nvra
from utils.test_constants import *
import os
from utils import pkg_name_split as pkgsplit
from utils.core.configuration_specific import JdkConfiguration
from utils.core.unknown_java_exception import UnknownJavaVersionException


class BaseTest(JdkConfiguration):

    def __init__(self):
        super().__init__()
        self.failed = []
        self.invalid_file_candidates = []

    def _get_target_java_directory(self, name):
        return get_32bit_id_in_nvra(pkgsplit.get_nvra(name))

    def _skipped_subpackages(self):
        return []

    def doc_test_java_files_permissions(self, pkgs):
        self._document("On all files extracted from RPMs to {}/nvra and {} apply "
                       "following rules:".format(JVM_DIR, MAN_DIR))
        DefaultMock().provideCleanUsefullRoot()
        default_manpages, res = DefaultMock().execute_ls("/usr/share/man/man1")
        default_manpages = default_manpages.split("\n")
        if res != 0:
            log_failed_test(self, "Default manpages extraction has failed. Manpage tests invalid: " + str(res) +
                            str(default_manpages))

        for pkg in pkgs:
            name = os.path.basename(pkg)
            subpackage = rename_default_subpkg(pkgsplit.get_subpackage_only(name))
            PermissionTest.instance.log("Checking {} subpackage...".format(subpackage), la.Verbosity.TEST)
            if subpackage in subpackages_without_alternatives() + self._skipped_subpackages():
                PermissionTest.instance.log("Skipping " + pkg, la.Verbosity.TEST)
                continue

            if not DefaultMock().postinstall_exception_checked(pkg):
                continue

            out, result = DefaultMock().executeCommand(["ls -LR " + JVM_DIR + "/" +
                                                       self._get_target_java_directory(name)])
            if result == 2:
                log_failed_test(self, "Java directory not found for " + subpackage)
                continue
            valid_targets = self._parse_output(out)
            self.sort_and_test(valid_targets, subpackage)

            manpages = two_lists_diff(DefaultMock().execute_ls(MAN_DIR)[0].split("\n"), default_manpages)
            for manpage in manpages:
                self.sort_and_test([MAN_DIR + "/" + manpage])

        PermissionTest.instance.log("Failed permissions tests: " + " \n ".join(self.failed), la.Verbosity.ERROR)
        PermissionTest.instance.log("Unexpected files, filetypes or errors occured: " +
                                    ", ".join(self.invalid_file_candidates))
        assert len(self.failed) == 0

    def _parse_output(self, out):
        output_parts = out.split("\n")
        return_targets = []
        header = re.compile("/[^:]*:")
        current_header = ""
        for line in output_parts:
            if line == "":
                continue
            elif "cannot access" in line:
                self.invalid_file_candidates.append(line)
                continue
            elif header.search(line):
                current_header = header.match(line)
                current_header = current_header.group(0).strip(":")
                continue
            else:
                return_targets.append(current_header + "/" + line)
        return return_targets

    def sort_and_test(self, valid_targets, subpackage=None):
        self._document("\n - ".join(["Directories should have 755 permissions.",
                                     "Content of bin directory should have 755 permissions",
                                     "Regular files should have 644 permissions",
                                     "Symbolic links should have 777 permissions.",
                                     "Other types of files with different permissions should not be present."]))
        for target in valid_targets:
            out, res = DefaultMock().executeCommand(['stat -c "%F" ' + target])
            if out == "directory":
                self._test_fill_in(target, out, "755")
            elif out == "regular file":
                if "/bin/" in target:
                    self._test_fill_in(target, "binary", "755")
                else:
                    self._test_fill_in(target, out, "644")
            elif out == "symbolic link":
                self._test_fill_in(target, out, "777")
                out, res = DefaultMock().executeCommand(["readlink " + target])
                if res != 0:
                    log_failed_test(self, "Target of symbolic link {} does not exist.".format(target) + " Error " + out)
                self.sort_and_test([out])
            else:
                if res != 0:
                    PermissionTest.instance.log("Command stat -c '%F' {} finished with {} exit code".format(target, res))
                else:
                    PermissionTest.instance.log("Unexpected filetype. Needs manual inspection.")
                log_failed_test(self, "In subpackage {} following was found: Command stat -c '%F' {} finished"
                                      " with message: {}. ".format(subpackage, target, res, out))
                self.invalid_file_candidates.append(target)

    def _test_fill_in(self, file, filetype, expected_permission):
        out, res = DefaultMock().executeCommand(['stat -c "%a" ' + file])
        if res != 0:
            log_failed_test(self, filetype + " link is broken, could not find " + file)
            return
        else:
            PermissionTest.instance.log(filetype + " {} exists. Checking permissions... ".format(file),
                                        la.Verbosity.TEST)
        for p in range(3):
            if not (int(out[p]) == int(expected_permission[p])):
                log_failed_test(self, "Permissions of {} not as expected, should be {} but is "
                                      "{}.".format(file, expected_permission, out))
                break
        else:
            PermissionTest.instance.log(filetype + " {} with permissions {}. Check "
                                        "successful.".format(file, out), la.Verbosity.TEST)
        return


class OpenJdk6(BaseTest):
    def _skipped_subpackages(self):
        return [JAVADOC]

    def _get_target_java_directory(self, name):
        directory = super()._get_target_java_directory(name)
        unnecessary_part = directory.split("-")[-1]
        directory = directory.replace("-" + unnecessary_part, "")
        return directory


class OpenJdk6PowBeArchAndX86(OpenJdk6):
    def _get_target_java_directory(self, name):
        return super()._get_target_java_directory(name) + "." + get_arch(PermissionTest.instance)


class OpenJdk7(OpenJdk6):
    def _skipped_subpackages(self):
        return super()._skipped_subpackages() + [DEFAULT]

    def _get_target_java_directory(self, name):
        return super(OpenJdk6, self)._get_target_java_directory(name)


class OpenJdk8(OpenJdk7):
    def _skipped_subpackages(self):
        return super()._skipped_subpackages() + [JAVADOC + DEBUG_SUFFIX, DEFAULT + DEBUG_SUFFIX,
                                                 JAVADOC + "-zip", JAVADOC + "-zip" + DEBUG_SUFFIX]


class PermissionTest(bt.BaseTest):
    instance = None

    def test_alternatives_binary_files(self):
        pkgs = self.getBuild()
        self.csch.doc_test_java_files_permissions(pkgs)

    def setCSCH(self):
        PermissionTest.instance = self
        rpms = rc.RuntimeConfig().getRpmList()
        self.log("Checking files for " + rpms.getMajorPackage(), la.Verbosity.TEST)
        if rpms.getVendor() == gc.OPENJDK:
            if rpms.getMajorVersionSimplified() == "6":
                if self.getCurrentArch() in (gc.getX86_64Arch() + gc.getPower64BeAchs()):
                    self.csch = OpenJdk6PowBeArchAndX86()
                    return
                else:
                    self.csch = OpenJdk6()
                    return
            if rpms.getMajorVersionSimplified() == "7":
                self.csch = OpenJdk7()
                return
            elif rpms.getMajorVersionSimplified() == "8":
                self.csch = OpenJdk8()
                return
            elif rpms.getMajorVersionSimplified() == "9":
                pass
            else:
                raise UnknownJavaVersionException("Unknown version of OpenJDK.")


def testAll():
    return PermissionTest().execute_tests()


def documentAll():
    la.LoggingAccess().stdout("File permissions conventions")
    return PermissionTest().execute_special_docs()


def main(argv):
    utils.core.base_xtest.defaultMain(argv, documentAll, testAll)
    return PermissionTest().execute_special_docs()


if __name__ == "__main__":
    main(sys.argv[1:])