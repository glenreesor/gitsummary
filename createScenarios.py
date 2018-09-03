#!/usr/bin/env python3

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
    os.mkdir(scenarioFolder)
    os.chdir(scenarioFolder)
    scenarioSetupFn()
    os.chdir('..')

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
    for aFile in [MODIFIED_FILE_1, MODIFIED_FILE_2, FILE_FOR_STASH]:
        utilCreateAndCommitFile(aFile)

    # Create the two stashes
    stashedFileHandle = open(FILE_FOR_STASH, 'w')
    stashedFileHandle.write('a')
    stashedFileHandle.close()
    utilExecute(['git', 'stash'])

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

def utilCreateAndCommitFile(filename, commitMsg = 'Commit Message'):
    """
    Create the specified file (empty) in the current working directory then
    'git add' and 'git commit'.

    Args
        String filename  - The name of the file to create
        String commitMsg - The commit message to use
    """
    newFile = open(filename, 'w')
    newFile.close()
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
