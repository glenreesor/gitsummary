#!/usr/bin/env python3

# Copyright 2018, 2019 Glen Reesor
#
# This file is part of gitsummary.
#
# Gitsummary is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3,
# as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import gitsummary as gs

import copy
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest

#-----------------------------------------------------------------------------
# setUp() and tearDown() common to all tests
#   - Create/delete a temporary folder where we can do git stuff
#   - cd into it at test start
#   - cd out and delete it at test exit
#
# We can't use tempfile.TemporaryDirectory() because its cleanup() method
# will fail on Windows files with the readonly attribute set (which is the
# case for files in .git/)
#-----------------------------------------------------------------------------
def commonTestSetUp(self):
    self.setupInitialDir = os.getcwd()
    self.tempDir = tempfile.mkdtemp(prefix='testGitsummary.')
    os.chdir(self.tempDir)

def commonTestTearDown(self):
    os.chdir(self.setupInitialDir)
    shutil.rmtree(self.tempDir, onerror=rmtreeErrorHandler)

def rmtreeErrorHandler(func, path, exception):
    # We're expecting this to be called due to a Windows readonly file, so
    # remove that attribute and continue
    os.chmod(path, stat.S_IWRITE)
    func(path)

#-----------------------------------------------------------------------------
# Helpers
#-----------------------------------------------------------------------------
def createAndCommitFile(
    filename,
    contents = 'Default contents',
    commitMsg = 'Commit message'
):
    """
    Create the specified file with the specified contents in the current working
    directory then 'git add' and 'git commit'.

    An error will be thrown if the file exists already.

    Args
        String filename  - The name of the file to create
        String contents  - The contents to be written to the file
        String commitMsg - The commit message to use
    """
    newFile = open(filename, 'x')
    newFile.write(contents)
    newFile.close()
    execute(['git', 'add', filename])
    execute(['git', 'commit', '-m', commitMsg])

#-----------------------------------------------------------------------------
def createEmptyRemoteLocalPair(remoteName, localName):
    """
    Create a remote/local pair with no commits in either

    Args
        String remoteName - The name of the folder to create for the remote
        String localName  - The name of the folder to create for the local
    """
    execute(['git', 'init', '--bare', remoteName])
    execute(['git', 'clone', remoteName, localName])

#-----------------------------------------------------------------------------
def createNonEmptyGitRepository():
    """
    Create a non-blank git repository using 'git init' in the current working
    directory.
    """
    execute(['git', 'init'])
    createAndCommitFile('createNonEmptyGitRepository-file')

#-----------------------------------------------------------------------------
def createNonEmptyRemoteLocalPair(remoteName, localName):
    """
    Create a remote/local pair with one commit in master, and the two
    repositories are in sync.

    Args
        String remoteName - The name of the folder to create for the remote
        String localName  - The name of the folder to create for the local
    """
    execute(['git', 'init', '--bare', remoteName])
    execute(['git', 'clone', remoteName, localName])
    os.chdir(localName)
    createAndCommitFile('createNonEmptyRemoteLocalPair-file')
    execute(['git', 'push'])
    os.chdir('..')

#-----------------------------------------------------------------------------
def execute(command):
    """
    Execute the specified command, redirecting stdout and stderr to DEVNULL.
    We redirect stderr as well because git sends some informative output there,
    which clutters the testing output.

    An error will be thrown if the command has a non-zero exit code.

    Args
        List command - The command and args to execute
    """
    subprocess.run(
        command,
        stdout = subprocess.DEVNULL,
        stderr = subprocess.DEVNULL,
        check=True
    )

#-----------------------------------------------------------------------------
def modifyAndCommitFile(
    filename,
    contents = 'default contents',
    commitMsg = 'Default commit message'
):
    """
    Replace the contents of the specified file with the specified contents, in
    the current working directory then 'git add' and 'git commit'.

    Throws an error if the file does not already exist.

    Args
        String filename  - The name of the file
        String contents  - The contents to be written to the file
        String commitMsg - The commit message to use
    """
    if (not os.path.isfile(filename)):
        raise Exception('File does not exist')

    modifiedFile = open(filename, 'w')
    modifiedFile.write(contents)
    modifiedFile.close()
    execute(['git', 'add', filename])
    execute(['git', 'commit', '-m', commitMsg])

