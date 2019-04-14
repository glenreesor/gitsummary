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

import gitsummary  # So we have access to the default .gitsummaryconfig
import json
import os
import subprocess

#------------------------------------------------------------------------------
# Setup folders for various test scenarios
#------------------------------------------------------------------------------

def main():
    print('Enter subfolder in which to create different scenarios')

    valid = False
    while not valid:
        destFolder = input()
        try:
            os.mkdir(destFolder)
            valid = True
        except Exception as e:
            print('Unable to create ' + destFolder)
            print(str(e))
            print()
            print('Try again.')

    os.chdir(destFolder)
    setupScenario('all-sections', createScenarioAllSections)
    setupScenario('demo', createScenarioDemo)
    setupScenario('detached-head', createScenarioDetachedHead)

def setupScenario(scenarioFolder, scenarioSetupFn):
    """
    Central function for creating scenarios.
        - Create the folder to hold the scenario
        - cd into that folder
        - Create the scenario using the specified function
        - cd out of that folder

    We use this one central function so there aren't multiple places where
    folder creation and folder navigation needs to be tested. Don't want to
    accidentally mess up filesystem.

    Args
        String   scenarioFolder  - The name of the folder in which to create
                                   the scenario
        Function scenarioSetupFn - The function that will create the environment
    """
    print('Creating ' + scenarioFolder)
    cwd = os.getcwd()
    os.mkdir(scenarioFolder)
    os.chdir(scenarioFolder)
    scenarioSetupFn()
    os.chdir(cwd)

def createScenarioAllSections():
    """
    In the current folder, create the environment for:
        - Each section of gitsummary output will have two entries
    """

    STAGE_FILE_1 = 'stage-file1'
    STAGE_FILE_2 = 'stage-file2'
    WORK_DIR_FILE_1 = 'workdir-file1'
    WORK_DIR_FILE_2 = 'workdir-file2'
    FILE_FOR_STASH = 'file-for-stash'
    UNTRACKED_FILE_1 = 'untracked-file1'
    UNTRACKED_FILE_2 = 'untracked-file2'
    UNMERGED_FILE_1 = 'unmerged-file1'
    UNMERGED_FILE_2 = 'unmerged-file2'

    #---------------------------------------------------------------------------
    # Create repo and an initial file, since otherwise ref 'master' won't exist
    #---------------------------------------------------------------------------
    utilExecute(['git', 'init'])
    utilCreateAndCommitFile('kangaroo')

    #---------------------------------------------------------------------------
    # Create the branch and files that will be used to create the merge conflicts
    #---------------------------------------------------------------------------
    utilExecute(['git', 'checkout', '-b', 'branch1', 'master'])
    for aFile in [UNMERGED_FILE_1, UNMERGED_FILE_2]:
        utilCreateAndCommitFile(aFile, 'abcdefg')

    #---------------------------------------------------------------------------
    # Switch to another branch to do everything else
    #---------------------------------------------------------------------------
    utilExecute(['git', 'checkout', '-b', 'dev', 'master'])

    #---------------------------------
    # First do things that require commits
    #---------------------------------

    # Create the two stashes
    utilCreateAndCommitFile(FILE_FOR_STASH, 'contents1', 'Fix something else')

    fileHandle = open(FILE_FOR_STASH, 'w')
    fileHandle.write('a')
    fileHandle.close()
    utilExecute(['git', 'stash'])

    utilModifyAndCommitFile(FILE_FOR_STASH, 'contents2', 'Fix something')
    fileHandle = open(FILE_FOR_STASH, 'w')
    fileHandle.write('b')
    fileHandle.close()
    utilExecute(['git', 'stash'])

    # Make the changes that will cause merge conflicts
    for aFile in [UNMERGED_FILE_1, UNMERGED_FILE_2]:
        utilCreateAndCommitFile(aFile, 'hijkellomellop')

    # Create the initial files which will be used for the 'Work Dir' section
    for aFile in [WORK_DIR_FILE_1, WORK_DIR_FILE_2]:
        utilCreateAndCommitFile(aFile)

    #---------------------------------
    # Now do things that don't require commits
    #---------------------------------

    # Create the merge conflict
    # Can't use utilExecute() helper since 'git merge' will return a non-zero
    # exit status
    subprocess.run(
        ['git', 'merge', 'branch1'],
        stdout = subprocess.DEVNULL,
        stderr = subprocess.DEVNULL,
        check=False
    )

    # Stage changes
    for aFile in [STAGE_FILE_1, STAGE_FILE_2]:
        fileHandle = open(aFile, 'w')
        fileHandle.write('a')
        fileHandle.close()
        utilExecute(['git', 'add', aFile])

    # Work Dir changes
    for aFile in [WORK_DIR_FILE_1, WORK_DIR_FILE_2]:
        fileHandle = open(aFile, 'w')
        fileHandle.write('a')
        fileHandle.close()

    # Untracked files
    for aFile in [UNTRACKED_FILE_1, UNTRACKED_FILE_2]:
        fileHandle = open(aFile, 'w')
        fileHandle.write('a')
        fileHandle.close()

