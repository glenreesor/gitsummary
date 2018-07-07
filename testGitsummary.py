#!/usr/bin/env python3
import gitsummary as gs

import os
import re
import subprocess
import tempfile
import unittest

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

    Args
        List command - The command and args to execute
    """
    subprocess.run(command, stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)

#-----------------------------------------------------------------------------
class Test_gitGetCommitDetails(unittest.TestCase):
    #-------------------------------------------------------------------------
    # setUp and tearDown
    #   - Create/delete a temporary folder where we can do git stuff
    #   - cd into it on creation
    #-------------------------------------------------------------------------
    def setUp(self):
        self.setupInitialDir = os.getcwd()
        self.tempDir = tempfile.TemporaryDirectory()
        os.chdir(self.tempDir.name)

    def tearDown(self):
        os.chdir(self.setupInitialDir)
        self.tempDir.cleanup()

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
    #-------------------------------------------------------------------------
    # setUp and tearDown
    #   - Create/delete a temporary folder where we can do git stuff
    #   - cd into it on creation
    #-------------------------------------------------------------------------
    def setUp(self):
        self.setupInitialDir = os.getcwd()
        self.tempDir = tempfile.TemporaryDirectory()
        os.chdir(self.tempDir.name)

    def tearDown(self):
        os.chdir(self.setupInitialDir)
        self.tempDir.cleanup()

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def test_noCommitsInFirstNotSecond(self):
        NEW_BRANCH = 'newBranch'

        createNonEmptyGitRepository()
        execute(['git', 'checkout', '-b', NEW_BRANCH])

        self.assertEqual(
            gs.gitGetCommitsInFirstNotSecond('master', NEW_BRANCH, True),
            [],
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
        self.assertEqual(len(commitList), 1)
        self.assertEqual(commitList[0], expectedHash)

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

        self.assertEqual(len(commitList), 2)
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

        self.assertEqual(len(commitList), 2)
        for index in 0, 1:
            self.assertEqual(expectedHashes[index], commitList[index])

#-----------------------------------------------------------------------------
class Test_gitGetCurrentBranch(unittest.TestCase):
    #-------------------------------------------------------------------------
    # setUp and tearDown
    #   - Create/delete a temporary folder where we can do git stuff
    #   - cd into it on creation
    #-------------------------------------------------------------------------
    def setUp(self):
        self.setupInitialDir = os.getcwd()
        self.tempDir = tempfile.TemporaryDirectory()
        os.chdir(self.tempDir.name)

    def tearDown(self):
        os.chdir(self.setupInitialDir)
        self.tempDir.cleanup()

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def test_oneBranchExists(self):
        EXPECTED_BRANCH = 'master'

        createNonEmptyGitRepository()
        self.assertEqual(gs.gitGetCurrentBranch(), EXPECTED_BRANCH)

    def test_multipleBranchesExist(self):
        EXPECTED_BRANCH = 'dev'

        createNonEmptyGitRepository()
        execute(['git', 'checkout', '-b', EXPECTED_BRANCH])

        self.assertEqual(gs.gitGetCurrentBranch(), EXPECTED_BRANCH)

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

        self.assertEqual(gs.gitGetCurrentBranch(), EXPECTED_BRANCH)

#-----------------------------------------------------------------------------
class Test_gitGetFileStatuses(unittest.TestCase):
    #-------------------------------------------------------------------------
    # setUp and tearDown
    #   - Create/delete a temporary folder where we can do git stuff
    #   - cd into it on creation
    #-------------------------------------------------------------------------
    def setUp(self):
        self.setupInitialDir = os.getcwd()
        self.tempDir = tempfile.TemporaryDirectory()
        os.chdir(self.tempDir.name)

    def tearDown(self):
        os.chdir(self.setupInitialDir)
        self.tempDir.cleanup()

    #-------------------------------------------------------------------------
    # Tests
    #   - Note: 'git status' docs suggest that it can detect copies in addition
    #           to rename. However according to the following thread, it appears
    #           that it can't, hence no tests for it.
    #               https://marc.info/?l=git&m=141730775928542&w=2
    #-------------------------------------------------------------------------
    def test_nothingToReport(self):
        createNonEmptyGitRepository()
        statuses = gs.gitGetFileStatuses()
        self.assertEqual(statuses[gs.KEY_FILE_STATUSES_STAGED], [])
        self.assertEqual(statuses[gs.KEY_FILE_STATUSES_MODIFIED], [])
        self.assertEqual(statuses[gs.KEY_FILE_STATUSES_UNTRACKED], [])
        self.assertEqual(statuses[gs.KEY_FILE_STATUSES_UNKNOWN], [])

    def test_stageAddedFile(self):
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

        createNonEmptyGitRepository()
        modifiedFile = open(TEST_FILE, 'w')
        modifiedFile.write('a')
        modifiedFile.close()
        execute(['git', 'add', TEST_FILE])

        self.assertEqual(gs.gitGetFileStatuses(), EXPECTED_RESULT)

    def test_stageDeletedFile(self):
        TEST_FILE = 'testfile'
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGED: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'D',
                    gs.KEY_FILE_STATUSES_FILENAME: TEST_FILE,
                },
            ],
            gs.KEY_FILE_STATUSES_MODIFIED: [],
            gs.KEY_FILE_STATUSES_UNTRACKED: [],
            gs.KEY_FILE_STATUSES_UNKNOWN: [],
        }

        createNonEmptyGitRepository()
        createAndCommitFile(TEST_FILE)
        execute(['git', 'rm', TEST_FILE])

        self.assertEqual(gs.gitGetFileStatuses(), EXPECTED_RESULT)

    def test_stageModifiedFile(self):
        TEST_FILE = 'testfile'
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGED: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'M',
                    gs.KEY_FILE_STATUSES_FILENAME: TEST_FILE,
                },
            ],
            gs.KEY_FILE_STATUSES_MODIFIED: [],
            gs.KEY_FILE_STATUSES_UNTRACKED: [],
            gs.KEY_FILE_STATUSES_UNKNOWN: [],
        }

        createNonEmptyGitRepository()
        createAndCommitFile(TEST_FILE)
        modifiedFile = open(TEST_FILE, 'w')
        modifiedFile.write('a')
        modifiedFile.close()
        execute(['git', 'add', TEST_FILE])

        self.assertEqual(gs.gitGetFileStatuses(), EXPECTED_RESULT)

    def test_stageRenamedFile(self):
        TEST_FILE = 'testfile'
        TEST_FILE_RENAMED = 'testfile1'
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGED: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'R',
                    gs.KEY_FILE_STATUSES_FILENAME: TEST_FILE,
                    gs.KEY_FILE_STATUSES_NEW_FILENAME: TEST_FILE_RENAMED,
                    gs.KEY_FILE_STATUSES_HEURISTIC_SCORE: '100',
                },
            ],
            gs.KEY_FILE_STATUSES_MODIFIED: [],
            gs.KEY_FILE_STATUSES_UNTRACKED: [],
            gs.KEY_FILE_STATUSES_UNKNOWN: [],
        }

        createNonEmptyGitRepository()
        createAndCommitFile(TEST_FILE)
        execute(['git', 'mv', TEST_FILE, TEST_FILE_RENAMED])

        self.assertEqual(gs.gitGetFileStatuses(), EXPECTED_RESULT)

    def test_workDirDeletedFile(self):
        TEST_FILE = 'testfile'
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGED: [],
            gs.KEY_FILE_STATUSES_MODIFIED: [
                {
                    gs.KEY_FILE_STATUSES_TYPE: 'D',
                    gs.KEY_FILE_STATUSES_FILENAME: TEST_FILE,
                },
            ],
            gs.KEY_FILE_STATUSES_UNTRACKED: [],
            gs.KEY_FILE_STATUSES_UNKNOWN: [],
        }

        createNonEmptyGitRepository()
        createAndCommitFile(TEST_FILE)
        os.remove(TEST_FILE)

        self.assertEqual(gs.gitGetFileStatuses(), EXPECTED_RESULT)

    def test_workDirModifiedFile(self):
        TEST_FILE = 'testfile'
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGED: [],
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
        createAndCommitFile(TEST_FILE)

        modifiedFile = open(TEST_FILE, 'w')
        modifiedFile.write('a')
        modifiedFile.close()

        self.assertEqual(gs.gitGetFileStatuses(), EXPECTED_RESULT)

    def test_UntrackedFile(self):
        TEST_FILE = 'testfile'
        EXPECTED_RESULT = {
            gs.KEY_FILE_STATUSES_STAGED: [],
            gs.KEY_FILE_STATUSES_MODIFIED: [],
            gs.KEY_FILE_STATUSES_UNTRACKED: [TEST_FILE],
            gs.KEY_FILE_STATUSES_UNKNOWN: [],
        }

        createNonEmptyGitRepository()
        newFile = open(TEST_FILE, 'w')
        newFile.write('a')
        newFile.close()

        self.assertEqual(gs.gitGetFileStatuses(), EXPECTED_RESULT)

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

        self.assertEqual(gs.gitGetFileStatuses(), EXPECTED_RESULT)

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

        self.assertEqual(gs.gitGetFileStatuses(), EXPECTED_RESULT)

#-----------------------------------------------------------------------------
class Test_gitGetLocalBranches(unittest.TestCase):
    #-------------------------------------------------------------------------
    # setUp and tearDown
    #   - Create/delete a temporary folder where we can do git stuff
    #   - cd into it on creation
    #-------------------------------------------------------------------------
    def setUp(self):
        self.setupInitialDir = os.getcwd()
        self.tempDir = tempfile.TemporaryDirectory()
        os.chdir(self.tempDir.name)

    def tearDown(self):
        os.chdir(self.setupInitialDir)
        self.tempDir.cleanup()

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def test_oneBranch(self):
        EXPECTED_BRANCHES = ['master']

        createNonEmptyGitRepository()
        self.assertEqual(gs.gitGetLocalBranches(), EXPECTED_BRANCHES)

    def test_moreThanOneBranch(self):
        NEW_BRANCH = 'dev'
        EXPECTED_BRANCHES = [NEW_BRANCH, 'master']
        EXPECTED_BRANCHES.sort()

        createNonEmptyGitRepository()
        execute(['git', 'checkout', '-b', NEW_BRANCH])

        self.assertEqual(gs.gitGetLocalBranches(), EXPECTED_BRANCHES)

    def test_remoteTrackingBranchExists(self):
        LOCAL = 'local'
        EXPECTED_BRANCHES = ['master']

        createNonEmptyRemoteLocalPair('remote', LOCAL)
        os.chdir(LOCAL)

        self.assertEqual(gs.gitGetLocalBranches(), EXPECTED_BRANCHES)


#-----------------------------------------------------------------------------
class Test_gitGetRemoteTrackingBranch(unittest.TestCase):
    #-------------------------------------------------------------------------
    # setUp and tearDown
    #   - Create/delete a temporary folder where we can do git stuff
    #   - cd into it on creation
    #-------------------------------------------------------------------------
    def setUp(self):
        self.setupInitialDir = os.getcwd()
        self.tempDir = tempfile.TemporaryDirectory()
        os.chdir(self.tempDir.name)

    def tearDown(self):
        os.chdir(self.setupInitialDir)
        self.tempDir.cleanup()

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def test_noRemoteRepository(self):
        createNonEmptyGitRepository()
        self.assertEqual(gs.gitGetRemoteTrackingBranch(''), '')
        self.assertEqual(gs.gitGetRemoteTrackingBranch('master'), '')

    def test_withRemoteRepository(self):
        LOCAL = 'local'

        createNonEmptyRemoteLocalPair('remote', LOCAL)
        os.chdir(LOCAL)
        execute(['git', 'checkout', '-b', 'dev'])

        self.assertEqual(gs.gitGetRemoteTrackingBranch(''), '')
        self.assertEqual(gs.gitGetRemoteTrackingBranch('dev'), '')
        self.assertEqual(gs.gitGetRemoteTrackingBranch('master'), 'origin/master')

#-----------------------------------------------------------------------------
class Test_gitGetStashes(unittest.TestCase):
    #-------------------------------------------------------------------------
    # setUp and tearDown
    #   - Create/delete a temporary folder where we can do git stuff
    #   - cd into it on creation
    #-------------------------------------------------------------------------
    def setUp(self):
        self.setupInitialDir = os.getcwd()
        self.tempDir = tempfile.TemporaryDirectory()
        os.chdir(self.tempDir.name)

    def tearDown(self):
        os.chdir(self.setupInitialDir)
        self.tempDir.cleanup()

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def test_noStashes(self):
        createNonEmptyGitRepository()
        self.assertEqual(gs.gitGetStashes(), [])

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
        self.assertEqual(len(stashes), 1)

        # Test the contents, but be a bit lazy
        #   hash        - just make sure it's 40 alphanumeric character
        #   description - This seems like it could change with later git
        #                 versions, so just confirm it's a string
        oneStash = stashes[0]
        self.assertEqual(len(oneStash[gs.KEY_STASH_FULL_HASH]), 40)
        self.assertTrue(re.match('^[0-9a-z]+$', oneStash[gs.KEY_STASH_FULL_HASH]))

        self.assertEqual(oneStash[gs.KEY_STASH_NAME], 'stash@{0}')
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
        self.assertEqual(len(stashes), 2)

        # Test the contents, but be a bit lazy
        #   hash        - just make sure it's 40 alphanumeric character
        #   description - This seems like it could change with later git
        #                 versions, so just confirm it's a string
        for oneStash in stashes:
            self.assertEqual(len(oneStash[gs.KEY_STASH_FULL_HASH]), 40)
            self.assertTrue(re.match('^[0-9a-z]+$', oneStash[gs.KEY_STASH_FULL_HASH]))

            self.assertTrue(re.match('^stash@{[0-9]+}$', oneStash[gs.KEY_STASH_NAME]))
            self.assertTrue(isinstance(oneStash[gs.KEY_STASH_DESCRIPTION], str))

#-----------------------------------------------------------------------------
class Test_gitUtilFolderIsTracked(unittest.TestCase):
    #-------------------------------------------------------------------------
    # setUp and tearDown
    #   - Create/delete a temporary folder where we can do git stuff
    #   - cd into it on creation
    #-------------------------------------------------------------------------
    def setUp(self):
        self.setupInitialDir = os.getcwd()
        self.tempDir = tempfile.TemporaryDirectory()
        os.chdir(self.tempDir.name)

    def tearDown(self):
        os.chdir(self.setupInitialDir)
        self.tempDir.cleanup()

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def test_notGitTracked(self):
        self.assertFalse(gs.gitUtilFolderIsTracked())

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
class Test_gitUtilRepositoryIsInInitialState(unittest.TestCase):
    #-------------------------------------------------------------------------
    # setUp and tearDown
    #   - Create/delete a temporary folder where we can do git stuff
    #   - cd into it on creation
    #-------------------------------------------------------------------------
    def setUp(self):
        self.setupInitialDir = os.getcwd()
        self.tempDir = tempfile.TemporaryDirectory()
        os.chdir(self.tempDir.name)

    def tearDown(self):
        os.chdir(self.setupInitialDir)
        self.tempDir.cleanup()

    #-------------------------------------------------------------------------
    # Tests
    #-------------------------------------------------------------------------
    def test_isInInitialState(self):
        execute(['git', 'init'])
        self.assertTrue(gs.gitUtilRepositoryIsInInitialState())

    def test_isNotInInitialState(self):
        createNonEmptyGitRepository()
        self.assertFalse(gs.gitUtilRepositoryIsInInitialState())

#-----------------------------------------------------------------------------
class Test_utilGetAheadBehindString(unittest.TestCase):
    #-------------------------------------------------------------------------
    # setUp and tearDown
    #   - Create/delete a temporary folder where we can do git stuff
    #   - cd into it on creation
    #-------------------------------------------------------------------------
    def setUp(self):
        self.setupInitialDir = os.getcwd()
        self.tempDir = tempfile.TemporaryDirectory()
        os.chdir(self.tempDir.name)

    def tearDown(self):
        os.chdir(self.setupInitialDir)
        self.tempDir.cleanup()

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
    #-------------------------------------------------------------------------
    # setUp and tearDown
    #   - Create/delete a temporary folder where we can do git stuff
    #   - cd into it on creation
    #-------------------------------------------------------------------------
    def setUp(self):
        self.setupInitialDir = os.getcwd()
        self.tempDir = tempfile.TemporaryDirectory()
        os.chdir(self.tempDir.name)

    def tearDown(self):
        os.chdir(self.setupInitialDir)
        self.tempDir.cleanup()

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

class Test_utilGetStyledText(unittest.TestCase):
    #-------------------------------------------------------------------------
    # setUp and tearDown
    #   - Create/delete a temporary folder where we can do git stuff
    #   - cd into it on creation
    #-------------------------------------------------------------------------
    def setUp(self):
        self.setupInitialDir = os.getcwd()
        self.tempDir = tempfile.TemporaryDirectory()
        os.chdir(self.tempDir.name)

    def tearDown(self):
        os.chdir(self.setupInitialDir)
        self.tempDir.cleanup()

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

class Test_utilGetColumnAlignedLines(unittest.TestCase):
    #-------------------------------------------------------------------------
    # setUp and tearDown
    #   - Create/delete a temporary folder where we can do git stuff
    #   - cd into it on creation
    #-------------------------------------------------------------------------
    def setUp(self):
        self.setupInitialDir = os.getcwd()
        self.tempDir = tempfile.TemporaryDirectory()
        os.chdir(self.tempDir.name)

    def tearDown(self):
        os.chdir(self.setupInitialDir)
        self.tempDir.cleanup()

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

    def testNonVariableGetPadded(self):
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

    def testVariablePadAndTrunc(self):
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
    #-------------------------------------------------------------------------
    # setUp and tearDown
    #   - Create/delete a temporary folder where we can do git stuff
    #   - cd into it on creation
    #-------------------------------------------------------------------------
    def setUp(self):
        self.setupInitialDir = os.getcwd()
        self.tempDir = tempfile.TemporaryDirectory()
        os.chdir(self.tempDir.name)

    def tearDown(self):
        os.chdir(self.setupInitialDir)
        self.tempDir.cleanup()

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
    #-------------------------------------------------------------------------
    # setUp and tearDown
    #   - Create/delete a temporary folder where we can do git stuff
    #   - cd into it on creation
    #-------------------------------------------------------------------------
    def setUp(self):
        self.setupInitialDir = os.getcwd()
        self.tempDir = tempfile.TemporaryDirectory()
        os.chdir(self.tempDir.name)

    def tearDown(self):
        os.chdir(self.setupInitialDir)
        self.tempDir.cleanup()

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

class Test_utilGetStagedFileAsTwoColumns(unittest.TestCase):
    #-------------------------------------------------------------------------
    # setUp and tearDown
    #   - Create/delete a temporary folder where we can do git stuff
    #   - cd into it on creation
    #-------------------------------------------------------------------------
    def setUp(self):
        self.setupInitialDir = os.getcwd()
        self.tempDir = tempfile.TemporaryDirectory()
        os.chdir(self.tempDir.name)

    def tearDown(self):
        os.chdir(self.setupInitialDir)
        self.tempDir.cleanup()

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
    #-------------------------------------------------------------------------
    # setUp and tearDown
    #   - Create/delete a temporary folder where we can do git stuff
    #   - cd into it on creation
    #-------------------------------------------------------------------------
    def setUp(self):
        self.setupInitialDir = os.getcwd()
        self.tempDir = tempfile.TemporaryDirectory()
        os.chdir(self.tempDir.name)

    def tearDown(self):
        os.chdir(self.setupInitialDir)
        self.tempDir.cleanup()

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

if __name__ == '__main__':
    # Since we have a pile of testings hitting the filesystem, change to a
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
