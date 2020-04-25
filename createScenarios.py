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
    In the current folder, create the following environment. We want unique
    numbers for ease of testing the shell helper option.
        - 2 stashes
        - 3 staged files
        - 4 modified workdir files
        - 5 merge conflicts
        - 6 untracked files
    """

    CONFLICT_BRANCH = 'f/conflict-branch'
    STASH_FILE = 'file-for-stash'
    STAGED_FILES = ['1-Hewey', '2-Louie', '3-Dewey']
    WORKDIR_FILES = ['1-Egon', '2-Winston', '3-Peter', '4-Ray']
    UNMERGED_FILES = ['1-Ron', '2-Fred', '3-George', '4-Percy', '5-Ginny']
    UNTRACKED_FILES = ['1-Luke', '2-Han', '3-Leia', '4-Chewie', '5-3PO', '6-R2']

    #---------------------------------------------------------------------------
    # Create repo and an initial file, since otherwise ref 'master' won't exist
    #---------------------------------------------------------------------------
    utilExecute(['git', 'init'])
    utilCreateAndCommitFile('kangaroo')

    #---------------------------------------------------------------------------
    # Create the branch and files that will be used to create the merge conflicts
    #---------------------------------------------------------------------------
    utilExecute(['git', 'checkout', '-b', CONFLICT_BRANCH, 'master'])
    for aFile in UNMERGED_FILES:
        utilCreateAndCommitFile(aFile, 'Commit comment')

    #---------------------------------------------------------------------------
    # Switch to new 'dev', where we're going to setup all required files and commits
    #---------------------------------------------------------------------------
    utilExecute(['git', 'checkout', '-b', 'dev', 'master'])

    #---------------------------------
    # First do things that require commits or stashing
    #---------------------------------

    # Stashes
    utilCreateAndCommitFile(STASH_FILE, 'The front fell off', 'Commit msg')

    # First stash
    utilModifyFile(STASH_FILE, 'Oh! I turned it off!')
    utilExecute(['git', 'stash', 'push', '-m', 'Some pretty amazing work here'])

    # Second stash
    utilModifyFile(STASH_FILE, 'Yes, I am a ninja')
    utilExecute(['git', 'stash', 'push', '-m', 'Started doing something'])

    # Make the changes that will cause merge conflicts
    for aFile in UNMERGED_FILES:
        utilCreateAndCommitFile(aFile, 'hijkellomellop')

    # Create the initial files which will be used for the 'Work Dir' section
    for aFile in WORKDIR_FILES:
        utilCreateAndCommitFile(aFile)

    #---------------------------------
    # Now do things that don't require commits
    #---------------------------------

    # Create the merge conflict
    # Can't use utilExecute() helper since 'git merge' will return a non-zero
    # exit status
    subprocess.run(
        ['git', 'merge', CONFLICT_BRANCH],
        stdout = subprocess.DEVNULL,
        stderr = subprocess.DEVNULL,
        check=False
    )

    # Stage changes
    for aFile in STAGED_FILES:
        utilCreateFile(aFile)
        utilExecute(['git', 'add', aFile])

    # Work Dir changes
    for aFile in WORKDIR_FILES:
        utilModifyFile(aFile, 'modified contents')

    # Untracked files
    for aFile in UNTRACKED_FILES:
        utilCreateFile(aFile)

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

    utilModifyFile(FILE_FOR_STASH, 'contents2')
    utilExecute(['git', 'stash'])

    # Commit a change so the next stash is on a different commit
    utilModifyAndCommitFile(FILE_FOR_STASH, 'contents3', 'Fix something')
    utilModifyFile(FILE_FOR_STASH, 'contents4')
    utilExecute(['git', 'stash'])

    # Stage changes
    for aFile in [STAGE_FILE_1, STAGE_FILE_2]:
        utilCreateFile(aFile)
        utilExecute(['git', 'add', aFile])

    # Work Dir files
    for aFile in [WORK_DIR_FILE_1, WORK_DIR_FILE_2]:
        utilModifyFile(aFile, 'modified contents')

    # Untracked files
    for aFile in [UNTRACKED_FILE_1, UNTRACKED_FILE_2]:
        utilCreateFile(aFile)

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
def utilCreateFile(filename, contents = 'Default contents'):
    """
    Create the specified file with the specified contents in the current working
    directory.

    An exception will be thrown if the file exists already.

    Args
        String filename  - The name of the file to create
        String contents  - The contents to be written to the file
    """
    newFile = open(filename, 'x')
    newFile.write(contents)
    newFile.close()

#-----------------------------------------------------------------------------
def utilCreateAndCommitFile(
    filename,
    contents = 'Default contents',
    commitMsg = 'Commit message'
):
    """
    Create the specified file with the specified contents in the current working
    directory then 'git add' and 'git commit'.

    An exception will be thrown if the file exists already.

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
def utilModifyFile(filename, contents = 'default modified contents'):
    """
    Replace the contents of the specified file with the specified contents, in
    the current working directory.

    Throws an error if the file does not already exist.

    Args
        String filename  - The name of the file
        String contents  - The contents to be written to the file
    """
    if (not os.path.isfile(filename)):
        raise Exception('File does not exist')

    modifiedFile = open(filename, 'w')
    modifiedFile.write(contents)
    modifiedFile.close()

#-----------------------------------------------------------------------------
def utilModifyAndCommitFile(
    filename,
    contents = 'default modified contents',
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

    An exception will be thrown if the command has a non-zero exit code.

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
