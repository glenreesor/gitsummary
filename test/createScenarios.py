#!/usr/bin/env python3

# Copyright 2018-2020 Glen Reesor
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

import sys
sys.path.append('..')
import gitsummary  # So we have access to the default .gitsummaryconfig

import json
import os
import subprocess

#------------------------------------------------------------------------------
# Setup folders for various test scenarios
#------------------------------------------------------------------------------

def main():
    DEFAULT_FOLDER = '/tmp/gitsummary.scenarios'
    print(
        'Folder in which to create different scenarios [' + DEFAULT_FOLDER + ']'
    )

    valid = False
    while not valid:
        inputString = input()
        destFolder = DEFAULT_FOLDER if inputString == '' else inputString

        try:
            os.mkdir(destFolder)
            valid = True
        except Exception as e:
            print('Unable to create ' + destFolder)
            print(str(e))
            print()
            print('Try again.')

    os.chdir(destFolder)
    setupScenario(
        'ahead-behind-remote-and-target',
        createScenarioAheadBehindRemoteAndTarget
    )
    setupScenario('all-sections', createScenarioAllSections)
    setupScenario('detached-head', createScenarioDetachedHead)
    setupScenario('example', createScenarioExample)
    setupScenario('git-init-state', createScenarioGitInitState)
    setupScenario('long-branch-name', createScenarioLongBranchName)

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

def createScenarioAheadBehindRemoteAndTarget():
    """
    In the current folder, create an environment where a branch is:
        - ahead and behind its remote branch
        - ahead and behind its target branch

    We want unique numbers for testing the shell helper option.

              rm1 --- rm2 (Remote master)
             /
            /- m1 --- m2 --- m3 --- m4 (master)
           /
    common1                    rd1 --- rd2 (Remote develop)
           \                  /
            common2 -- common3
                              \
                               d1 (develop)

    This will result in:
         master:
            - ahead of its remote by 4
            - behind its remote by 2

         develop:
            - ahead of its remote by 1
            - behind its remote by 2
            - ahead of its target by 3
            - behind its target by 4
    """
    MY_FILE = 'myFile'
    parent = os.getcwd()

    #-------------------------------------------------------------------------
    # Create the above scenario using 3 repos:
    #   - REMOTE
    #   - LOCAL, which will end up with the above scenario
    #   - LOCAL-HELPER, which will be used to push to REMOTE, so LOCAL will
    #     end up being behind REMOTE as appropriate
    #-------------------------------------------------------------------------
    REMOTE = 'remote'
    LOCAL = 'local'
    LOCAL_HELPER = 'local-helper'

    #-------------------------------------------------------------------------
    # REMOTE Step 1:
    #   - Create master: 'common1'
    #   - Create develop: 'common2', 'common3'
    #-------------------------------------------------------------------------
    utilExecute(['git', 'init', '--bare', REMOTE])

    utilExecute(['git', 'clone', REMOTE, LOCAL_HELPER])
    os.chdir(LOCAL_HELPER)

    utilCreateAndCommitFile(MY_FILE, 'common1', 'common1')
    utilExecute(['git', 'push'])

    utilExecute(['git', 'checkout', '-b', 'develop'])
    utilModifyAndCommitFile(MY_FILE, 'common2', 'common2')
    utilModifyAndCommitFile(MY_FILE, 'common3', 'common3')

    utilExecute(['git', 'push', '--set-upstream', 'origin', 'develop'])

    #-------------------------------------------------------------------------
    # LOCAL Step 1:
    #   - Clone from REMOTE so we get 'common1', 'common2', 'common3'
    #   - This is all we want in common with REMOTE
    #-------------------------------------------------------------------------
    os.chdir(parent)
    utilExecute(['git', 'clone', REMOTE, LOCAL])

    #-------------------------------------------------------------------------
    # REMOTE Step 2:
    #   - Create the commits that will not be pulled by LOCAL:
    #       - master: rm1, rm2
    #       - develop: rd1, rd2
    #-------------------------------------------------------------------------
    os.chdir(parent)
    os.chdir(LOCAL_HELPER)

    utilExecute(['git', 'checkout', 'master'])
    utilModifyAndCommitFile(MY_FILE, 'rm1', 'rm1')
    utilModifyAndCommitFile(MY_FILE, 'rm2', 'rm2')
    utilExecute(['git', 'push'])

    utilExecute(['git', 'checkout', 'develop'])
    utilModifyAndCommitFile(MY_FILE, 'rd1', 'rd1')
    utilModifyAndCommitFile(MY_FILE, 'rd2', 'rd2')
    utilExecute(['git', 'push'])

    #-------------------------------------------------------------------------
    # LOCAL Step 2:
    #   - Create remaining commits:
    #       - master: m1, m2, m3, m4
    #       - develop: d1
    #   - fetch from remote so we're aware of being ahead/behind
    #
    #-------------------------------------------------------------------------
    os.chdir(parent)
    os.chdir(LOCAL)

    utilExecute(['git', 'checkout', 'master'])
    utilModifyAndCommitFile(MY_FILE, 'm1', 'm1')
    utilModifyAndCommitFile(MY_FILE, 'm2', 'm2')
    utilModifyAndCommitFile(MY_FILE, 'm3', 'm3')
    utilModifyAndCommitFile(MY_FILE, 'm4', 'm4')

    utilExecute(['git', 'checkout', 'develop'])
    utilModifyAndCommitFile(MY_FILE, 'd1', 'd1')

    utilExecute(['git', 'fetch'])

    #-------------------------------------------------------------------------
    # Final step: Create a file showing the expected ahead/behind numbers
    #-------------------------------------------------------------------------
    utilCreateFile(
        'Expected Numbers.txt',
        'develop\n    Remote: +1   -2\n    Target: +3   -4\n'
    )

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
    # Switch to new 'develop', where we're going to setup all required files and
    # commits
    #---------------------------------------------------------------------------
    utilExecute(['git', 'checkout', '-b', 'develop', 'master'])

    #---------------------------------------------------------------------------
    # Step 1: Things that require commits or stashing
    #   - 2 stashes
    #   - commits to cause merge conflcits
    #   - initial versions for Work Dir files
    #---------------------------------------------------------------------------
    utilCreateAndCommitFile(STASH_FILE, 'The front fell off', 'Commit msg')
    utilModifyFile(STASH_FILE, 'Oh! I turned it off!')
    utilExecute(['git', 'stash', 'push', '-m', 'Some pretty amazing work here'])

    utilModifyFile(STASH_FILE, 'Yes, I am a ninja')
    utilExecute(['git', 'stash', 'push', '-m', 'Started doing something'])

    for aFile in UNMERGED_FILES:
        utilCreateAndCommitFile(aFile, 'hijkellomellop')

    for aFile in WORKDIR_FILES:
        utilCreateAndCommitFile(aFile)

    #---------------------------------------------------------------------------
    # Step 2: Things that don't require commits
    #---------------------------------------------------------------------------
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

