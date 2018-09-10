#!/usr/bin/env python3

# Copyright 2018 Glen Reesor
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

    STAGED_FILE_1 = 'staged-file1'
    STAGED_FILE_2 = 'staged-file2'
    MODIFIED_FILE_1 = 'modified-file1'
    MODIFIED_FILE_2 = 'modified-file2'
    FILE_FOR_STASH = 'file-for-stash'
    UNTRACKED_FILE_1 = 'untracked-file1'
    UNTRACKED_FILE_2 = 'untracked-file2'

    # Create the initial files, which will be used for the 'Modified' section
    utilExecute(['git', 'init'])
    for aFile in [MODIFIED_FILE_1, MODIFIED_FILE_2]:
        utilModifyAndCommitFile(aFile)

    # Create the two stashes
    utilModifyAndCommitFile(FILE_FOR_STASH, 'contents1', 'Fix something else')

    stashedFileHandle = open(FILE_FOR_STASH, 'w')
    stashedFileHandle.write('a')
    stashedFileHandle.close()
    utilExecute(['git', 'stash'])

    utilModifyAndCommitFile(FILE_FOR_STASH, 'contents2', 'Fix something')
    stashedFileHandle = open(FILE_FOR_STASH, 'w')
    stashedFileHandle.write('b')
    stashedFileHandle.close()
    utilExecute(['git', 'stash'])

    # Stage changes
    for aFile in [STAGED_FILE_1, STAGED_FILE_2]:
        stagedFileHandle = open(aFile, 'w')
        stagedFileHandle.write('a')
        stagedFileHandle.close()
        utilExecute(['git', 'add', aFile])

    # Modified files
    for aFile in [MODIFIED_FILE_1, MODIFIED_FILE_2]:
        modifiedFileHandle = open(aFile, 'w')
        modifiedFileHandle.write('a')
        modifiedFileHandle.close()

    # Untracked files
    for aFile in [UNTRACKED_FILE_1, UNTRACKED_FILE_2]:
        untrackedFileHandle = open(aFile, 'w')
        untrackedFileHandle.write('a')
        untrackedFileHandle.close()

    # Make another branch
    utilExecute(['git', 'checkout', '-b', 'dev'])

def createScenarioDemo():
    """
    In the current folder, create the environment for:
        - Demo output showing gitsummary capabilities
        - Branches
            commit1   commit2   commit3   commit4   commit5    ... commitX
            master
                                          dev
                      feature-make-awesome
                                                               feature-make-faster
                      hf-fix-bad-bug

        - Staged files etc will be setup on feature-make-faster, hence "X"
          in "commitX" above, and below in remotes

        - Remotes:
            master              : in sync
            dev                 : in sync
            feature-make-awesome: no remote
            feature-make-faster : +X

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

    utilModifyAndCommitFile(WORK_FILE, 'contents1', 'commit1')
    utilExecute(['git', 'push'])

    utilExecute(['git', 'checkout', '-b', 'dev', 'master'])
    utilExecute(['git', 'push', '--set-upstream', 'origin', 'dev'])

    utilExecute(['git', 'checkout', '-b', 'hf-fix-bad-bug', 'master'])
    utilModifyAndCommitFile(WORK_FILE, 'contents2', 'commit2')

    utilExecute(['git', 'checkout', 'dev'])
    utilModifyAndCommitFile(WORK_FILE, 'contents3', 'commit3')
    utilExecute(['git', 'push'])

    utilExecute(['git', 'checkout', '-b', 'feature-make-awesome', 'dev'])

    utilExecute(['git', 'checkout', 'dev'])
    utilModifyAndCommitFile(WORK_FILE, 'contents4', 'commit4')
    utilModifyAndCommitFile(WORK_FILE, 'contents5', 'commit5')
    utilExecute(['git', 'push'])

    utilExecute(['git', 'checkout', '-b', 'feature-make-faster', 'dev'])
    utilModifyAndCommitFile(WORK_FILE, 'contents6', 'commit6')
    utilExecute(['git', 'push', '--set-upstream', 'origin', 'feature-make-faster'])
    utilModifyAndCommitFile(WORK_FILE, 'contents6a', 'commit6a')
    utilModifyAndCommitFile(WORK_FILE, 'contents6b', 'commit6b')

    #-------------------------------------------------------------------------
    # Setup files to get two entries in each section of gitsummary output
    #-------------------------------------------------------------------------
    STAGED_FILE_1 = 'app.js'
    STAGED_FILE_2 = '.eslintrc'
    MODIFIED_FILE_1 = 'index.html'
    MODIFIED_FILE_2 = 'app.css'
    FILE_FOR_STASH = 'file-for-stash'
    UNTRACKED_FILE_1 = 'todo.txt'
    UNTRACKED_FILE_2 = 'test.output'

    # Create the initial files, which will be used for the 'Modified' section
    for aFile in [MODIFIED_FILE_1, MODIFIED_FILE_2]:
        utilModifyAndCommitFile(aFile)

    # Create the two stashes
    utilModifyAndCommitFile(FILE_FOR_STASH, 'contents1', 'Fix something else')

    stashedFileHandle = open(FILE_FOR_STASH, 'w')
    stashedFileHandle.write('a')
    stashedFileHandle.close()
    utilExecute(['git', 'stash'])

    utilModifyAndCommitFile(FILE_FOR_STASH, 'contents2', 'Fix something')
    stashedFileHandle = open(FILE_FOR_STASH, 'w')
    stashedFileHandle.write('b')
    stashedFileHandle.close()
    utilExecute(['git', 'stash'])

    # Stage changes
    for aFile in [STAGED_FILE_1, STAGED_FILE_2]:
        stagedFileHandle = open(aFile, 'w')
        stagedFileHandle.write('a')
        stagedFileHandle.close()
        utilExecute(['git', 'add', aFile])

    # Modified files
    for aFile in [MODIFIED_FILE_1, MODIFIED_FILE_2]:
        modifiedFileHandle = open(aFile, 'w')
        modifiedFileHandle.write('a')
        modifiedFileHandle.close()

    # Untracked files
    for aFile in [UNTRACKED_FILE_1, UNTRACKED_FILE_2]:
        untrackedFileHandle = open(aFile, 'w')
        untrackedFileHandle.write('a')
        untrackedFileHandle.close()

def createScenarioDetachedHead():
    """
    In the current folder, create the environment for:
        - Detached head state
    """
    utilExecute(['git', 'init'])
    utilModifyAndCommitFile('file1')
    previousCommitHash = subprocess.check_output(
        ['git', 'rev-list', '--max-count=1', 'master'],
        universal_newlines = True
    ).splitlines()[0]
    utilModifyAndCommitFile('file2')
    utilExecute(['git', 'checkout', previousCommitHash])

def utilModifyAndCommitFile(
    filename,
    contents = 'default contents',
    commitMsg = 'Default commit message'
):
    """
    Modify (or create if it doesn't exist) the specified file, with the specified
    contents, in the current working directory then 'git add' and 'git commit'.

    Args
        String filename  - The name of the file
        String contents  - The contents for the file
        String commitMsg - The commit message to use
    """
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
