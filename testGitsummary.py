#!/usr/bin/env python3
import gitsummary as gs

import os
import re
import subprocess
import tempfile
import unittest

#-----------------------------------------------------------------------------
# setUp() and tearDown() common to all tests
#   - Create/delete a temporary folder where we can do git stuff
#   - cd into it on creation
#-----------------------------------------------------------------------------
def commonTestSetUp(self):
    self.setupInitialDir = os.getcwd()
    self.tempDir = tempfile.TemporaryDirectory()
    os.chdir(self.tempDir.name)

def commonTestTearDown(self):
    os.chdir(self.setupInitialDir)
    self.tempDir.cleanup()

#-----------------------------------------------------------------------------
# Helpers
#-----------------------------------------------------------------------------
def createAndCommitFile(filename, commitMsg = 'Commit Message'):
    """
    Create the specified file (empty) in the current working directory then
    'git add' and 'git commit'.
    """
    newFile = open(filename, 'w')
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
class Test_gitGetCommitDetails(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def test(self):
        COMMIT_MSG = 'This is the message'

        createNonEmptyGitRepository()
        createAndCommitFile('newFile', COMMIT_MSG)

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
    def test_initialRepositoryState(self):
        EXPECTED_BRANCH = 'master'
        execute(['git', 'init'])

        self.assertEqual(EXPECTED_BRANCH, gs.gitGetCurrentBranch())

    def test_initialRepositoryStateFromClonedRemote(self):
        LOCAL = 'local'
        createEmptyRemoteLocalPair('remote', LOCAL)
        os.chdir(LOCAL)

        self.assertEqual('master', gs.gitGetCurrentBranch())

    def test_initialRepositoryStateNotMaster(self):
        EXPECTED_BRANCH = 'dev'
        execute(['git', 'init'])
        execute(['git', 'checkout', '-b', EXPECTED_BRANCH])

        self.assertEqual(EXPECTED_BRANCH, gs.gitGetCurrentBranch())

    def test_oneBranchExists(self):
        EXPECTED_BRANCH = 'master'

        createNonEmptyGitRepository()
        self.assertEqual(EXPECTED_BRANCH, gs.gitGetCurrentBranch())

    def test_multipleBranchesExist(self):
        EXPECTED_BRANCH = 'dev'

        createNonEmptyGitRepository()
        execute(['git', 'checkout', '-b', EXPECTED_BRANCH])

        self.assertEqual(EXPECTED_BRANCH, gs.gitGetCurrentBranch())

    def test_detachedHeadState(self):
        EXPECTED_BRANCH = ''

        createNonEmptyGitRepository()
        createAndCommitFile('newFile1')
        firstHash = subprocess.check_output(
            ['git', 'rev-list', '--max-count=1', 'master'],
            universal_newlines = True
        ).splitlines()[0]

        createAndCommitFile('newFile2')
        execute(['git', 'checkout', firstHash])

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
            gs.KEY_FILE_STATUSES_STAGED: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'A',
                    gs.KEY_FILE_STATUSES_FILENAME: testFile
                },
            ],
            gs.KEY_FILE_STATUSES_MODIFIED: [],
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
            gs.KEY_FILE_STATUSES_STAGED: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'D',
                    gs.KEY_FILE_STATUSES_FILENAME: testFile,
                },
            ],
            gs.KEY_FILE_STATUSES_MODIFIED: [],
            gs.KEY_FILE_STATUSES_UNTRACKED: [],
            gs.KEY_FILE_STATUSES_UNKNOWN: [],
        }

        createNonEmptyGitRepository()
        createAndCommitFile(testFile)
        execute(['git', 'rm', testFile])

        self.assertEqual(EXPECTED_RESULT, gs.gitGetFileStatuses())

    def util_testStageModifiedFile(self, testFile):
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGED: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'M',
                    gs.KEY_FILE_STATUSES_FILENAME: testFile,
                },
            ],
            gs.KEY_FILE_STATUSES_MODIFIED: [],
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
            gs.KEY_FILE_STATUSES_STAGED: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'R',
                    gs.KEY_FILE_STATUSES_FILENAME: testFile,
                    gs.KEY_FILE_STATUSES_NEW_FILENAME: TEST_FILE_RENAMED,
                    gs.KEY_FILE_STATUSES_HEURISTIC_SCORE: '100',
                },
            ],
            gs.KEY_FILE_STATUSES_MODIFIED: [],
            gs.KEY_FILE_STATUSES_UNTRACKED: [],
            gs.KEY_FILE_STATUSES_UNKNOWN: [],
        }

        createNonEmptyGitRepository()
        createAndCommitFile(testFile)
        execute(['git', 'mv', testFile, TEST_FILE_RENAMED])

        self.assertEqual(EXPECTED_RESULT, gs.gitGetFileStatuses())

    def util_testWorkDirDeletedFile(self, testFile):
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGED: [],
            gs.KEY_FILE_STATUSES_MODIFIED: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'D',
                    gs.KEY_FILE_STATUSES_FILENAME: testFile,
                },
            ],
            gs.KEY_FILE_STATUSES_UNTRACKED: [],
            gs.KEY_FILE_STATUSES_UNKNOWN: [],
        }

        createNonEmptyGitRepository()
        createAndCommitFile(testFile)
        os.remove(testFile)

        self.assertEqual(EXPECTED_RESULT, gs.gitGetFileStatuses())

    def util_testWorkDirModifiedFile(self, testFile):
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGED: [],
            gs.KEY_FILE_STATUSES_MODIFIED: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'M',
                    gs.KEY_FILE_STATUSES_FILENAME: testFile,
                },
            ],
            gs.KEY_FILE_STATUSES_UNTRACKED: [],
            gs.KEY_FILE_STATUSES_UNKNOWN: [],
        }

        createNonEmptyGitRepository()
        createAndCommitFile(testFile)

        modifiedFile = open(testFile, 'w')
        modifiedFile.write('a')
        modifiedFile.close()

        self.assertEqual(EXPECTED_RESULT, gs.gitGetFileStatuses())

    def util_testUnmergedFile(self, testFile):
        # Unmerged files are created by merge conflicts, and git always
        # says both the stage and workdir are unmerged
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGED: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'U',
                    gs.KEY_FILE_STATUSES_FILENAME: testFile,
                },
            ],
            gs.KEY_FILE_STATUSES_MODIFIED: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'U',
                    gs.KEY_FILE_STATUSES_FILENAME: testFile,
                },
            ],
            gs.KEY_FILE_STATUSES_UNTRACKED: [],
            gs.KEY_FILE_STATUSES_UNKNOWN: [],
        }

        # LOCAL1 and LOCAL2 will both modify the same file, thus resulting
        # in a merge conflict
        LOCAL1 = 'local1'
        LOCAL2 = 'local2'
        REMOTE = 'remote'

        createEmptyRemoteLocalPair(REMOTE, LOCAL1)
        execute(['git', 'clone', REMOTE, LOCAL2])

        # LOCAL1 and LOCAL2 need to operate on the same git history, thus
        # need to create a common empty file for them to work on first
        os.chdir(LOCAL1)
        createAndCommitFile(testFile, 'Created in local1')
        execute(['git', 'push'])

        os.chdir('..')
        os.chdir(LOCAL2)
        execute(['git', 'pull'])

        # Make the changes in LOCAL1, which will conflict with changes to be
        # done in LOCAL2
        os.chdir('..')
        os.chdir(LOCAL1)
        testFileHandle = open(testFile, 'w')
        testFileHandle.write('Changes from local1')
        testFileHandle.close()
        execute(['git', 'add', testFile])
        execute(['git', 'commit', '-m', 'commit from local1'])
        execute(['git', 'push'])

        # Make the conflicting changes in LOCAL2
        os.chdir('..')
        os.chdir(LOCAL2)
        testFileHandle = open(testFile, 'w')
        testFileHandle.write('The front fell off')
        testFileHandle.close()
        execute(['git', 'add', testFile])
        execute(['git', 'commit', '-m', 'commit from local2'])

        # Force the merge conflict
        # Can't use execute() helper since 'git pull' will return a non-zero
        # exit status
        subprocess.run(
            ['git', 'pull'],
            stdout = subprocess.DEVNULL,
            stderr = subprocess.DEVNULL,
            check=False
        )

        self.assertEqual(EXPECTED_RESULT, gs.gitGetFileStatuses())

    def util_testUntrackedFile(self, testFile):
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGED: [],
            gs.KEY_FILE_STATUSES_MODIFIED: [],
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
        self.assertEqual([], statuses[gs.KEY_FILE_STATUSES_STAGED])
        self.assertEqual([], statuses[gs.KEY_FILE_STATUSES_MODIFIED])
        self.assertEqual([], statuses[gs.KEY_FILE_STATUSES_UNTRACKED])
        self.assertEqual([], statuses[gs.KEY_FILE_STATUSES_UNKNOWN])

    def test_initialRepositoryStateStageAddedFile(self):
        TEST_FILE = 'testfile'
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGED: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'A',
                    gs.KEY_FILE_STATUSES_FILENAME: TEST_FILE,
                },
            ],
            gs.KEY_FILE_STATUSES_MODIFIED: [],
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
            gs.KEY_FILE_STATUSES_STAGED: [],
            gs.KEY_FILE_STATUSES_MODIFIED: [],
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
        self.assertEqual([], statuses[gs.KEY_FILE_STATUSES_STAGED])
        self.assertEqual([], statuses[gs.KEY_FILE_STATUSES_MODIFIED])
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
        self.util_testUnmergedFile('testfile')

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
        self.util_testUnmergedFile('testfile with spaces')

    def test_untrackedFileWithSpaces(self):
        self.util_testUntrackedFile('testfile with spaces')

    def test_multipleStatusesOnOneFile(self):
        # This is a test where one file has changes in both the working
        # directory and the stage. We accomplish by doing the following:
        #   - commit a new file
        #   - make a change and stage it
        #   - make another change in the working directory

        TEST_FILE = 'testfile'
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGED: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'M',
                    gs.KEY_FILE_STATUSES_FILENAME: TEST_FILE,
                },
            ],
            gs.KEY_FILE_STATUSES_MODIFIED: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'M',
                    gs.KEY_FILE_STATUSES_FILENAME: TEST_FILE,
                },
            ],
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
            gs.KEY_FILE_STATUSES_STAGED: [
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
            gs.KEY_FILE_STATUSES_MODIFIED: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'M',
                    gs.KEY_FILE_STATUSES_FILENAME: TEST_FILE3,
                },
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'D',
                    gs.KEY_FILE_STATUSES_FILENAME: TEST_FILE4,
                },
            ],
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
    def test_initialRepositoryState(self):
        EXPECTED_BRANCHES = ['master']

        execute(['git', 'init'])
        self.assertEqual(EXPECTED_BRANCHES, gs.gitGetLocalBranches())

    def test_oneBranch(self):
        EXPECTED_BRANCHES = ['master']

        createNonEmptyGitRepository()
        self.assertEqual(EXPECTED_BRANCHES, gs.gitGetLocalBranches())

    def test_moreThanOneBranch(self):
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
    def test_initialRepositoryStateNoRemote(self):
        execute(['git', 'init'])

        self.assertEqual('', gs.gitGetRemoteTrackingBranch(''))
        self.assertEqual('', gs.gitGetRemoteTrackingBranch('master'))

    def test_initialRepositoryStateWithRemote(self):
        LOCAL = 'local'
        createEmptyRemoteLocalPair('remote', LOCAL)
        os.chdir(LOCAL)

        self.assertEqual(''             , gs.gitGetRemoteTrackingBranch(''))
        self.assertEqual('origin/master', gs.gitGetRemoteTrackingBranch('master'))

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
class Test_gitUtilFolderIsTracked(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def test_notGitTracked(self):
        self.assertFalse(gs.gitUtilFolderIsTracked())

    def test_initialRepositoryState(self):
        execute(['git', 'init'])
        self.assertTrue(gs.gitUtilFolderIsTracked())

    def test_isGitTracked(self):
        createNonEmptyGitRepository()
        self.assertTrue(gs.gitUtilFolderIsTracked())

#-----------------------------------------------------------------------------
# Placeholders for:
#   gitUtilGetOutput()            - No tests since it's implicitly tested by
#                                   everything else
#   gitUtilOutputSaysNotTracked() - No tests since it's tested indirectly
#                                   through gitUtilFolderIsTracked()
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

class Test_utilGetModifiedFileAsTwoColumns(unittest.TestCase):
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
        modifiedFileStatus = fileStatuses[gs.KEY_FILE_STATUSES_MODIFIED][0]
        self.assertEqual(
            [
                modifiedFileStatus[gs.KEY_FILE_STATUSES_TYPE],
                modifiedFileStatus[gs.KEY_FILE_STATUSES_FILENAME],
            ],
            gs.utilGetModifiedFileAsTwoColumns(modifiedFileStatus)
        )

class Test_utilGetRawBranchesLines(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #   - utilGetRawBranchesLines() just calls other functions that are fully
    #     tested
    #   - so just a minimal test that it works properly with >1 branches
    #-------------------------------------------------------------------------

    def test(self):
        createNonEmptyGitRepository()
        execute(['git', 'checkout', '-b', 'dev'])

        self.assertEqual(3,
            len(gs.utilGetRawBranchesLines(
                'dev', gs.gitGetLocalBranches(), ['dev', 'master']
            ))
        )

class Test_utilGetRawModifiedLines(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #   - utilGetRawModifiedLines() just calls other functions that are fully
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
            len(gs.utilGetRawModifiedLines(gs.gitGetFileStatuses()))
        )

class Test_utilGetRawStagedLines(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #   - utilGetRawStagedLines() just calls other functions that are fully
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
            len(gs.utilGetRawStagedLines(gs.gitGetFileStatuses()))
        )

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
        stagedFileStatus = fileStatuses[gs.KEY_FILE_STATUSES_STAGED][0]
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
        stagedFileStatus = fileStatuses[gs.KEY_FILE_STATUSES_STAGED][0]
        self.assertEqual(
            [
                stagedFileStatus[gs.KEY_FILE_STATUSES_TYPE] + '(100)',
                stagedFileStatus[gs.KEY_FILE_STATUSES_FILENAME] + ' -> ' + NEW_FILE,
            ],
            gs.utilGetStagedFileAsTwoColumns(stagedFileStatus)
        )

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

class Test_utilGetTargetBranch(unittest.TestCase):
    def setUp(self)   : commonTestSetUp(self)
    def tearDown(self): commonTestTearDown(self)

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def test(self):
        self.assertEqual('', gs.utilGetTargetBranch('master', []))
        self.assertEqual('', gs.utilGetTargetBranch('master', ['master']))
        self.assertEqual('', gs.utilGetTargetBranch('master', ['master', 'dev']))

        self.assertEqual(''      , gs.utilGetTargetBranch('dev', []))
        self.assertEqual('master', gs.utilGetTargetBranch('dev', ['master']))
        self.assertEqual('master', gs.utilGetTargetBranch('dev', ['master', 'dev']))
        self.assertEqual(''      , gs.utilGetTargetBranch('dev', ['dev']))

        self.assertEqual(''      , gs.utilGetTargetBranch('hf-my-hotfix', []))
        self.assertEqual('master', gs.utilGetTargetBranch('hf-my-hotfix', ['master']))
        self.assertEqual('master', gs.utilGetTargetBranch('hf-my-hotfix', ['master', 'dev']))
        self.assertEqual(''      , gs.utilGetTargetBranch('hf-my-hotfix', ['dev']))

        self.assertEqual(''   , gs.utilGetTargetBranch('feature-branch', []))
        self.assertEqual(''   , gs.utilGetTargetBranch('feature-branch', ['master']))
        self.assertEqual('dev', gs.utilGetTargetBranch('feature-branch', ['master', 'dev']))

if __name__ == '__main__':
    # Since we have a pile of tests hitting the filesystem, change to a
    # temporary directory up front, just in case we forget to for an individual
    # test (and end up botching stuff in our dev folder)
    initialDir = os.getcwd()
    tempDir = tempfile.TemporaryDirectory()
    os.chdir(tempDir.name)

    # Now it's safe to test!
    unittest.main()

    # Cleanup
    os.chdir(initialDir)
    tempDir.cleanup()