def createScenarioExample():
    """
    In the current folder, create the environment for:
        - Sample output showing gitsummary capabilities
        - Branches are a pain, so this will just create the required files
          (so we don't have to fiddle with as much formatting later)

    """

    BRANCHES=[
        'develop',
        'feature-ds2-defences-phase2',
        'feature-endor-shield-generator'
    ]
    CURRENT_BRANCH='hotfix-stabilize-reactor-core'
    STAGE_FILES=['controller-superlaser.f77', 'controller-turbolaser.f77']
    STASH_FILE='stashFile'
    WORK_DIR_FILE='controller-ion-cannon.f77'
    UNTRACKED_FILES=['ds1-thermal-exhaust-port.cobol', 'npm.faq']

    #-------------------------------------------------------------------------
    # Init repository and create the extra branches
    #-------------------------------------------------------------------------
    utilExecute(['git', 'init'])
    utilCreateAndCommitFile('bob')

    for branch in BRANCHES:
        utilExecute(['git', 'checkout', '-b', branch, 'master'])

    #-------------------------------------------------------------------------
    # Now all the files
    #-------------------------------------------------------------------------
    utilExecute(['git', 'checkout', '-b', 'hotfix-stabilize-reactor-core', 'master'])

    # Stash
    utilCreateAndCommitFile(STASH_FILE)
    utilModifyFile(STASH_FILE)
    utilExecute(['git', 'stash', 'push', '-m', 'First try'])

    # Work Dir
    utilCreateAndCommitFile(WORK_DIR_FILE)
    utilModifyFile(WORK_DIR_FILE)

    # Stage
    for stageFile in STAGE_FILES:
        utilCreateFile(stageFile)
        utilExecute(['git', 'add', stageFile])

    # Untracked
    for untrackedFile in UNTRACKED_FILES:
        utilCreateFile(untrackedFile)

def createScenarioGitInitState():
    """
    In the current folder, create the environment immediately after 'git init'.
    We need this for testing the shell helper
    """
    utilExecute(['git', 'init'])

def createScenarioLongBranchName():
    """
    In the current folder, create the environment for testing truncation
    of the shell helper's output:
        - Super long branch name
        - Other stuff so we'll know if the shell helper is removing them
            - A modified file
            - A staged file
            - An untracked file
    """
    MODIFIED_FILE = 'modifiedFile'
    STAGED_FILE = 'stagedFile'
    UNTRACKED_FILE = 'untrackedFile'

    utilExecute(['git', 'init'])
    utilCreateAndCommitFile(MODIFIED_FILE)

    # We want 'develop' so shell helper will show it as a target
    utilExecute(['git', 'checkout', '-b', 'develop'])

    # Super long branch
    utilExecute(['git', 'checkout', '-b', 'f/super-doooper-long-branch-name'])

    # Other stuff as per above
    utilModifyFile(MODIFIED_FILE)
    utilCreateFile(UNTRACKED_FILE)
    utilCreateFile(STAGED_FILE)
    utilExecute(['git', 'add', STAGED_FILE])

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