#-----------------------------------------------------------------------------
class Test_fsGetConfigFullyQualifiedFilename(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def testNoneFound(self):
        self.assertEqual(None, gs.fsGetConfigFullyQualifiedFilename())

    def testCurrentFolder(self):
        EXPECTED_PATH = os.path.join(os.getcwd(), gs.CONFIG_FILENAME)

        configFile = open(gs.CONFIG_FILENAME, 'w')
        configFile.close()

        self.assertEqual(
            EXPECTED_PATH,
            gs.fsGetConfigFullyQualifiedFilename()
        )

    def testParentFolder(self):
        CHILD_FOLDER = 'childFolder'
        EXPECTED_PATH = os.path.join(os.getcwd(), gs.CONFIG_FILENAME)

        configFile = open(gs.CONFIG_FILENAME, 'w')
        configFile.close()

        os.mkdir(CHILD_FOLDER)
        os.chdir(CHILD_FOLDER)

        self.assertEqual(
            EXPECTED_PATH,
            gs.fsGetConfigFullyQualifiedFilename()
        )

#-----------------------------------------------------------------------------
class Test_fsGetConfigToUse(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #   - Opening, parsing, and validating the user's configuration file are
    #     performed (and thus tested) in other functions
    #   - So here we're just testing the high level if/else structure
    #-------------------------------------------------------------------------
    def testValidUserConfig(self):
        CONFIG = [
            '{',
            '    "' + gs.KEY_CONFIG_BRANCH_ORDER   + '": ["^master$"],',
            '    "' + gs.KEY_CONFIG_DEFAULT_TARGET + '": "dev",',
            '    "' + gs.KEY_CONFIG_BRANCHES       + '": [',
            '        {',
            '            "' + gs.KEY_CONFIG_BRANCH_NAME   + '": "^feature$",',
            '            "' + gs.KEY_CONFIG_BRANCH_TARGET + '": "dev"',
            '        }',
            '    ]',
            '}'
        ]

        configFile = open(gs.CONFIG_FILENAME, 'w')
        for line in CONFIG:
            configFile.write(line)
        configFile.close()

        returnVal = gs.fsGetConfigToUse()

        self.assertTrue(returnVal[gs.KEY_RETURN_STATUS])
        self.assertEqual(0, len(returnVal[gs.KEY_RETURN_MESSAGES]))
        self.assertEqual(
            json.loads(''.join(CONFIG)),
            returnVal[gs.KEY_RETURN_VALUE]
        )

    def testNoUserConfig(self):
        returnVal = gs.fsGetConfigToUse()

        self.assertTrue(returnVal[gs.KEY_RETURN_STATUS])
        self.assertEqual(0, len(returnVal[gs.KEY_RETURN_MESSAGES]))
        self.assertEqual(gs.CONFIG_DEFAULT, returnVal[gs.KEY_RETURN_VALUE])

    def testInvalidUserConfig(self):
        CONFIG = '{}'
        configFile = open(gs.CONFIG_FILENAME, 'w')
        configFile.write(CONFIG)
        configFile.close()

        returnVal = gs.fsGetConfigToUse()

        self.assertFalse(returnVal[gs.KEY_RETURN_STATUS])
        self.assertTrue(len(returnVal[gs.KEY_RETURN_MESSAGES]) > 0)
        self.assertEqual(
            json.loads(CONFIG),
            returnVal[gs.KEY_RETURN_VALUE]
        )

#-----------------------------------------------------------------------------
class Test_fsGetValidatedUserConfig(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #   - Validation of the user configuration is performed (and thus tested)
    #     in other functions
    #   - So here we're just testing:
    #       - Reading the file, including removing comments
    #       - Returning correct status after validation
    #-------------------------------------------------------------------------
    def testValidConfigNoComments(self):
        CONFIG = [
            '{',
            '    "' + gs.KEY_CONFIG_BRANCH_ORDER   + '": ["^master$"],',
            '    "' + gs.KEY_CONFIG_DEFAULT_TARGET + '": "dev",',
            '    "' + gs.KEY_CONFIG_BRANCHES       + '": [',
            '        {',
            '            "' + gs.KEY_CONFIG_BRANCH_NAME   + '": "^feature$",',
            '            "' + gs.KEY_CONFIG_BRANCH_TARGET + '": "dev"',
            '        }',
            '    ]',
            '}'
        ]

        configFile = open(gs.CONFIG_FILENAME, 'w')
        for line in CONFIG:
            configFile.write(line + '\n')
        configFile.close()

        returnVal = gs.fsGetValidatedUserConfig(gs.CONFIG_FILENAME)

        self.assertTrue(returnVal[gs.KEY_RETURN_STATUS])
        self.assertEqual(0, len(returnVal[gs.KEY_RETURN_MESSAGES]))
        self.assertEqual(
            json.loads(''.join(CONFIG)),
            returnVal[gs.KEY_RETURN_VALUE]
        )

    def testValidConfigWithComments(self):
        CONFIG = [
            '{',
            '    "' + gs.KEY_CONFIG_BRANCH_ORDER   + '": ["^master$"],',
            '    "' + gs.KEY_CONFIG_DEFAULT_TARGET + '": "dev",',
            '    "' + gs.KEY_CONFIG_BRANCHES       + '": [',
            '        {',
            '            "' + gs.KEY_CONFIG_BRANCH_NAME   + '": "^feature$",',
            '            "' + gs.KEY_CONFIG_BRANCH_TARGET + '": "dev"',
            '        }',
            '    ]',
            '}'
        ]

        configFile = open(gs.CONFIG_FILENAME, 'w')
        for i, line in enumerate(CONFIG):
            if i == 1:
                configFile.write('// Comment at beginning of line\n')
                configFile.write('    // Indented comment\n')
            configFile.write(line + '\n')
        configFile.close()

        returnVal = gs.fsGetValidatedUserConfig(gs.CONFIG_FILENAME)

        self.assertTrue(returnVal[gs.KEY_RETURN_STATUS])
        self.assertEqual(0, len(returnVal[gs.KEY_RETURN_MESSAGES]))
        self.assertEqual(
            json.loads(''.join(CONFIG)),
            returnVal[gs.KEY_RETURN_VALUE]
        )

    def testInvalidConfig(self):
        CONFIG = '{}'

        configFile = open(gs.CONFIG_FILENAME, 'w')
        configFile.write(CONFIG + '\n')
        configFile.close()

        returnVal = gs.fsGetValidatedUserConfig(gs.CONFIG_FILENAME)

        self.assertFalse(returnVal[gs.KEY_RETURN_STATUS])
        self.assertTrue(len(returnVal[gs.KEY_RETURN_MESSAGES]) >0)
        self.assertEqual(
            json.loads(CONFIG),
            returnVal[gs.KEY_RETURN_VALUE]
        )

    def testErrorOpeningFile(self):
        returnVal = gs.fsGetValidatedUserConfig('file that does not exist')

        self.assertFalse(returnVal[gs.KEY_RETURN_STATUS])
        self.assertTrue(len(returnVal[gs.KEY_RETURN_MESSAGES]) >0)

#-----------------------------------------------------------------------------
class Test_gitGetCommitDetails(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def test(self):
        COMMIT_MSG = 'This is the message'

        createNonEmptyGitRepository()
        createAndCommitFile('newFile', '', COMMIT_MSG)

        # rev-list output will be:
        # commit [fullHash]
        # [shortHash]
        output = subprocess.check_output(
            ['git', 'rev-list', '--max-count=1', '--pretty=%h','master'],
            universal_newlines = True
        ).splitlines()
        fullHash = output[0].split(' ')[1]
        shortHash = output[1]

        expectedResult = {
            gs.KEY_COMMIT_SHORT_HASH: shortHash,
            gs.KEY_COMMIT_DESCRIPTION: COMMIT_MSG,
        }
        self.assertEqual(expectedResult, gs.gitGetCommitDetails(fullHash))

#-----------------------------------------------------------------------------
class Test_gitGetCommitsInFirstNotSecond(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def test_initialRepositoryState(self):
        execute(['git', 'init'])

        self.assertEqual(
            [],
            gs.gitGetCommitsInFirstNotSecond('master', 'origin/master', True),
        )

        self.assertEqual(
            [],
            gs.gitGetCommitsInFirstNotSecond('origin/master', 'master', True),
        )

    def test_initialRepositoryStateClonedFromRemote1(self):
        # This is the simple case where we:
        #   - clone an empty repository
        #   - immediately ask for the commits in one branch but not another
        LOCAL = 'local'
        createEmptyRemoteLocalPair('remote', LOCAL)
        os.chdir(LOCAL)

        self.assertEqual(
            [],
            gs.gitGetCommitsInFirstNotSecond('master', 'origin/master', True),
        )

        self.assertEqual(
            [],
            gs.gitGetCommitsInFirstNotSecond('origin/master', 'master', True),
        )

    def test_initialRepositoryStateClonedFromRemote2(self):
        # This is case where:
        #   - we clone an empty repository
        #   - commits get added to the remote
        #   - we fetch changes (but not pull)
        #   - we ask for the commits in one branch but not another

        # LOCAL1 will be the branch that is cloned from empty REMOTE
        # LOCAL2 will be used to make REMOTE ahead of LOCAL1
        LOCAL1 = 'local1'
        LOCAL2 = 'local2'
        REMOTE = 'remote'

        createEmptyRemoteLocalPair(REMOTE, LOCAL1)

        # Create LOCAL2 and use it to make REMOTE ahead of LOCAL1
        execute(['git', 'clone', REMOTE, LOCAL2])
        os.chdir(LOCAL2)
        createAndCommitFile('testRemote-local2-file1')
        execute(['git', 'push'])

        # Get the hash so we can ensure we're getting the right output
        expectedHash = subprocess.check_output(
            ['git', 'rev-list', '--max-count=1', 'master'],
            universal_newlines = True
        ).splitlines()[0]

        # Back to LOCAL1 and fetch so we'll know that there are commits
        # in the remote, but not local
        os.chdir('..')
        os.chdir(LOCAL1)
        execute(['git', 'fetch'])

        self.assertEqual(
            [],
            gs.gitGetCommitsInFirstNotSecond('master', 'origin/master', True),
        )

        self.assertEqual(
            [expectedHash],
            gs.gitGetCommitsInFirstNotSecond('origin/master', 'master', True),
        )

    def test_noCommitsInFirstNotSecond(self):
        NEW_BRANCH = 'newBranch'

        createNonEmptyGitRepository()
        execute(['git', 'checkout', '-b', NEW_BRANCH])

        self.assertEqual(
            [],
            gs.gitGetCommitsInFirstNotSecond('master', NEW_BRANCH, True),
        )

    def test_oneCommitInFirstNotSecond(self):
        NEW_BRANCH = 'newBranch'

        createNonEmptyGitRepository()
        execute(['git', 'checkout', '-b', NEW_BRANCH])
        createAndCommitFile('newFile')

        # Get the hash so we can ensure we're getting the right output
        # Not a super-robust test since it's using the same git command
        # as the function we're testing :-)
        expectedHash = subprocess.check_output(
            ['git', 'rev-list', '--max-count=1', NEW_BRANCH],
            universal_newlines = True
        ).splitlines()[0]

        commitList = gs.gitGetCommitsInFirstNotSecond(NEW_BRANCH, 'master', True)
        self.assertEqual(1, len(commitList))
        self.assertEqual(expectedHash, commitList[0])

    def test_multipleCommitsInFirstNotSecond(self):
        NEW_BRANCH = 'newBranch'

        createNonEmptyGitRepository()
        execute(['git', 'checkout', '-b', NEW_BRANCH])
        createAndCommitFile('newFile1')
        createAndCommitFile('newFile2')

        # Get the hashes so we can compare
        expectedHashes = subprocess.check_output(
            ['git', 'rev-list', '--max-count=2', NEW_BRANCH],
            universal_newlines = True
        ).splitlines()

        commitList = gs.gitGetCommitsInFirstNotSecond(NEW_BRANCH, 'master', True)

        self.assertEqual(2, len(commitList))
        for index in 0, 1:
            self.assertEqual(expectedHashes[index], commitList[index])

    def test_oneBranchIsRemote(self):
        LOCAL = 'local'

        createNonEmptyRemoteLocalPair('remote', LOCAL)

        os.chdir(LOCAL)
        createAndCommitFile('newFile1')
        createAndCommitFile('newFile2')

        # Get the hashes so we can compare
        expectedHashes = subprocess.check_output(
            ['git', 'rev-list', '--max-count=2', 'master'],
            universal_newlines = True
        ).splitlines()

        commitList = gs.gitGetCommitsInFirstNotSecond('master', 'origin/master', True)

        self.assertEqual(2, len(commitList))
        for index in 0, 1:
            self.assertEqual(expectedHashes[index], commitList[index])

#-----------------------------------------------------------------------------
class Test_gitGetCurrentBranch(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------

    #
    # First the oddball cases where there are no refs
    #
    def test_initialRepositoryState(self):
        EXPECTED_BRANCH = 'master'
        execute(['git', 'init'])

        self.assertEqual(EXPECTED_BRANCH, gs.gitGetCurrentBranch())

    def test_initialRepositoryStateNotMaster(self):
        EXPECTED_BRANCH = 'dev'

        execute(['git', 'init'])
        execute(['git', 'checkout', '-b', EXPECTED_BRANCH])

        self.assertEqual(EXPECTED_BRANCH, gs.gitGetCurrentBranch())

    def test_initialRepositoryStateFromClonedRemote(self):
        EXPECTED_BRANCH = 'master'

        LOCAL = 'local'
        createEmptyRemoteLocalPair('remote', LOCAL)
        os.chdir(LOCAL)

        self.assertEqual(EXPECTED_BRANCH, gs.gitGetCurrentBranch())

    #
    # Tests involving detached head state
    #
    def test_oneBranchDetachedHeadState(self):
        EXPECTED_BRANCH = ''

        createNonEmptyGitRepository()
        createAndCommitFile('newFile1')
        previousCommitHash = subprocess.check_output(
            ['git', 'rev-list', '--max-count=1', 'master'],
            universal_newlines = True
        ).splitlines()[0]

        createAndCommitFile('newFile2')
        execute(['git', 'checkout', previousCommitHash])

        self.assertEqual(EXPECTED_BRANCH, gs.gitGetCurrentBranch())

    def test_multipleBranchesDetachedHeadState(self):
        EXPECTED_BRANCH = ''

        createNonEmptyGitRepository()
        createAndCommitFile('newFile1')
        previousCommitHash = subprocess.check_output(
            ['git', 'rev-list', '--max-count=1', 'master'],
            universal_newlines = True
        ).splitlines()[0]

        createAndCommitFile('newFile2')
        execute(['git', 'checkout', '-b', 'dev'])
        execute(['git', 'checkout', previousCommitHash])

        self.assertEqual(EXPECTED_BRANCH, gs.gitGetCurrentBranch())


    #
    # Now the "regular" cases where we can rely on refs existing
    #
    def test_oneBranchExists(self):
        EXPECTED_BRANCH = 'master'

        createNonEmptyGitRepository()
        self.assertEqual(EXPECTED_BRANCH, gs.gitGetCurrentBranch())

    def test_multipleBranchesExist(self):
        EXPECTED_BRANCH = 'dev'

        createNonEmptyGitRepository()
        execute(['git', 'checkout', '-b', EXPECTED_BRANCH])

        self.assertEqual(EXPECTED_BRANCH, gs.gitGetCurrentBranch())

#-----------------------------------------------------------------------------
class Test_gitGetFileStatuses(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Helper functions that run a test for passed-in filename
    #-------------------------------------------------------------------------
    def util_testStageAddedFile(self, testFile):
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGE: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'A',
                    gs.KEY_FILE_STATUSES_FILENAME: testFile
                },
            ],
            gs.KEY_FILE_STATUSES_WORK_DIR: [],
            gs.KEY_FILE_STATUSES_UNMERGED: [],
            gs.KEY_FILE_STATUSES_UNTRACKED: [],
            gs.KEY_FILE_STATUSES_UNKNOWN: [],
        }

        createNonEmptyGitRepository()
        modifiedFile = open(testFile, 'w')
        modifiedFile.write('a')
        modifiedFile.close()
        execute(['git', 'add', testFile])

        self.assertEqual(EXPECTED_RESULT, gs.gitGetFileStatuses())

    def util_testStageDeletedFile(self, testFile):
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGE: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'D',
                    gs.KEY_FILE_STATUSES_FILENAME: testFile,
                },
            ],
            gs.KEY_FILE_STATUSES_WORK_DIR: [],
            gs.KEY_FILE_STATUSES_UNMERGED: [],
            gs.KEY_FILE_STATUSES_UNTRACKED: [],
            gs.KEY_FILE_STATUSES_UNKNOWN: [],
        }

        createNonEmptyGitRepository()
        createAndCommitFile(testFile)
        execute(['git', 'rm', testFile])

        self.assertEqual(EXPECTED_RESULT, gs.gitGetFileStatuses())

    def util_testStageModifiedFile(self, testFile):
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGE: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'M',
                    gs.KEY_FILE_STATUSES_FILENAME: testFile,
                },
            ],
            gs.KEY_FILE_STATUSES_WORK_DIR: [],
            gs.KEY_FILE_STATUSES_UNMERGED: [],
            gs.KEY_FILE_STATUSES_UNTRACKED: [],
            gs.KEY_FILE_STATUSES_UNKNOWN: [],
        }

        createNonEmptyGitRepository()
        createAndCommitFile(testFile)
        modifiedFile = open(testFile, 'w')
        modifiedFile.write('a')
        modifiedFile.close()
        execute(['git', 'add', testFile])

        self.assertEqual(EXPECTED_RESULT, gs.gitGetFileStatuses())

    def util_testStageRenamedFile(self, testFile):
        TEST_FILE_RENAMED = testFile + 'renamed'
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGE: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'R',
                    gs.KEY_FILE_STATUSES_FILENAME: testFile,
                    gs.KEY_FILE_STATUSES_NEW_FILENAME: TEST_FILE_RENAMED,
                    gs.KEY_FILE_STATUSES_HEURISTIC_SCORE: '100',
                },
            ],
            gs.KEY_FILE_STATUSES_WORK_DIR: [],
            gs.KEY_FILE_STATUSES_UNMERGED: [],
            gs.KEY_FILE_STATUSES_UNTRACKED: [],
            gs.KEY_FILE_STATUSES_UNKNOWN: [],
        }

        createNonEmptyGitRepository()
        createAndCommitFile(testFile)
        execute(['git', 'mv', testFile, TEST_FILE_RENAMED])

        self.assertEqual(EXPECTED_RESULT, gs.gitGetFileStatuses())

    def util_testWorkDirDeletedFile(self, testFile):
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGE: [],
            gs.KEY_FILE_STATUSES_WORK_DIR: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'D',
                    gs.KEY_FILE_STATUSES_FILENAME: testFile,
                },
            ],
            gs.KEY_FILE_STATUSES_UNMERGED: [],
            gs.KEY_FILE_STATUSES_UNTRACKED: [],
            gs.KEY_FILE_STATUSES_UNKNOWN: [],
        }

        createNonEmptyGitRepository()
        createAndCommitFile(testFile)
        os.remove(testFile)

        self.assertEqual(EXPECTED_RESULT, gs.gitGetFileStatuses())

    def util_testWorkDirModifiedFile(self, testFile):
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGE: [],
            gs.KEY_FILE_STATUSES_WORK_DIR: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'M',
                    gs.KEY_FILE_STATUSES_FILENAME: testFile,
                },
            ],
            gs.KEY_FILE_STATUSES_UNMERGED: [],
            gs.KEY_FILE_STATUSES_UNTRACKED: [],
            gs.KEY_FILE_STATUSES_UNKNOWN: [],
        }

        createNonEmptyGitRepository()
        createAndCommitFile(testFile)

        modifiedFile = open(testFile, 'w')
        modifiedFile.write('a')
        modifiedFile.close()

        self.assertEqual(EXPECTED_RESULT, gs.gitGetFileStatuses())

    def util_testUnmergedFile(self, testFile1, testFile2):
        # Unmerged files are created by merge conflicts.
        # Files that are added by both branches are signified by 'A'
        # Files that are modified by both branches are signified by 'U'
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGE: [],
            gs.KEY_FILE_STATUSES_WORK_DIR: [],
            gs.KEY_FILE_STATUSES_UNMERGED: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'U',
                    gs.KEY_FILE_STATUSES_FILENAME: testFile1,
                },
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'A',
                    gs.KEY_FILE_STATUSES_FILENAME: testFile2,
                },
            ],
            gs.KEY_FILE_STATUSES_UNTRACKED: [],
            gs.KEY_FILE_STATUSES_UNKNOWN: [],
        }

        # BRANCH1 and BRANCH2 will each:
        #   - modify testFile1
        #   - add testFile2
        BRANCH1 = 'branch1'
        BRANCH2 = 'branch2'

        # Create the common git history on master that each branch will work from
        execute(['git', 'init'])
        createAndCommitFile(testFile1)

        # Make the changes in BRANCH1
        execute(['git', 'checkout', '-b', BRANCH1, 'master'])
        modifyAndCommitFile(testFile1, 'abcde')
        createAndCommitFile(testFile2, 'abcde')

        # Make the changes in BRANCH2
        execute(['git', 'checkout', '-b', BRANCH2, 'master'])
        modifyAndCommitFile(testFile1, 'fghij')
        createAndCommitFile(testFile2, 'fghij')

        # Merge BRANCH1 into BRANCH2, thereby causing the merge conflicts.
        # Can't use execute() helper since 'git merge' will return a non-zero
        # exit status
        subprocess.run(
            ['git', 'merge', BRANCH1],
            stdout = subprocess.DEVNULL,
            stderr = subprocess.DEVNULL,
            check=False
        )

        self.assertEqual(EXPECTED_RESULT, gs.gitGetFileStatuses())

    def util_testUntrackedFile(self, testFile):
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGE: [],
            gs.KEY_FILE_STATUSES_WORK_DIR: [],
            gs.KEY_FILE_STATUSES_UNMERGED: [],
            gs.KEY_FILE_STATUSES_UNTRACKED: [testFile],
            gs.KEY_FILE_STATUSES_UNKNOWN: [],
        }

        createNonEmptyGitRepository()
        newFile = open(testFile, 'w')
        newFile.write('a')
        newFile.close()

        self.assertEqual(EXPECTED_RESULT, gs.gitGetFileStatuses())

    #-------------------------------------------------------------------------
    # Tests
    #   - Note: 'git status' docs suggest that it can detect copies in addition
    #           to renames. However according to the following thread, it appears
    #           that it can't, hence no tests for it.
    #               https://marc.info/?l=git&m=141730775928542&w=2
    #-------------------------------------------------------------------------
    def test_initialRepositoryStateNothingToReport(self):
        execute(['git', 'init'])

        statuses = gs.gitGetFileStatuses()
        self.assertEqual([], statuses[gs.KEY_FILE_STATUSES_STAGE])
        self.assertEqual([], statuses[gs.KEY_FILE_STATUSES_WORK_DIR])
        self.assertEqual([], statuses[gs.KEY_FILE_STATUSES_UNMERGED])
        self.assertEqual([], statuses[gs.KEY_FILE_STATUSES_UNTRACKED])
        self.assertEqual([], statuses[gs.KEY_FILE_STATUSES_UNKNOWN])

    def test_initialRepositoryStateStageAddedFile(self):
        TEST_FILE = 'testfile'
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGE: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'A',
                    gs.KEY_FILE_STATUSES_FILENAME: TEST_FILE,
                },
            ],
            gs.KEY_FILE_STATUSES_WORK_DIR: [],
            gs.KEY_FILE_STATUSES_UNMERGED: [],
            gs.KEY_FILE_STATUSES_UNTRACKED: [],
            gs.KEY_FILE_STATUSES_UNKNOWN: [],
        }

        execute(['git', 'init'])

        modifiedFile = open(TEST_FILE, 'w')
        modifiedFile.write('a')
        modifiedFile.close()
        execute(['git', 'add', TEST_FILE])

        self.assertEqual(EXPECTED_RESULT, gs.gitGetFileStatuses())

    def test_initialRepositoryStateUntrackedFile(self):
        TEST_FILE = 'testfile'
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGE: [],
            gs.KEY_FILE_STATUSES_WORK_DIR: [],
            gs.KEY_FILE_STATUSES_UNMERGED: [],
            gs.KEY_FILE_STATUSES_UNTRACKED: [TEST_FILE],
            gs.KEY_FILE_STATUSES_UNKNOWN: [],
        }

        execute(['git', 'init'])

        newFile = open(TEST_FILE, 'w')
        newFile.write('a')
        newFile.close()

        self.assertEqual(EXPECTED_RESULT, gs.gitGetFileStatuses())

    def test_nothingToReport(self):
        createNonEmptyGitRepository()
        statuses = gs.gitGetFileStatuses()
        self.assertEqual([], statuses[gs.KEY_FILE_STATUSES_STAGE])
        self.assertEqual([], statuses[gs.KEY_FILE_STATUSES_WORK_DIR])
        self.assertEqual([], statuses[gs.KEY_FILE_STATUSES_UNMERGED])
        self.assertEqual([], statuses[gs.KEY_FILE_STATUSES_UNTRACKED])
        self.assertEqual([], statuses[gs.KEY_FILE_STATUSES_UNKNOWN])

    # Tests for each type of file status
    def test_stageAddedFile(self):
        self.util_testStageAddedFile('testfile')

    def test_stageDeletedFile(self):
        self.util_testStageDeletedFile('testfile')

    def test_stageModifiedFile(self):
        self.util_testStageModifiedFile('testfile')

    def test_stageRenamedFile(self):
        self.util_testStageRenamedFile('testfile')

    def test_workDirDeletedFile(self):
        self.util_testWorkDirDeletedFile('testfile')

    def test_workDirModifiedFile(self):
        self.util_testWorkDirModifiedFile('testfile')

    def test_unmergedFile(self):
        self.util_testUnmergedFile('testfile1', 'testfile2')

    def test_untrackedFile(self):
        self.util_testUntrackedFile('testfile')

    # Tests for each type of file status, where filenames have spaces
    def test_stageAddedFileWithSpaces(self):
        self.util_testStageAddedFile('testfile with spaces')

    def test_stageDeletedFileWithSpaces(self):
        self.util_testStageDeletedFile('testfile with spaces')

    def test_stageModifiedFileWithSpaces(self):
        self.util_testStageModifiedFile('testfile with spaces')

    def test_stageRenamedFileWithSpaces(self):
        self.util_testStageRenamedFile('testfile with spaces')

    def test_workDirDeletedFileWithSpaces(self):
        self.util_testWorkDirDeletedFile('testfile with spaces')

    def test_workDirModifiedFileWithSpaces(self):
        self.util_testWorkDirModifiedFile('testfile with spaces')

    def test_unmergedFileWithSpaces(self):
        self.util_testUnmergedFile('testfile1 with spaces', 'testfile2 with spaces')

    def test_untrackedFileWithSpaces(self):
        self.util_testUntrackedFile('testfile with spaces')

    def test_multipleStatusesType1(self):
        # This test corresponds to the git status line of type '1'.
        # (One file modified in the stage and also modified in work dir.)
        # We accomplish this by doing the following:
        #   - commit a new file
        #   - make a change and stage it
        #   - make another change in the working directory

        TEST_FILE = 'testfile'
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGE: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'M',
                    gs.KEY_FILE_STATUSES_FILENAME: TEST_FILE,
                },
            ],
            gs.KEY_FILE_STATUSES_WORK_DIR: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'M',
                    gs.KEY_FILE_STATUSES_FILENAME: TEST_FILE,
                },
            ],
            gs.KEY_FILE_STATUSES_UNMERGED: [],
            gs.KEY_FILE_STATUSES_UNTRACKED: [],
            gs.KEY_FILE_STATUSES_UNKNOWN: [],
        }

        createNonEmptyGitRepository()

        # Create and commit
        createAndCommitFile(TEST_FILE)

        # Modify and stage
        modifiedFile = open(TEST_FILE, 'w')
        modifiedFile.write('a')
        modifiedFile.close()
        execute(['git', 'add', TEST_FILE])

        # Modify but don't stage
        modifiedFile = open(TEST_FILE, 'w')
        modifiedFile.write('b')
        modifiedFile.close()

        self.assertEqual(EXPECTED_RESULT, gs.gitGetFileStatuses())

    def test_multipleStatusesType2(self):
        # This test corresponds to the git status line of type '2'.
        # (One file renamed in the stage and modified in work dir.)
        # We accomplish this by doing the following:
        #   - commit a new file
        #   - rename the file (staged)
        #   - make a change to the renamed file in the working directory

        TEST_FILE = 'testfile'
        RENAMED_FILE = 'testfile-renamed'

        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGE: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'R',
                    gs.KEY_FILE_STATUSES_FILENAME: TEST_FILE,
                    gs.KEY_FILE_STATUSES_NEW_FILENAME: RENAMED_FILE,
                    gs.KEY_FILE_STATUSES_HEURISTIC_SCORE: '100',
                },
            ],
            gs.KEY_FILE_STATUSES_WORK_DIR: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'M',
                    gs.KEY_FILE_STATUSES_FILENAME: RENAMED_FILE,
                },
            ],
            gs.KEY_FILE_STATUSES_UNMERGED: [],
            gs.KEY_FILE_STATUSES_UNTRACKED: [],
            gs.KEY_FILE_STATUSES_UNKNOWN: [],
        }

        createNonEmptyGitRepository()

        # Create and commit
        createAndCommitFile(TEST_FILE)

        # Rename and stage
        execute(['git', 'mv', TEST_FILE, RENAMED_FILE])

        # Modify but don't stage
        modifiedFile = open(RENAMED_FILE, 'w')
        modifiedFile.write('b')
        modifiedFile.close()

        self.assertEqual(EXPECTED_RESULT, gs.gitGetFileStatuses())

    def test_multipleFiles(self):
        # This is a test with multiple files in each category. No pattern other
        # than trying to exercise something you'd expect in real life.
        #
        # Scenario
        #   - file1 is renamed in the stage
        #   - file2 is modified in the stage
        #   - file3 is modified in the working directory
        #   - file4 is deleted in the working directory
        #   - file5 is untracked
        #   - file6 is untracked
        TEST_FILE1 = 'testfile1'
        TEST_FILE1_RENAMED = 'testfile1-renamed'
        TEST_FILE2 = 'testfile2'
        TEST_FILE3 = 'testfile3'
        TEST_FILE4 = 'testfile4'
        TEST_FILE5 = 'testfile5'
        TEST_FILE6 = 'testfile6'
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGE: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'R',
                    gs.KEY_FILE_STATUSES_FILENAME: TEST_FILE1,
                    gs.KEY_FILE_STATUSES_NEW_FILENAME: TEST_FILE1_RENAMED,
                    gs.KEY_FILE_STATUSES_HEURISTIC_SCORE: '100',
                },
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'M',
                    gs.KEY_FILE_STATUSES_FILENAME: TEST_FILE2,
                },
            ],
            gs.KEY_FILE_STATUSES_WORK_DIR: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'M',
                    gs.KEY_FILE_STATUSES_FILENAME: TEST_FILE3,
                },
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'D',
                    gs.KEY_FILE_STATUSES_FILENAME: TEST_FILE4,
                },
            ],
            gs.KEY_FILE_STATUSES_UNMERGED: [],
            gs.KEY_FILE_STATUSES_UNTRACKED: [
                TEST_FILE5,
                TEST_FILE6,
            ],
            gs.KEY_FILE_STATUSES_UNKNOWN: [],
        }

        createNonEmptyGitRepository()

        #---------------------------------------------------------------------
        # First commit files that need to be there (can't do this later, since
        # it'll end up committing things that we want in the stage)
        #---------------------------------------------------------------------
        for newFile in [TEST_FILE1, TEST_FILE2, TEST_FILE3, TEST_FILE4]:
            createAndCommitFile(newFile)

        #---------------------------------------------------------------------
        # Staged files
        #---------------------------------------------------------------------
        execute(['git', 'mv', TEST_FILE1, TEST_FILE1_RENAMED])

        modifiedStagedFile = open(TEST_FILE2, 'w')
        modifiedStagedFile.write('a')
        modifiedStagedFile.close()
        execute(['git', 'add', TEST_FILE2])

        #---------------------------------------------------------------------
        # Working directory files
        #---------------------------------------------------------------------
        modifiedWorkingDirFile = open(TEST_FILE3, 'w')
        modifiedWorkingDirFile.write('a')
        modifiedWorkingDirFile.close()

        os.remove(TEST_FILE4)

        #---------------------------------------------------------------------
        # Untracked files
        #---------------------------------------------------------------------
        for newFile in [TEST_FILE5, TEST_FILE6]:
            untrackedFile = open(newFile, 'w')
            untrackedFile.close()

        self.assertEqual(EXPECTED_RESULT, gs.gitGetFileStatuses())