def createScenarioDemo():
    """
    In the current folder, create the environment for:
        - Demo output showing gitsummary capabilities
        - Branches
            commit1   commit2   commit3   commit4   commit5    ... commitX
            master
                                          develop
                      make-awesome-new-thing
                                                               make-faster
                      hotfix-fix-something-bad

        - Stage files etc will be setup on make-faster, hence "X"
          in "commitX" above, and below in remotes

        - Remotes:
            master                 : in sync
            develop                : in sync
            make-awesome-new-thing : no remote
            make-faster            : +X

        - Two entries in each section of gitsummary output
    """

    #-------------------------------------------------------------------------
    # Create branches
    #-------------------------------------------------------------------------
    REMOTE = 'remote'
    LOCAL = 'local'
    WORK_FILE = 'branch-work-setup'

    utilExecute(['git', 'init', '--bare', REMOTE])
    utilExecute(['git', 'clone', REMOTE, LOCAL])
    os.chdir(LOCAL)

    utilCreateAndCommitFile(WORK_FILE, 'contents1', 'commit1')
    utilExecute(['git', 'push'])

    utilExecute(['git', 'checkout', '-b', 'develop', 'master'])
    utilExecute(['git', 'push', '--set-upstream', 'origin', 'develop'])

    utilExecute(['git', 'checkout', '-b', 'hotfix-fix-something-bad', 'master'])
    utilModifyAndCommitFile(WORK_FILE, 'contents2', 'commit2')

    utilExecute(['git', 'checkout', 'develop'])
    utilModifyAndCommitFile(WORK_FILE, 'contents3', 'commit3')
    utilExecute(['git', 'push'])

    utilExecute(['git', 'checkout', '-b', 'make-awesome-new-thing', 'develop'])

    utilExecute(['git', 'checkout', 'develop'])
    utilModifyAndCommitFile(WORK_FILE, 'contents4', 'commit4')
    utilModifyAndCommitFile(WORK_FILE, 'contents5', 'commit5')
    utilExecute(['git', 'push'])

    utilExecute(['git', 'checkout', '-b', 'make-faster', 'develop'])
    utilModifyAndCommitFile(WORK_FILE, 'contents6', 'commit6')
    utilExecute(['git', 'push', '--set-upstream', 'origin', 'make-faster'])
    utilModifyAndCommitFile(WORK_FILE, 'contents6a', 'commit6a')
    utilModifyAndCommitFile(WORK_FILE, 'contents6b', 'commit6b')

    #-------------------------------------------------------------------------
    # Create .gitsummaryconfig with gitsummary defaults.
    # Do it here so we don't commit the "added" files below.
    #-------------------------------------------------------------------------
    gitsummaryConfigFile = open(gitsummary.CONFIG_FILENAME, 'w')
    json.dump(gitsummary.CONFIG_DEFAULT, gitsummaryConfigFile)
    gitsummaryConfigFile.close()

    utilExecute(['git', 'add', gitsummary.CONFIG_FILENAME])
    utilExecute(['git', 'commit', '-m', 'Add .gitsummaryconfig'])

    #-------------------------------------------------------------------------
    # Setup files to get two entries in each section of gitsummary output
    #-------------------------------------------------------------------------
    STAGE_FILE_1 = 'app.js'
    STAGE_FILE_2 = '.eslintrc'
    WORK_DIR_FILE_1 = 'index.html'
    WORK_DIR_FILE_2 = 'app.css'
    FILE_FOR_STASH = 'file-for-stash'
    UNTRACKED_FILE_1 = 'todo.txt'
    UNTRACKED_FILE_2 = 'test.output'

    # Create the initial files, which will be used for the 'Modified' section
    for aFile in [WORK_DIR_FILE_1, WORK_DIR_FILE_2]:
        utilCreateAndCommitFile(aFile)

    # Create the two stashes
    utilCreateAndCommitFile(FILE_FOR_STASH, 'contents1', 'Fix something else')

    fileHandle = open(FILE_FOR_STASH, 'w')
    fileHandle.write('a')
    fileHandle.close()
    utilExecute(['git', 'stash'])

    utilModifyAndCommitFile(FILE_FOR_STASH, 'contents2', 'Fix something')
    fileHandle = open(FILE_FOR_STASH, 'w')
    fileHandle.write('b')
    fileHandle.close()
    utilExecute(['git', 'stash'])

    # Stage changes
    for aFile in [STAGE_FILE_1, STAGE_FILE_2]:
        fileHandle = open(aFile, 'w')
        fileHandle.write('a')
        fileHandle.close()
        utilExecute(['git', 'add', aFile])

    # Modified files
    for aFile in [WORK_DIR_FILE_1, WORK_DIR_FILE_2]:
        fileHandle = open(aFile, 'w')
        fileHandle.write('a')
        fileHandle.close()

    # Untracked files
    for aFile in [UNTRACKED_FILE_1, UNTRACKED_FILE_2]:
        fileHandle = open(aFile, 'w')
        fileHandle.write('a')
        fileHandle.close()

def createScenarioDetachedHead():
    """
    In the current folder, create the environment for:
        - Detached head state
    """
    utilExecute(['git', 'init'])
    utilCreateAndCommitFile('file1')
    previousCommitHash = subprocess.check_output(
        ['git', 'rev-list', '--max-count=1', 'master'],
        universal_newlines = True
    ).splitlines()[0]
    utilCreateAndCommitFile('file2')
    utilExecute(['git', 'checkout', previousCommitHash])

#-----------------------------------------------------------------------------
# Helpers
#-----------------------------------------------------------------------------
def utilCreateAndCommitFile(
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
    utilExecute(['git', 'add', filename])
    utilExecute(['git', 'commit', '-m', commitMsg])

#-----------------------------------------------------------------------------
def utilModifyAndCommitFile(
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
    utilExecute(['git', 'add', filename])
    utilExecute(['git', 'commit', '-m', commitMsg])

def utilExecute(command):
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

#------------------------------------------------------------------------------
main()