#-----------------------------------------------------------------------------
class Test_gitGetLocalBranches(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------

    #
    # First the oddball cases where there are no refs
    #
    def test_initialRepositoryState(self):
        EXPECTED_BRANCHES = ['master']

        execute(['git', 'init'])
        self.assertEqual(EXPECTED_BRANCHES, gs.gitGetLocalBranches())

    def test_initialRepositoryStateNotMaster(self):
        EXPECTED_BRANCHES = ['dev']

        execute(['git', 'init'])
        execute(['git', 'checkout', '-b', 'dev'])

        self.assertEqual(EXPECTED_BRANCHES, gs.gitGetLocalBranches())

    def test_initialRepositoryStateFromClonedRemote(self):
        EXPECTED_BRANCHES = ['master']

        LOCAL = 'local'
        createEmptyRemoteLocalPair('remote', LOCAL)
        os.chdir(LOCAL)

        self.assertEqual(EXPECTED_BRANCHES, gs.gitGetLocalBranches())

    #
    # Tests involving detached head state
    #
    def test_oneBranchDetachedHeadState(self):
        EXPECTED_BRANCHES = ['master']

        createNonEmptyGitRepository()
        createAndCommitFile('newFile1')
        previousCommitHash = subprocess.check_output(
            ['git', 'rev-list', '--max-count=1', 'master'],
            universal_newlines = True
        ).splitlines()[0]

        createAndCommitFile('newFile2')
        execute(['git', 'checkout', previousCommitHash])

        self.assertEqual(EXPECTED_BRANCHES, gs.gitGetLocalBranches())

    def test_multipleBranchesDetachedHeadState(self):
        EXPECTED_BRANCHES = ['dev', 'master']

        createNonEmptyGitRepository()
        createAndCommitFile('newFile1')
        previousCommitHash = subprocess.check_output(
            ['git', 'rev-list', '--max-count=1', 'master'],
            universal_newlines = True
        ).splitlines()[0]

        createAndCommitFile('newFile2')
        execute(['git', 'checkout', '-b', 'dev'])
        execute(['git', 'checkout', previousCommitHash])

        self.assertEqual(EXPECTED_BRANCHES, gs.gitGetLocalBranches())

    #
    # Now the "regular" cases where we can rely on refs existing
    #
    def test_oneBranch(self):
        EXPECTED_BRANCHES = ['master']

        createNonEmptyGitRepository()
        self.assertEqual(EXPECTED_BRANCHES, gs.gitGetLocalBranches())

    def test_multipleBranchesExist(self):
        NEW_BRANCH = 'dev'
        EXPECTED_BRANCHES = [NEW_BRANCH, 'master']
        EXPECTED_BRANCHES.sort()

        createNonEmptyGitRepository()
        execute(['git', 'checkout', '-b', NEW_BRANCH])

        self.assertEqual(EXPECTED_BRANCHES, gs.gitGetLocalBranches())

    def test_remoteTrackingBranchExists(self):
        LOCAL = 'local'
        EXPECTED_BRANCHES = ['master']

        createNonEmptyRemoteLocalPair('remote', LOCAL)
        os.chdir(LOCAL)

        self.assertEqual(EXPECTED_BRANCHES, gs.gitGetLocalBranches())

#-----------------------------------------------------------------------------
class Test_gitGetRemoteTrackingBranch(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------

    #
    # First the oddball cases where there are no refs
    #
    def test_initialRepositoryStateNoRemote(self):
        execute(['git', 'init'])

        self.assertEqual('', gs.gitGetRemoteTrackingBranch(''))
        self.assertEqual('', gs.gitGetRemoteTrackingBranch('master'))

    def test_initialRepositoryStateNoRemoteNotMaster(self):
        execute(['git', 'init'])
        execute(['git', 'checkout', '-b', 'dev'])

        self.assertEqual('', gs.gitGetRemoteTrackingBranch(''))
        self.assertEqual('', gs.gitGetRemoteTrackingBranch('dev'))

    def test_initialRepositoryStateWithRemote(self):
        LOCAL = 'local'
        createEmptyRemoteLocalPair('remote', LOCAL)
        os.chdir(LOCAL)

        self.assertEqual(''             , gs.gitGetRemoteTrackingBranch(''))
        self.assertEqual('origin/master', gs.gitGetRemoteTrackingBranch('master'))

    #
    # Tests involving detached head state
    #
    def test_noRemoteRepositoryOneBranchDetachedHeadState(self):
        createNonEmptyGitRepository()
        createAndCommitFile('newFile1')
        previousCommitHash = subprocess.check_output(
            ['git', 'rev-list', '--max-count=1', 'master'],
            universal_newlines = True
        ).splitlines()[0]

        createAndCommitFile('newFile2')
        execute(['git', 'checkout', previousCommitHash])

        self.assertEqual('', gs.gitGetRemoteTrackingBranch(''))
        self.assertEqual('', gs.gitGetRemoteTrackingBranch('master'))

    def test_noRemoteRepositoryMultipleBranchesDetachedHeadState(self):
        createNonEmptyGitRepository()
        createAndCommitFile('newFile1')
        previousCommitHash = subprocess.check_output(
            ['git', 'rev-list', '--max-count=1', 'master'],
            universal_newlines = True
        ).splitlines()[0]

        createAndCommitFile('newFile2')
        execute(['git', 'checkout', '-b', 'dev'])
        execute(['git', 'checkout', previousCommitHash])

        self.assertEqual('', gs.gitGetRemoteTrackingBranch(''))
        self.assertEqual('', gs.gitGetRemoteTrackingBranch('master'))
        self.assertEqual('', gs.gitGetRemoteTrackingBranch('dev'))

    def test_withRemoteRepositoryOneBranchDetachedHeadState(self):
        LOCAL = 'local'

        createNonEmptyRemoteLocalPair('remote', LOCAL)
        os.chdir(LOCAL)
        createAndCommitFile('newFile1')

        previousCommitHash = subprocess.check_output(
            ['git', 'rev-list', '--max-count=1', 'master'],
            universal_newlines = True
        ).splitlines()[0]

        createAndCommitFile('newFile2')
        execute(['git', 'checkout', previousCommitHash])

        self.assertEqual(''             , gs.gitGetRemoteTrackingBranch(''))
        self.assertEqual('origin/master', gs.gitGetRemoteTrackingBranch('master'))

    def test_withRemoteRepositoryMultipleBranchesDetachedHeadState(self):
        LOCAL = 'local'

        createNonEmptyRemoteLocalPair('remote', LOCAL)
        os.chdir(LOCAL)
        createAndCommitFile('newFile1')

        previousCommitHash = subprocess.check_output(
            ['git', 'rev-list', '--max-count=1', 'master'],
            universal_newlines = True
        ).splitlines()[0]

        createAndCommitFile('newFile2')
        execute(['git', 'checkout', '-b' 'dev'])
        execute(['git', 'checkout', previousCommitHash])

        self.assertEqual(''             , gs.gitGetRemoteTrackingBranch(''))
        self.assertEqual(''             , gs.gitGetRemoteTrackingBranch('dev'))
        self.assertEqual('origin/master', gs.gitGetRemoteTrackingBranch('master'))

    #
    # Now the "regular" cases where we can rely on refs existing
    #
    def test_noRemoteRepository(self):
        createNonEmptyGitRepository()
        self.assertEqual('', gs.gitGetRemoteTrackingBranch(''))
        self.assertEqual('', gs.gitGetRemoteTrackingBranch('master'))

    def test_withRemoteRepository(self):
        LOCAL = 'local'

        createNonEmptyRemoteLocalPair('remote', LOCAL)
        os.chdir(LOCAL)
        execute(['git', 'checkout', '-b', 'dev'])

        self.assertEqual(''             , gs.gitGetRemoteTrackingBranch(''))
        self.assertEqual(''             , gs.gitGetRemoteTrackingBranch('dev'))
        self.assertEqual('origin/master', gs.gitGetRemoteTrackingBranch('master'))

#-----------------------------------------------------------------------------
class Test_gitGetStashes(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def test_initialRepositoryState(self):
        execute(['git', 'init'])
        self.assertEqual([], gs.gitGetStashes())

    def test_noStashes(self):
        createNonEmptyGitRepository()
        self.assertEqual([], gs.gitGetStashes())

    def test_oneStash(self):
        TEST_FILENAME = 'testfile'

        createNonEmptyGitRepository()

        # Commit a new file
        createAndCommitFile(TEST_FILENAME)

        # Make changes to the file and then stash it
        modifiedFile = open(TEST_FILENAME, 'w')
        modifiedFile.write('The front fell off')
        modifiedFile.close()
        execute(['git', 'stash'])

        stashes = gs.gitGetStashes()
        self.assertEqual(1, len(stashes))

        # Test the contents, but be a bit lazy
        #   hash        - just make sure it's 40 alphanumeric character
        #   description - This seems like it could change with later git
        #                 versions, so just confirm it's a string
        oneStash = stashes[0]
        self.assertEqual(40, len(oneStash[gs.KEY_STASH_FULL_HASH]))
        self.assertTrue(re.match('^[0-9a-z]+$', oneStash[gs.KEY_STASH_FULL_HASH]))

        self.assertEqual('stash@{0}', oneStash[gs.KEY_STASH_NAME])
        self.assertTrue(isinstance(oneStash[gs.KEY_STASH_DESCRIPTION], str))

    def test_multipleStashes(self):
        TEST_FILENAME = 'testfile'

        createNonEmptyGitRepository()

        # Commit a new file
        createAndCommitFile(TEST_FILENAME)

        # Make changes to the file and create our first stash
        modifiedFile = open(TEST_FILENAME, 'w')
        modifiedFile.write('The front fell off')
        modifiedFile.close()
        execute(['git', 'stash'])

        # Make more changes to the file and create our second stash
        modifiedFile = open(TEST_FILENAME, 'w')
        modifiedFile.write('It\'s *beyond* the environment')
        modifiedFile.close()
        execute(['git', 'stash'])

        stashes = gs.gitGetStashes()
        self.assertEqual(2, len(stashes))

        # Test the contents, but be a bit lazy
        #   hash        - just make sure it's 40 alphanumeric character
        #   description - This seems like it could change with later git
        #                 versions, so just confirm it's a string
        for oneStash in stashes:
            self.assertEqual(40, len(oneStash[gs.KEY_STASH_FULL_HASH]))
            self.assertTrue(re.match('^[0-9a-z]+$', oneStash[gs.KEY_STASH_FULL_HASH]))

            self.assertTrue(re.match('^stash@{[0-9]+}$', oneStash[gs.KEY_STASH_NAME]))
            self.assertTrue(isinstance(oneStash[gs.KEY_STASH_DESCRIPTION], str))

#-----------------------------------------------------------------------------
# Placeholders for:
#   gitUtilGetOutput()            - No tests since it's implicitly tested by
#                                   everything else
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
class Test_utilGetAheadBehindString(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def test(self):
        AHEAD = 'ahead'
        BEHIND = 'behind'
        RESULT = 'result'
        SEP = '  '

        testCases = [
            { AHEAD: ''  , BEHIND: ''  , RESULT: '    ' + SEP + '    ', },
            { AHEAD: 0   , BEHIND: 0   , RESULT: '   .' + SEP + '.   ', },
            { AHEAD: 1   , BEHIND: 1   , RESULT: '  +1' + SEP + '-1  ', },
            { AHEAD: 100 , BEHIND: 100 , RESULT: '+100' + SEP + '-100', },
            { AHEAD: 999 , BEHIND: 999 , RESULT: '+999' + SEP + '-999', },
            { AHEAD: 1000, BEHIND: 1000, RESULT: '>999' + SEP + '>999', },
        ]

        for case in testCases:
            self.assertEqual(
                case[RESULT],
                gs.utilGetAheadBehindString(case[AHEAD], case[BEHIND])
            )

#-----------------------------------------------------------------------------
class Test_utilGetBranchAsFiveColumns(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #
    # Obviously we don't test all combinations of column values.
    # Since the function being tested is mostly assembling info from other
    # already-tested functions, we just need to confirm that proper info gets
    # into the proper columns.
    #-------------------------------------------------------------------------
    def testCurrentBranchYes(self):
        # We're only testing current branch indicator
        CURRENT_BRANCH = 'dev'
        createNonEmptyGitRepository()
        execute(['git', 'checkout', '-b', CURRENT_BRANCH])

        result = gs.utilGetBranchAsFiveColumns(
            CURRENT_BRANCH,
            CURRENT_BRANCH,
            ''
        )

        self.assertEqual('*', result[0])
        self.assertEqual(CURRENT_BRANCH, result[1])
        self.assertEqual(gs.utilGetAheadBehindString('', ''), result[2])
        self.assertEqual(gs.utilGetAheadBehindString('', ''), result[3])
        self.assertEqual('', result[4])

    def testCurrentBranchNo(self):
        # We're only testing current branch indicator
        CURRENT_BRANCH = 'master'
        createNonEmptyGitRepository()
        execute(['git', 'checkout', '-b', 'dev'])

        result = gs.utilGetBranchAsFiveColumns(
            'dev',
            CURRENT_BRANCH,
            ''
        )

        self.assertEqual('', result[0])
        self.assertEqual(CURRENT_BRANCH, result[1])
        self.assertEqual(gs.utilGetAheadBehindString('', ''), result[2])
        self.assertEqual(gs.utilGetAheadBehindString('', ''), result[3])
        self.assertEqual('', result[4])

    def testRemote(self):
        # Test the ahead/behind functionality for a remote branch.
        # Branch will be ahead 1 and behind 2 relative to remote

        # LOCAL1 will be the branch we test the function with.
        # LOCAL2 is used to make REMOTE ahead of LOCAL1
        LOCAL1 = 'local1'
        LOCAL2 = 'local2'
        REMOTE = 'remote'

        createNonEmptyRemoteLocalPair(REMOTE, LOCAL1)

        # Create LOCAL2 and use it to make LOCAL1 behind REMOTE by 2 commits
        execute(['git', 'clone', REMOTE, LOCAL2])
        os.chdir(LOCAL2)
        createAndCommitFile('testRemote-local2-file1')
        createAndCommitFile('testRemote-local2-file2')
        execute(['git', 'push'])

        # Make LOCAL1 ahead of REMOTE by 1 commit
        os.chdir('..')
        os.chdir(LOCAL1)
        createAndCommitFile('testRemote-local1-file1')

        # Update remote tracking branch
        execute(['git', 'fetch'])

        result = gs.utilGetBranchAsFiveColumns(
            'master',
            'master',
            ''
        )

        self.assertEqual('*', result[0])
        self.assertEqual('master', result[1])
        self.assertEqual(gs.utilGetAheadBehindString(1, 2), result[2])
        self.assertEqual(gs.utilGetAheadBehindString('', ''), result[3])
        self.assertEqual('', result[4])

    def testTarget(self):
        # Test the ahead/behind functionality for a target branch.
        # Branch will be ahead 1 and behind 2 relative to target

        # TEST_BRANCH will be the branch we test the function with.
        # TARGET will be the, uh, target branch.
        TEST_BRANCH = 'testBranch'
        TARGET = 'master'

        createNonEmptyGitRepository()

        # Create our test branch and make it 1 commit ahead of the target
        execute(['git', 'checkout', '-b', TEST_BRANCH])
        createAndCommitFile('testBranch-file1')

        # Go back to the target and make it ahead of our test branch by 2
        # commits
        execute(['git', 'checkout', TARGET])
        createAndCommitFile('targetBranch-file1')
        createAndCommitFile('targetBranch-file2')

        result = gs.utilGetBranchAsFiveColumns(
            'master',
            TEST_BRANCH,
            TARGET
        )

        self.assertEqual('', result[0])
        self.assertEqual(TEST_BRANCH, result[1])
        self.assertEqual(gs.utilGetAheadBehindString('', ''), result[2])
        self.assertEqual(gs.utilGetAheadBehindString(1, 2), result[3])
        self.assertEqual(TARGET, result[4])

#-----------------------------------------------------------------------------
class Test_utilGetBranchOrder(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def testDefaultBranchOrder(self):
        BRANCHES = [
            'hotfix-oops2',
            'hotfix-oops',
            'make-something2',
            'make-something',
            'release-1.0.0',
            'develop',
            'master',
        ]

        ORDERED_BRANCHES = [
            'master',
            'develop',
            'hotfix-oops',
            'hotfix-oops2',
            'release-1.0.0',
            'make-something',
            'make-something2',
        ]
        self.assertEqual(
            ORDERED_BRANCHES,
            gs.utilGetBranchOrder(gs.CONFIG_DEFAULT, BRANCHES)
        )

    def testEmptyBranchPatterns(self):
        BRANCH_LIST = ['d', 'c', 'b', 'a']
        config = copy.deepcopy(gs.CONFIG_DEFAULT)
        config[gs.KEY_CONFIG_BRANCH_ORDER] = []

        self.assertEqual(
            sorted(BRANCH_LIST),
            gs.utilGetBranchOrder(config, BRANCH_LIST)
        )

    def testBranchPatternsZeroMatches(self):
        BRANCH_LIST = ['d', 'c', 'b', 'a']
        config = copy.deepcopy(gs.CONFIG_DEFAULT)
        config[gs.KEY_CONFIG_BRANCH_ORDER] = ['e', 'f']

        self.assertEqual(
            sorted(BRANCH_LIST),
            gs.utilGetBranchOrder(config, BRANCH_LIST)
        )

    def testBranchPatternsOneMatches(self):
        BRANCH_LIST = ['d', 'c', 'b', 'a']
        config = copy.deepcopy(gs.CONFIG_DEFAULT)
        config[gs.KEY_CONFIG_BRANCH_ORDER] = ['c', 'e']

        self.assertEqual(
            ['c', 'a', 'b', 'd'],
            gs.utilGetBranchOrder(config, BRANCH_LIST)
        )

    def testBranchPatternsMultipleMatches(self):
        BRANCH_LIST = ['d', 'c', 'b', 'a']
        config = copy.deepcopy(gs.CONFIG_DEFAULT)
        config[gs.KEY_CONFIG_BRANCH_ORDER] = ['c', 'b']

        self.assertEqual(
            ['c', 'b', 'a', 'd'],
            gs.utilGetBranchOrder(config, BRANCH_LIST)
        )

    def testOneBranchMatchesMultiplePatterns(self):
        BRANCH_LIST = ['e', 'd', 'c', 'b', 'a']
        config = copy.deepcopy(gs.CONFIG_DEFAULT)
        config[gs.KEY_CONFIG_BRANCH_ORDER] = ['e', 'e', 'c', 'b']

        self.assertEqual(
            ['e', 'c', 'b', 'a', 'd'],
            gs.utilGetBranchOrder(config, BRANCH_LIST)
        )

    def testPatternsTreatedAsRegularExpressions(self):
        BRANCH_LIST = [
            'elephant',
            'eagle',
            'deer',
            'cougar',
            'beagle',
            'alligator'
        ]
        config = copy.deepcopy(gs.CONFIG_DEFAULT)
        config[gs.KEY_CONFIG_BRANCH_ORDER] = ['^ea', 'ant$', 'oug']

        self.assertEqual(
            ['eagle', 'elephant', 'cougar', 'alligator', 'beagle', 'deer'],
            gs.utilGetBranchOrder(config, BRANCH_LIST)
        )

#-----------------------------------------------------------------------------
class Test_utilGetColumnAlignedLines(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def testNoLines(self):
        REQUIRED_WIDTH = 80
        TRUNC_INDICATOR = '...'
        VARIABLE_COLUMN = 3
        COLUMN_WIDTHS = [10, 10, 10, 10]
        LINES = []

        EXPECTED = []

        self.assertEqual(
            EXPECTED,
            gs.utilGetColumnAlignedLines(
                REQUIRED_WIDTH,
                TRUNC_INDICATOR,
                VARIABLE_COLUMN,
                COLUMN_WIDTHS,
                LINES
            )
        )

    def testNoModificationsRequired(self):
        REQUIRED_WIDTH = 43     # Remember column separators
        TRUNC_INDICATOR = '...'
        VARIABLE_COLUMN = 3
        COLUMN_WIDTHS = [10, 10, 10, 10]
        LINES = [
            ['1234567890', '1234567890', '1234567890', '1234567890'],
            ['1234567890', '1234567890', '1234567890', '1234567890'],
        ]

        EXPECTED = [
            ['1234567890', '1234567890', '1234567890', '1234567890'],
            ['1234567890', '1234567890', '1234567890', '1234567890'],
        ]

        self.assertEqual(
            EXPECTED,
            gs.utilGetColumnAlignedLines(
                REQUIRED_WIDTH,
                TRUNC_INDICATOR,
                VARIABLE_COLUMN,
                COLUMN_WIDTHS,
                LINES
            )
        )

    def testRequiredWidthTooNarrow(self):
        REQUIRED_WIDTH = 30     # Remember column separators
        TRUNC_INDICATOR = '...'
        VARIABLE_COLUMN = 3
        COLUMN_WIDTHS = [10, 10, 10, 10]
        LINES = [
            ['1234567890', '1234567890', '1234567890', '1234567890'],
            ['1234567890', '1234567890', '1234567890', '1234567890'],
        ]

        EXPECTED = [
            ['1234567890', '1234567890', '1234567890', '...'],
            ['1234567890', '1234567890', '1234567890', '...'],
        ]

        self.assertEqual(
            EXPECTED,
            gs.utilGetColumnAlignedLines(
                REQUIRED_WIDTH,
                TRUNC_INDICATOR,
                VARIABLE_COLUMN,
                COLUMN_WIDTHS,
                LINES
            )
        )

    def testNonVariableWidthColumnGetsPadded(self):
        REQUIRED_WIDTH = 43     # Remember column separators
        TRUNC_INDICATOR = '...'
        VARIABLE_COLUMN = 3
        COLUMN_WIDTHS = [10, 10, 10, 10]
        LINES = [
            ['1234567890', '123456789', '12345678', '1234567890'],
            ['1234567890', '123456789', '12345678', '1234567890'],
        ]

        EXPECTED = [
            ['1234567890', '123456789 ', '12345678  ', '1234567890'],
            ['1234567890', '123456789 ', '12345678  ', '1234567890'],
        ]

        self.assertEqual(
            EXPECTED,
            gs.utilGetColumnAlignedLines(
                REQUIRED_WIDTH,
                TRUNC_INDICATOR,
                VARIABLE_COLUMN,
                COLUMN_WIDTHS,
                LINES
            )
        )

    def testVariableWidthColumnPadAndTrunc(self):
        REQUIRED_WIDTH = 43     # Remember column separators
        TRUNC_INDICATOR = '...'
        VARIABLE_COLUMN = 3
        COLUMN_WIDTHS = [10, 10, 10, 10]
        LINES = [
            ['1234567890', '1234567890', '1234567890', '123456789'],
            ['1234567890', '1234567890', '1234567890', '1234567890a'],
        ]

        EXPECTED = [
            ['1234567890', '1234567890', '1234567890', '123456789 '],
            ['1234567890', '1234567890', '1234567890', '1234567...'],
        ]

        self.assertEqual(
            EXPECTED,
            gs.utilGetColumnAlignedLines(
                REQUIRED_WIDTH,
                TRUNC_INDICATOR,
                VARIABLE_COLUMN,
                COLUMN_WIDTHS,
                LINES
            )
        )

    def testZeroLengthTruncIndicator(self):
        REQUIRED_WIDTH = 43     # Remember column separators
        TRUNC_INDICATOR = ''
        VARIABLE_COLUMN = 3
        COLUMN_WIDTHS = [10, 10, 10, 10]
        LINES = [
            ['1234567890', '1234567890', '1234567890', '123456789'],
            ['1234567890', '1234567890', '1234567890', '1234567890a'],
        ]

        EXPECTED = [
            ['1234567890', '1234567890', '1234567890', '123456789 '],
            ['1234567890', '1234567890', '1234567890', '1234567890'],
        ]

        self.assertEqual(
            EXPECTED,
            gs.utilGetColumnAlignedLines(
                REQUIRED_WIDTH,
                TRUNC_INDICATOR,
                VARIABLE_COLUMN,
                COLUMN_WIDTHS,
                LINES
            )
        )

#-----------------------------------------------------------------------------
class Test_utilGetMaxColumnWidths(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def testNoLines(self):
        self.assertEqual(
            [],
            gs.utilGetMaxColumnWidths([])
        )

    def test(self):
        self.assertEqual(
            [ 2, 3, 10],
            gs.utilGetMaxColumnWidths(
                [
                    ['12', '1'  , '123456789'],
                    ['1' , '123', '1234'],
                    ['1' , '1'  , '1234567890'],
                ]
            )
        )

#-----------------------------------------------------------------------------
class Test_utilGetWorkDirFileAsTwoColumns(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def test(self):
        TEST_FILE = 'test'
        createNonEmptyGitRepository()
        createAndCommitFile(TEST_FILE)
        modifiedFile = open(TEST_FILE, 'w')
        modifiedFile.write('a')
        modifiedFile.close()

        fileStatuses = gs.gitGetFileStatuses()
        modifiedFileStatus = fileStatuses[gs.KEY_FILE_STATUSES_WORK_DIR][0]
        self.assertEqual(
            [
                modifiedFileStatus[gs.KEY_FILE_STATUSES_TYPE],
                modifiedFileStatus[gs.KEY_FILE_STATUSES_FILENAME],
            ],
            gs.utilGetWorkDirFileAsTwoColumns(modifiedFileStatus)
        )

#-----------------------------------------------------------------------------
class Test_utilGetRawBranchesLines(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #   - utilGetRawBranchesLines() just calls other functions that are fully
    #     tested
    #   - so just minimal tests of the showAllBranches argument
    #-------------------------------------------------------------------------

    def testAllBranches(self):
        createNonEmptyGitRepository()
        execute(['git', 'checkout', '-b', 'dev'])

        # Expected: header, master, dev
        self.assertEqual(3,
            len(gs.utilGetRawBranchesLines(
                gs.CONFIG_DEFAULT,
                gs.gitGetCurrentBranch(),
                gs.gitGetLocalBranches(),
                True
            ))
        )

    def testAllBranchesDetachedHeadState(self):
        createNonEmptyGitRepository()
        execute(['git', 'checkout', '-b', 'dev'])

        createAndCommitFile('newFile1')
        previousCommitHash = subprocess.check_output(
            ['git', 'rev-list', '--max-count=1', 'dev'],
            universal_newlines = True
        ).splitlines()[0]

        createAndCommitFile('newFile2')
        execute(['git', 'checkout', previousCommitHash])

        # Expected: header, master, dev, Detached Head
        self.assertEqual(4,
            len(gs.utilGetRawBranchesLines(
                gs.CONFIG_DEFAULT,
                gs.gitGetCurrentBranch(),
                gs.gitGetLocalBranches(),
                True
            ))
        )

    def testCurrentBranchOnly(self):
        createNonEmptyGitRepository()
        execute(['git', 'checkout', '-b', 'dev'])

        # Expected: header, dev
        self.assertEqual(2,
            len(gs.utilGetRawBranchesLines(
                gs.CONFIG_DEFAULT,
                gs.gitGetCurrentBranch(),
                gs.gitGetLocalBranches(),
                False
            ))
        )

    def testCurrentBranchOnlyDetachedHeadState(self):
        createNonEmptyGitRepository()
        execute(['git', 'checkout', '-b', 'dev'])

        createAndCommitFile('newFile1')
        previousCommitHash = subprocess.check_output(
            ['git', 'rev-list', '--max-count=1', 'dev'],
            universal_newlines = True
        ).splitlines()[0]

        createAndCommitFile('newFile2')
        execute(['git', 'checkout', previousCommitHash])

        # Expected: header, Detached Head
        self.assertEqual(2,
            len(gs.utilGetRawBranchesLines(
                gs.CONFIG_DEFAULT,
                gs.gitGetCurrentBranch(),
                gs.gitGetLocalBranches(),
                False
            ))
        )

#-----------------------------------------------------------------------------
class Test_utilGetRawWorkDirLines(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #   - utilGetRawWorkDirLines() just calls other functions that are fully
    #     tested
    #   - so just a minimal test that it works properly with >1 modified files
    #-------------------------------------------------------------------------

    def test(self):
        TEST_FILE_1 = 'testfile_1'
        TEST_FILE_2 = 'testfile_2'
        createNonEmptyGitRepository()

        for testFile in [TEST_FILE_1, TEST_FILE_2]:
            createAndCommitFile(testFile)
            modifiedFile = open(testFile, 'w')
            modifiedFile.write('a')
            modifiedFile.close()

        self.assertEqual(2,
            len(gs.utilGetRawWorkDirLines(gs.gitGetFileStatuses()))
        )

#-----------------------------------------------------------------------------
class Test_utilGetRawStageLines(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #   - utilGetRawStageLines() just calls other functions that are fully
    #     tested
    #   - so just a minimal test that it works properly with >1 staged files
    #-------------------------------------------------------------------------

    def test(self):
        TEST_FILE_1 = 'testfile_1'
        TEST_FILE_2 = 'testfile_2'
        createNonEmptyGitRepository()

        for testFile in [TEST_FILE_1, TEST_FILE_2]:
            modifiedFile = open(testFile, 'w')
            modifiedFile.write('a')
            modifiedFile.close()
            execute(['git', 'add', testFile])

        self.assertEqual(2,
            len(gs.utilGetRawStageLines(gs.gitGetFileStatuses()))
        )

#-----------------------------------------------------------------------------
class Test_utilGetRawStashLines(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #   - utilGetRawStashLines() just calls other functions that are fully
    #     tested
    #   - so just a minimal test that it works properly with >1 stashes
    #-------------------------------------------------------------------------

    def test(self):
        TEST_FILE_1 = 'testfile_1'
        TEST_FILE_2 = 'testfile_2'
        createNonEmptyGitRepository()

        for testFile in [TEST_FILE_1, TEST_FILE_2]:
            createAndCommitFile(testFile)

        for testFile in [TEST_FILE_1, TEST_FILE_2]:
            modifiedFile = open(testFile, 'w')
            modifiedFile.write('a')
            modifiedFile.close()
            execute(['git', 'stash'])

        self.assertEqual(2,
            len(gs.utilGetRawStashLines())
        )

#-----------------------------------------------------------------------------
class Test_utilGetRawUntrackedLines(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #   - utilGetRawUntrackedLines() just calls other functions that are fully
    #     tested
    #   - so just a minimal test that it works properly with >1 untracked files
    #-------------------------------------------------------------------------

    def test(self):
        TEST_FILE_1 = 'testfile_1'
        TEST_FILE_2 = 'testfile_2'
        createNonEmptyGitRepository()

        for testFile in [TEST_FILE_1, TEST_FILE_2]:
            modifiedFile = open(testFile, 'w')
            modifiedFile.write('a')
            modifiedFile.close()

        self.assertEqual(2,
            len(gs.utilGetRawUntrackedLines(gs.gitGetFileStatuses()))
        )

#-----------------------------------------------------------------------------
class Test_utilGetStagedFileAsTwoColumns(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def testNoHeuristic(self):
        TEST_FILE = 'test'
        createNonEmptyGitRepository()
        newFile = open(TEST_FILE, 'w')
        newFile.write('a')
        newFile.close()
        execute(['git', 'add', TEST_FILE])

        fileStatuses = gs.gitGetFileStatuses()
        stagedFileStatus = fileStatuses[gs.KEY_FILE_STATUSES_STAGE][0]
        self.assertEqual(
            [
                stagedFileStatus[gs.KEY_FILE_STATUSES_TYPE],
                stagedFileStatus[gs.KEY_FILE_STATUSES_FILENAME],
            ],
            gs.utilGetStagedFileAsTwoColumns(stagedFileStatus)
        )

    def testWithHeuristic(self):
        TEST_FILE = 'test'
        NEW_FILE = 'test-new'

        createNonEmptyGitRepository()
        createAndCommitFile(TEST_FILE)
        execute(['git', 'mv', TEST_FILE, NEW_FILE])

        fileStatuses = gs.gitGetFileStatuses()
        stagedFileStatus = fileStatuses[gs.KEY_FILE_STATUSES_STAGE][0]
        self.assertEqual(
            [
                stagedFileStatus[gs.KEY_FILE_STATUSES_TYPE] + '(100)',
                stagedFileStatus[gs.KEY_FILE_STATUSES_FILENAME] + ' -> ' + NEW_FILE,
            ],
            gs.utilGetStagedFileAsTwoColumns(stagedFileStatus)
        )

#-----------------------------------------------------------------------------
class Test_utilGetStashAsTwoColumns(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def test(self):
        TEST_FILE = 'test'
        createNonEmptyGitRepository()
        newFile = open(TEST_FILE, 'w')
        newFile.write('a')
        newFile.close()
        execute(['git', 'add', TEST_FILE])
        execute(['git', 'stash'])

        stashStatus = gs.gitGetStashes()[0]
        self.assertEqual(
            [
                stashStatus[gs.KEY_STASH_NAME],
                stashStatus[gs.KEY_STASH_DESCRIPTION],
            ],
            gs.utilGetStashAsTwoColumns(stashStatus)
        )

#-----------------------------------------------------------------------------
class Test_utilGetStyledText(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def testNoStyles(self):
        self.assertEqual('test', gs.utilGetStyledText([], 'test'))

    def testOneStyle(self):
        self.assertEqual(
            '\033[1mtest\033[0m',
            gs.utilGetStyledText([gs.TEXT_BOLD], 'test')
        )

    def testMultipleStyles(self):
        self.assertEqual(
            '\033[1;5mtest\033[0m',
            gs.utilGetStyledText([gs.TEXT_BOLD, gs.TEXT_FLASHING], 'test')
        )

#-----------------------------------------------------------------------------
class Test_utilGetTargetBranch(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Test - Defaults
    #-------------------------------------------------------------------------
    def testDefaultTargets(self):
        BRANCH_LIST = [
            'master',
            'develop',
            'hotfix-broken',
            'release-1.0.0',
            'make-awesome',
        ]

        self.assertEqual(
            '',
            gs.utilGetTargetBranch(gs.CONFIG_DEFAULT, 'master', BRANCH_LIST)
        )

        self.assertEqual(
            'master',
            gs.utilGetTargetBranch(gs.CONFIG_DEFAULT, 'develop', BRANCH_LIST)
        )

        self.assertEqual(
            'master',
            gs.utilGetTargetBranch(gs.CONFIG_DEFAULT, 'hotfix-broken', BRANCH_LIST)
        )

        self.assertEqual(
            'master',
            gs.utilGetTargetBranch(gs.CONFIG_DEFAULT, 'release-1.0.0', BRANCH_LIST)
        )

        self.assertEqual(
            'develop',
            gs.utilGetTargetBranch(gs.CONFIG_DEFAULT, 'make-awesome', BRANCH_LIST)
        )

    #-------------------------------------------------------------------------
    # Tests - Matching Different Targets without regular expressions
    #-------------------------------------------------------------------------
    FIRST_BRANCH = 'firstBranch'
    FIRST_TARGET = 'firstTarget'

    SECOND_BRANCH = 'secondBranch'
    SECOND_TARGET = 'secondTarget'

    DEFAULT_TARGET = 'defaultTarget'

    CONFIG = {
        gs.KEY_CONFIG_DEFAULT_TARGET: DEFAULT_TARGET,
        gs.KEY_CONFIG_BRANCHES: [
            {
                gs.KEY_CONFIG_BRANCH_NAME: FIRST_BRANCH,
                gs.KEY_CONFIG_BRANCH_TARGET: FIRST_TARGET,
            },
            {
                gs.KEY_CONFIG_BRANCH_NAME: SECOND_BRANCH,
                gs.KEY_CONFIG_BRANCH_TARGET: SECOND_TARGET,
            },
        ]
    }

    def testFirstBranchMatchesAndTargetExists(self):
        BRANCH = self.FIRST_BRANCH
        EXPECTED_TARGET = self.FIRST_TARGET
        BRANCH_LIST = [
            self.FIRST_BRANCH,
            self.FIRST_TARGET,
            self.SECOND_BRANCH,
            self.SECOND_TARGET,
        ]

        self.assertEqual(
            EXPECTED_TARGET,
            gs.utilGetTargetBranch(
                self.CONFIG,
                BRANCH,
                BRANCH_LIST,
            )
        )

    def testFirstBranchMatchesAndTargetDoesNotExit(self):
        BRANCH = self.FIRST_BRANCH
        EXPECTED_TARGET = ''
        BRANCH_LIST = [
            self.FIRST_BRANCH,
            self.SECOND_BRANCH,
            self.SECOND_TARGET,
        ]

        self.assertEqual(
            EXPECTED_TARGET,
            gs.utilGetTargetBranch(
                self.CONFIG,
                BRANCH,
                BRANCH_LIST,
            )
        )

    def testNotFirstBranchMatchesAndTargetExists(self):
        BRANCH = self.SECOND_BRANCH
        EXPECTED_TARGET = self.SECOND_TARGET
        BRANCH_LIST = [
            self.FIRST_BRANCH,
            self.FIRST_TARGET,
            self.SECOND_BRANCH,
            self.SECOND_TARGET,
        ]

        self.assertEqual(
            EXPECTED_TARGET,
            gs.utilGetTargetBranch(
                self.CONFIG,
                BRANCH,
                BRANCH_LIST,
            )
        )

    def testNotFirstBranchMatchesAndTargetDoesNotExist(self):
        BRANCH = self.SECOND_BRANCH
        EXPECTED_TARGET = ''
        BRANCH_LIST = [
            self.FIRST_BRANCH,
            self.FIRST_TARGET,
            self.SECOND_BRANCH,
        ]

        self.assertEqual(
            EXPECTED_TARGET,
            gs.utilGetTargetBranch(
                self.CONFIG,
                BRANCH,
                BRANCH_LIST,
            )
        )

    def testDefaultTargetAndTargetExists(self):
        BRANCH = 'something-else'
        EXPECTED_TARGET = self.DEFAULT_TARGET
        BRANCH_LIST = [
            'something-else',
            self.FIRST_BRANCH,
            self.FIRST_TARGET,
            self.SECOND_BRANCH,
            self.SECOND_TARGET,
            self.DEFAULT_TARGET,
        ]

        self.assertEqual(
            EXPECTED_TARGET,
            gs.utilGetTargetBranch(
                self.CONFIG,
                BRANCH,
                BRANCH_LIST,
            )
        )

    def testDefaultTargetAndTargetDoesNotExist(self):
        BRANCH = 'something-else'
        EXPECTED_TARGET = ''
        BRANCH_LIST = [
            'something-else',
            self.FIRST_BRANCH,
            self.FIRST_TARGET,
            self.SECOND_BRANCH,
            self.SECOND_TARGET,
        ]

        self.assertEqual(
            EXPECTED_TARGET,
            gs.utilGetTargetBranch(
                self.CONFIG,
                BRANCH,
                BRANCH_LIST,
            )
        )

    #-------------------------------------------------------------------------
    # Tests - Matching Different Targets with regular expressions
    #-------------------------------------------------------------------------
    def testMatchUsingRegularExpression(self):
        CONFIG = {
            gs.KEY_CONFIG_DEFAULT_TARGET: 'develop',
            gs.KEY_CONFIG_BRANCHES: [
                {
                    gs.KEY_CONFIG_BRANCH_NAME:'^xx-start',
                    gs.KEY_CONFIG_BRANCH_TARGET: 'first',
                },
                {
                    gs.KEY_CONFIG_BRANCH_NAME:'end-xx$',
                    gs.KEY_CONFIG_BRANCH_TARGET: 'second',
                },
                {
                    gs.KEY_CONFIG_BRANCH_NAME:'middle-xx-more',
                    gs.KEY_CONFIG_BRANCH_TARGET: 'third',
                },
            ],
        }

        BRANCH_LIST = [
            'develop',
            'first',
            'second',
            'third',
            'xx-start-bla',
            'bla-end-xx',
            'bla-middle-xx-more-bla',
        ]

        self.assertEqual(
            'first',
            gs.utilGetTargetBranch(
                CONFIG,
                'xx-start-bla',
                BRANCH_LIST,
            )
        )

        self.assertEqual(
            'second',
            gs.utilGetTargetBranch(
                CONFIG,
                'bla-end-xx',
                BRANCH_LIST,
            )
        )

        self.assertEqual(
            'third',
            gs.utilGetTargetBranch(
                CONFIG,
                'bla-middle-xx-more-bla',
                BRANCH_LIST,
            )
        )

#-----------------------------------------------------------------------------
class Test_utilValidateGitsummaryConfig(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def testOkOneBranch(self):
        TEST_CONFIG = {
            gs.KEY_CONFIG_BRANCH_ORDER: ['^master$'],
            gs.KEY_CONFIG_DEFAULT_TARGET: 'master',
            gs.KEY_CONFIG_BRANCHES: [
                {
                    gs.KEY_CONFIG_BRANCH_NAME: '^develop$',
                    gs.KEY_CONFIG_BRANCH_TARGET: 'master',
                },
            ],
        }
        testResult = gs.utilValidateGitsummaryConfig(TEST_CONFIG)

        self.assertTrue(testResult[gs.KEY_RETURN_STATUS])
        self.assertEqual(0, len(testResult[gs.KEY_RETURN_MESSAGES]))

    def testOkMultipleBranches(self):
        TEST_CONFIG = {
            gs.KEY_CONFIG_BRANCH_ORDER: ['^master$'],
            gs.KEY_CONFIG_DEFAULT_TARGET: 'master',
            gs.KEY_CONFIG_BRANCHES: [
                {
                    gs.KEY_CONFIG_BRANCH_NAME: '^master$',
                    gs.KEY_CONFIG_BRANCH_TARGET: '',
                },
                {
                    gs.KEY_CONFIG_BRANCH_NAME: '^develop$',
                    gs.KEY_CONFIG_BRANCH_TARGET: 'master',
                },
            ],
        }
        testResult = gs.utilValidateGitsummaryConfig(TEST_CONFIG)

        self.assertTrue(testResult[gs.KEY_RETURN_STATUS])
        self.assertEqual(0, len(testResult[gs.KEY_RETURN_MESSAGES]))

    def testEmpty(self):
        TEST_CONFIG = {}
        testResult = gs.utilValidateGitsummaryConfig(TEST_CONFIG)

        self.assertFalse(testResult[gs.KEY_RETURN_STATUS])
        self.assertEqual(3, len(testResult[gs.KEY_RETURN_MESSAGES]))

    def testUnknownKey(self):
        TEST_CONFIG = {
            gs.KEY_CONFIG_BRANCH_ORDER: ['^master$'],
            gs.KEY_CONFIG_DEFAULT_TARGET: 'master',
            gs.KEY_CONFIG_BRANCHES: [],
            'unknown': 'bobs yer uncle',
        }
        testResult = gs.utilValidateGitsummaryConfig(TEST_CONFIG)

        self.assertFalse(testResult[gs.KEY_RETURN_STATUS])
        self.assertEqual(1, len(testResult[gs.KEY_RETURN_MESSAGES]))

    def testBranchOrderMissing(self):
        TEST_CONFIG = {
            gs.KEY_CONFIG_DEFAULT_TARGET: 'master',
            gs.KEY_CONFIG_BRANCHES: [],
        }
        testResult = gs.utilValidateGitsummaryConfig(TEST_CONFIG)

        self.assertFalse(testResult[gs.KEY_RETURN_STATUS])
        self.assertEqual(1, len(testResult[gs.KEY_RETURN_MESSAGES]))

    def testBranchOrderNotArray(self):
        TEST_CONFIG = {
            gs.KEY_CONFIG_BRANCH_ORDER: 'bobs yer uncle',
            gs.KEY_CONFIG_DEFAULT_TARGET: 'master',
            gs.KEY_CONFIG_BRANCHES: [],
        }
        testResult = gs.utilValidateGitsummaryConfig(TEST_CONFIG)

        self.assertFalse(testResult[gs.KEY_RETURN_STATUS])
        self.assertEqual(1, len(testResult[gs.KEY_RETURN_MESSAGES]))

    def testBranchOrderNotArrayOfStrings(self):
        TEST_CONFIG = {
            gs.KEY_CONFIG_BRANCH_ORDER: [ [] ],
            gs.KEY_CONFIG_DEFAULT_TARGET: 'master',
            gs.KEY_CONFIG_BRANCHES: [],
        }
        testResult = gs.utilValidateGitsummaryConfig(TEST_CONFIG)

        self.assertFalse(testResult[gs.KEY_RETURN_STATUS])
        self.assertEqual(1, len(testResult[gs.KEY_RETURN_MESSAGES]))

    def testBranchOrderNotArrayOfValidRegularExpressions(self):
        TEST_CONFIG = {
            gs.KEY_CONFIG_BRANCH_ORDER: ['$['],
            gs.KEY_CONFIG_DEFAULT_TARGET: 'master',
            gs.KEY_CONFIG_BRANCHES: [],
        }
        testResult = gs.utilValidateGitsummaryConfig(TEST_CONFIG)

        self.assertFalse(testResult[gs.KEY_RETURN_STATUS])
        self.assertEqual(1, len(testResult[gs.KEY_RETURN_MESSAGES]))

    def testDefaultTargetMissing(self):
        TEST_CONFIG = {
            gs.KEY_CONFIG_BRANCH_ORDER: ['^master$'],
            gs.KEY_CONFIG_BRANCHES: [],
        }
        testResult = gs.utilValidateGitsummaryConfig(TEST_CONFIG)

        self.assertFalse(testResult[gs.KEY_RETURN_STATUS])
        self.assertEqual(1, len(testResult[gs.KEY_RETURN_MESSAGES]))

    def testDefaultTargetNotString(self):
        TEST_CONFIG = {
            gs.KEY_CONFIG_BRANCH_ORDER: ['^master$'],
            gs.KEY_CONFIG_DEFAULT_TARGET: [],
            gs.KEY_CONFIG_BRANCHES: [],
        }
        testResult = gs.utilValidateGitsummaryConfig(TEST_CONFIG)

        self.assertFalse(testResult[gs.KEY_RETURN_STATUS])
        self.assertEqual(1, len(testResult[gs.KEY_RETURN_MESSAGES]))

    def testBranchesMissing(self):
        TEST_CONFIG = {
            gs.KEY_CONFIG_BRANCH_ORDER: ['^master$'],
            gs.KEY_CONFIG_DEFAULT_TARGET: 'master',
        }
        testResult = gs.utilValidateGitsummaryConfig(TEST_CONFIG)

        self.assertFalse(testResult[gs.KEY_RETURN_STATUS])
        self.assertEqual(1, len(testResult[gs.KEY_RETURN_MESSAGES]))

    def testBranchesNotArray(self):
        TEST_CONFIG = {
            gs.KEY_CONFIG_BRANCH_ORDER: ['^master$'],
            gs.KEY_CONFIG_DEFAULT_TARGET: 'master',
            gs.KEY_CONFIG_BRANCHES: 'bobs yer uncle',
        }
        testResult = gs.utilValidateGitsummaryConfig(TEST_CONFIG)

        self.assertFalse(testResult[gs.KEY_RETURN_STATUS])
        self.assertEqual(1, len(testResult[gs.KEY_RETURN_MESSAGES]))

    def testBranchNameMissing(self):
        TEST_CONFIG = {
            gs.KEY_CONFIG_BRANCH_ORDER: ['^master$'],
            gs.KEY_CONFIG_DEFAULT_TARGET: 'master',
            gs.KEY_CONFIG_BRANCHES: [
                {
                    gs.KEY_CONFIG_BRANCH_TARGET: 'bobs yer uncle',
                },
            ],
        }
        testResult = gs.utilValidateGitsummaryConfig(TEST_CONFIG)

        self.assertFalse(testResult[gs.KEY_RETURN_STATUS])
        self.assertEqual(1, len(testResult[gs.KEY_RETURN_MESSAGES]))

    def testBranchNameNotString(self):
        TEST_CONFIG = {
            gs.KEY_CONFIG_BRANCH_ORDER: ['^master$'],
            gs.KEY_CONFIG_DEFAULT_TARGET: 'master',
            gs.KEY_CONFIG_BRANCHES: [
                {
                    gs.KEY_CONFIG_BRANCH_NAME: [],
                    gs.KEY_CONFIG_BRANCH_TARGET: 'bobs yer uncle',
                },
            ],
        }
        testResult = gs.utilValidateGitsummaryConfig(TEST_CONFIG)

        self.assertFalse(testResult[gs.KEY_RETURN_STATUS])
        self.assertEqual(1, len(testResult[gs.KEY_RETURN_MESSAGES]))

    def testBranchNameNotValidRegexp(self):
        TEST_CONFIG = {
            gs.KEY_CONFIG_BRANCH_ORDER: ['^master$'],
            gs.KEY_CONFIG_DEFAULT_TARGET: 'master',
            gs.KEY_CONFIG_BRANCHES: [
                {
                    gs.KEY_CONFIG_BRANCH_NAME: '$[',
                    gs.KEY_CONFIG_BRANCH_TARGET: 'bobs yer uncle',
                },
            ],
        }
        testResult = gs.utilValidateGitsummaryConfig(TEST_CONFIG)

        self.assertFalse(testResult[gs.KEY_RETURN_STATUS])
        self.assertEqual(1, len(testResult[gs.KEY_RETURN_MESSAGES]))

    def testBranchTargetMissing(self):
        TEST_CONFIG = {
            gs.KEY_CONFIG_BRANCH_ORDER: ['^master$'],
            gs.KEY_CONFIG_DEFAULT_TARGET: 'master',
            gs.KEY_CONFIG_BRANCHES: [
                {
                    gs.KEY_CONFIG_BRANCH_NAME: 'bobs yer uncle',
                },
            ],
        }
        testResult = gs.utilValidateGitsummaryConfig(TEST_CONFIG)

        self.assertFalse(testResult[gs.KEY_RETURN_STATUS])
        self.assertEqual(1, len(testResult[gs.KEY_RETURN_MESSAGES]))

    def testBranchTargetNotString(self):
        TEST_CONFIG = {
            gs.KEY_CONFIG_BRANCH_ORDER: ['^master$'],
            gs.KEY_CONFIG_DEFAULT_TARGET: 'master',
            gs.KEY_CONFIG_BRANCHES: [
                {
                    gs.KEY_CONFIG_BRANCH_NAME: 'bobs yer uncle',
                    gs.KEY_CONFIG_BRANCH_TARGET: [],
                },
            ],
        }
        testResult = gs.utilValidateGitsummaryConfig(TEST_CONFIG)

        self.assertFalse(testResult[gs.KEY_RETURN_STATUS])
        self.assertEqual(1, len(testResult[gs.KEY_RETURN_MESSAGES]))

    def testBranchUnknownKey(self):
        TEST_CONFIG = {
            gs.KEY_CONFIG_BRANCH_ORDER: ['^master$'],
            gs.KEY_CONFIG_DEFAULT_TARGET: 'master',
            gs.KEY_CONFIG_BRANCHES: [
                {
                    gs.KEY_CONFIG_BRANCH_NAME: 'a-name',
                    gs.KEY_CONFIG_BRANCH_TARGET: 'a-target',
                    'unknown': 'something',
                },
            ],
        }
        testResult = gs.utilValidateGitsummaryConfig(TEST_CONFIG)

        self.assertFalse(testResult[gs.KEY_RETURN_STATUS])
        self.assertEqual(1, len(testResult[gs.KEY_RETURN_MESSAGES]))

#-----------------------------------------------------------------------------
class Test_utilValidateKeyPresenceAndType(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def testOk(self):
        TEST_KEY = 'testKey'
        TEST_VALUE = '123'

        TEST_OBJECT = {
            TEST_KEY: TEST_VALUE,
        }

        self.assertEqual(
            0,
            len(gs.utilValidateKeyPresenceAndType(
                TEST_OBJECT,
                TEST_KEY,
                TEST_VALUE,
                'msg',
                'string'
            ))
        )

    def testMissingKey(self):
        TEST_KEY = 'testKey'
        TEST_VALUE = '123'

        TEST_OBJECT = {
            TEST_KEY: TEST_VALUE,
        }

        self.assertEqual(
            1,
            len(gs.utilValidateKeyPresenceAndType(
                TEST_OBJECT,
                'key-not-in-object',
                TEST_VALUE,
                'msg',
                'string'
            ))
        )

    def testKeyIncorrectType(self):
        TEST_KEY = 'testKey'
        TEST_VALUE = '123'

        TEST_OBJECT = {
            TEST_KEY: TEST_VALUE,
        }

        self.assertEqual(
            1,
            len(gs.utilValidateKeyPresenceAndType(
                TEST_OBJECT,
                TEST_KEY,
                [],
                'msg',
                'array'
            ))
        )

if __name__ == '__main__':
    # Since we have a pile of tests hitting the filesystem, change to a
    # temporary directory up front, just in case we forget to for an individual
    # test (and end up messing up stuff in our dev folder)
    initialDir = os.getcwd()
    tempDir = tempfile.mkdtemp(prefix='testGitsummary.')
    os.chdir(tempDir)

    # Now it's safe to test!
    # We need 'exit=false' so our cleanup after unittest.main() will run.
    unittest.main(exit=False)

    # Cleanup
    os.chdir(initialDir)
    shutil.rmtree(tempDir)
