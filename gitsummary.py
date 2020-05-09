#!/usr/bin/env python3

# Copyright 2016-2019 Glen Reesor
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

import json
import os
import re
import subprocess
import sys

#-------------------------------------------------------------------------------
VERSION = '3.2.0'

#-------------------------------------------------------------------------------
# Constants that have user exposure (so don't change the values)
#-------------------------------------------------------------------------------
KEY_CONFIG_DEFAULT_TARGET = 'defaultTarget'
KEY_CONFIG_BRANCHES = 'branches'
KEY_CONFIG_BRANCH_NAME = 'name'
KEY_CONFIG_BRANCH_ORDER = 'branchOrder'
KEY_CONFIG_BRANCH_TARGET = 'target'

# Output options common to both fullRepoOutput and shellHelper
OPTIONS_OUTPUT_STAGE = 'stage'
OPTIONS_OUTPUT_STASHES = 'stashes'
OPTIONS_OUTPUT_UNMERGED = 'unmerged'
OPTIONS_OUTPUT_UNTRACKED = 'untracked'
OPTIONS_OUTPUT_WORK_DIR = 'workdir'

# Output options applicable to only fullRepoOutput
OPTIONS_OUTPUT_BRANCH_ALL = 'branch-all'
OPTIONS_OUTPUT_BRANCH_CURRENT = 'branch-current'

# Output options applicable to only shellHelper
OPTIONS_OUTPUT_BRANCH_NAME = 'branch-name'
OPTIONS_OUTPUT_TARGET_BRANCH = 'target-branch'
OPTIONS_OUTPUT_AHEAD_REMOTE = 'ahead-remote'
OPTIONS_OUTPUT_AHEAD_TARGET = 'ahead-target'
OPTIONS_OUTPUT_BEHIND_REMOTE = 'behind-remote'
OPTIONS_OUTPUT_BEHIND_TARGET = 'behind-target'

#-------------------------------------------------------------------------------
# Keys to dictionaries so errors will be caught by linter rather than at runtime
#-------------------------------------------------------------------------------
KEY_FILE_STATUSES_STAGE = 'stage'
KEY_FILE_STATUSES_UNKNOWN = 'unknown'
KEY_FILE_STATUSES_UNMERGED = 'unmerged'
KEY_FILE_STATUSES_UNTRACKED = 'untracked'
KEY_FILE_STATUSES_WORK_DIR = 'workdir'

KEY_FILE_STATUSES_TYPE = 'type'
KEY_FILE_STATUSES_FILENAME = 'filename'
KEY_FILE_STATUSES_NEW_FILENAME = 'newFilename'
KEY_FILE_STATUSES_HEURISTIC_SCORE = 'heuristicScore'

KEY_RETURN_STATUS = 'returnStatus'
KEY_RETURN_MESSAGES = 'returnMessages'
KEY_RETURN_VALUE = 'returnValue'

KEY_STASH_FULL_HASH = 'fullHash'
KEY_STASH_NAME = 'name'
KEY_STASH_DESCRIPTION = 'description'

# Related to commandline options
KEY_OPTIONS_COLOR = 'optionsColor'
KEY_OPTIONS_SELECTED_OUTPUT = 'optionsSelectedOutput'
KEY_OPTIONS_MAX_WIDTH = 'optionsMaxWidth'

OPTIONS_COLOR_AUTO = 'color-auto'
OPTIONS_COLOR_NO = 'color-no'
OPTIONS_COLOR_YES = 'color-yes'

OPTIONS_MAX_WIDTH_AUTO = 'max-width-auto'

#-------------------------------------------------------------------------------
# Other constants so we can catch typos by linting
#-------------------------------------------------------------------------------
CURRENT_BRANCH_INDICATOR = '>'

TEXT_BRIGHT = 'bright'
TEXT_NORMAL = 'normal'

TEXT_BLACK = 'black'
TEXT_BLUE = 'blue'
TEXT_CYAN = 'cyan'
TEXT_GREEN = 'green'
TEXT_MAGENTA = 'magenta'
TEXT_YELLOW = 'yellow'
TEXT_RED = 'red'
TEXT_WHITE = 'white'

#-------------------------------------------------------------------------------
# Constants exposed for testing purposes
#-------------------------------------------------------------------------------

# This corresponds to the "--no-optional-locks" commandline option and is
# treated differently than other options since it's only used in one
# place (gitUtilGetOutput). We use a global so we don't have to pass
# this around everywhere
#
# We also set the default here so testGitsummary will work
GLOBAL_GIT_NO_OPTIONAL_LOCKS = False


# Branch names are based on:
#   https://nvie.com/posts/a-successful-git-branching-model/
CONFIG_DEFAULT = {
    KEY_CONFIG_BRANCH_ORDER: [
        '^master$',
        '^develop$',
        '^hotfix-',
        '^release-',
    ],
    KEY_CONFIG_DEFAULT_TARGET: 'develop',
    KEY_CONFIG_BRANCHES: [
        {
            KEY_CONFIG_BRANCH_NAME: '^master$',
            KEY_CONFIG_BRANCH_TARGET: ''
        },
        {
            KEY_CONFIG_BRANCH_NAME:'^develop$',
            KEY_CONFIG_BRANCH_TARGET: 'master'
        },
        {
            KEY_CONFIG_BRANCH_NAME:'^hotfix-',
            KEY_CONFIG_BRANCH_TARGET: 'master'
        },
        {
            KEY_CONFIG_BRANCH_NAME:'^release-',
            KEY_CONFIG_BRANCH_TARGET: 'master'
        },
    ]
}

CONFIG_FILENAME = '.gitsummaryconfig'

#-------------------------------------------------------------------------------
def fullRepoOutput(options):
    """
    Orchestrate all output (full repository)

    Args
        Dictionary options - A dictionary with the following key:
                                KEY_OPTIONS_SELECTED_OUTPUT : List of String

    Example:

    Stashes   stash@{0} This is a stash
              stash@{1} This is another stash

    Stage     A filename1
              A filename2

    Work Dir  M filename1
              M filename2

    Unmerged  A filename1
              M filename2

    Untracked filename1
              filename2

                          Remote   Target
       master              .  .
     > dev                 .  .     .  .  master
       featureBranch       .  .     .  .  dev
    """

    #---------------------------------------------------------------------------
    # Set configuration options
    #---------------------------------------------------------------------------
    configToUse = fsGetConfigToUse()
    if configToUse[KEY_RETURN_STATUS]:
        gitsummaryConfig = configToUse[KEY_RETURN_VALUE]
    else:
        for line in configToUse[KEY_RETURN_MESSAGES]:
            print(line)
        sys.exit()

    #---------------------------------------------------------------------------
    # Figure out if we're running interactively, and set options as appropriate
    #---------------------------------------------------------------------------
    if sys.stdout.isatty():
        (SCREEN_WIDTH, SCREEN_HEIGHT) = os.get_terminal_size()

        useColor = True and (options[KEY_OPTIONS_COLOR] != OPTIONS_COLOR_NO)
        maxWidth = (
            SCREEN_WIDTH
                if options[KEY_OPTIONS_MAX_WIDTH] == OPTIONS_MAX_WIDTH_AUTO
                else int(options[KEY_OPTIONS_MAX_WIDTH])
        )
    else:
        maxWidth= (
            -1
                if options[KEY_OPTIONS_MAX_WIDTH] == OPTIONS_MAX_WIDTH_AUTO
                else int(options[KEY_OPTIONS_MAX_WIDTH])
        )
        useColor = False or (options[KEY_OPTIONS_COLOR] == OPTIONS_COLOR_YES)

    #---------------------------------------------------------------------------
    # Assemble the raw output lines(no colors, padding, or truncation)
    #
    # Each element in raw*Lines below:
    #   - corresponds to one line of output
    #   - is itself another list, where each element corresponds to a column of
    #     output
    #
    # Later steps will:
    #   - pad/truncate columns to ensure proper line length
    #   - add colors
    #---------------------------------------------------------------------------

    fileStatuses = gitGetFileStatuses()
    currentBranch = gitGetCurrentBranch()
    localBranches = gitGetLocalBranches()

    localBranchesInDisplayOrder = utilGetBranchOrder(
        gitsummaryConfig,
        localBranches
    )

    rawStashLines = (
        utilGetRawStashLines()
            if OPTIONS_OUTPUT_STASHES in options[KEY_OPTIONS_SELECTED_OUTPUT]
            else []
        )

    rawStageLines = (
        utilGetRawStageLines(fileStatuses)
            if OPTIONS_OUTPUT_STAGE in options[KEY_OPTIONS_SELECTED_OUTPUT]
            else []
        )

    rawWorkDirLines = (
        utilGetRawWorkDirLines(fileStatuses)
            if OPTIONS_OUTPUT_WORK_DIR in options[KEY_OPTIONS_SELECTED_OUTPUT]
            else []
        )

    rawUnmergedLines = (
        utilGetRawUnmergedLines(fileStatuses)
            if OPTIONS_OUTPUT_UNMERGED in options[KEY_OPTIONS_SELECTED_OUTPUT]
            else []
        )

    rawUntrackedLines = (
        utilGetRawUntrackedLines(fileStatuses)
            if OPTIONS_OUTPUT_UNTRACKED in options[KEY_OPTIONS_SELECTED_OUTPUT]
            else []
        )

    if OPTIONS_OUTPUT_BRANCH_CURRENT in options[KEY_OPTIONS_SELECTED_OUTPUT]:
        rawBranchLines = utilGetRawBranchesLines(
            gitsummaryConfig,
            currentBranch,
            localBranchesInDisplayOrder,
            False,
        )
    elif OPTIONS_OUTPUT_BRANCH_ALL in options[KEY_OPTIONS_SELECTED_OUTPUT]:
        rawBranchLines = utilGetRawBranchesLines(
            gitsummaryConfig,
            currentBranch,
            localBranchesInDisplayOrder,
            True,
        )
    else:
        rawBranchLines = []

    #---------------------------------------------------------------------------
    # For each section of output (stashes, stage, etc):
    #   - Determine maximum widths for each column of each line, so we can
    #     align columns within each section
    #
    # Each xyzMaxColumnWidths will be a List of numbers, where each number
    # is the maximum width of the corresponding column.
    #---------------------------------------------------------------------------
    stashesMaxColumnWidths = utilGetMaxColumnWidths(rawStashLines)
    stageMaxColumnWidths = utilGetMaxColumnWidths(rawStageLines)
    workDirMaxColumnWidths = utilGetMaxColumnWidths(rawWorkDirLines)
    unmergedMaxColumnWidths = utilGetMaxColumnWidths(rawUnmergedLines)
    untrackedMaxColumnWidths = utilGetMaxColumnWidths(rawUntrackedLines)
    branchesMaxColumnWidths = utilGetMaxColumnWidths(rawBranchLines)

    #---------------------------------------------------------------------------
    # Ensure that title column for each of stashes, stage, work dir, unmerged,
    # and untracked is the same width so they line up
    #---------------------------------------------------------------------------
    maxTitleWidths = max(
        stashesMaxColumnWidths[0] if len(stashesMaxColumnWidths) > 0 else 0,
        stageMaxColumnWidths[0] if len(stageMaxColumnWidths) > 0 else 0,
        workDirMaxColumnWidths[0] if len(workDirMaxColumnWidths) > 0 else 0,
        unmergedMaxColumnWidths[0] if len(unmergedMaxColumnWidths) > 0 else 0,
        untrackedMaxColumnWidths[0] if len(untrackedMaxColumnWidths) > 0 else 0,
    )

    if len(stashesMaxColumnWidths) > 0:
        stashesMaxColumnWidths[0] = maxTitleWidths

    if len(stageMaxColumnWidths) > 0:
        stageMaxColumnWidths[0] = maxTitleWidths

    if len(workDirMaxColumnWidths) > 0:
        workDirMaxColumnWidths[0] = maxTitleWidths

    if len(unmergedMaxColumnWidths) > 0:
        unmergedMaxColumnWidths[0] = maxTitleWidths

    if len(untrackedMaxColumnWidths) > 0:
        untrackedMaxColumnWidths[0] = maxTitleWidths

    #---------------------------------------------------------------------------
    # Get all of our lines (still in columns) with each column padded or
    # truncated as required
    #---------------------------------------------------------------------------
    TRUNCATION_INDICATOR = '...'

    alignedStashLines = utilGetColumnAlignedLines(
        maxWidth,
        TRUNCATION_INDICATOR,
        2,
        stashesMaxColumnWidths,
        rawStashLines,
    )

    alignedStageLines = utilGetColumnAlignedLines(
        maxWidth,
        TRUNCATION_INDICATOR,
        2,
        stageMaxColumnWidths,
        rawStageLines,
    )

    alignedWorkDirLines = utilGetColumnAlignedLines(
        maxWidth,
        TRUNCATION_INDICATOR,
        2,
        workDirMaxColumnWidths,
        rawWorkDirLines,
    )

    alignedUnmergedLines = utilGetColumnAlignedLines(
        maxWidth,
        TRUNCATION_INDICATOR,
        2,
        unmergedMaxColumnWidths,
        rawUnmergedLines,
    )

    alignedUntrackedLines = utilGetColumnAlignedLines(
        maxWidth,
        TRUNCATION_INDICATOR,
        1,
        untrackedMaxColumnWidths,
        rawUntrackedLines,
    )

    alignedBranchLines = utilGetColumnAlignedLines(
        maxWidth,
        TRUNCATION_INDICATOR,
        1,
        branchesMaxColumnWidths,
        rawBranchLines,
    )

    #---------------------------------------------------------------------------
    # Final step: Create a single string for each line, with required colors
    #---------------------------------------------------------------------------
    getStyledText = utilGetStyledText if useColor else utilNoopGetStyledText

    styledStashLines = []
    for line in alignedStashLines:
        styledStashLines.append(
            line[0] + ' ' + getStyledText([TEXT_GREEN], line[1]) + ' ' + line[2]
        )

    styledStageLines = []
    for line in alignedStageLines:
        styledStageLines.append(
            line[0] + ' ' + (
                getStyledText([TEXT_BRIGHT, TEXT_GREEN], line[1] + ' ' + line[2])
            )
        )

    styledWorkDirLines = []
    for line in alignedWorkDirLines:
        styledWorkDirLines.append(
            line[0] + ' ' + (
                getStyledText([TEXT_BRIGHT, TEXT_MAGENTA], line[1] + ' ' + line[2])
            )
        )

    styledUnmergedLines = []
    for line in alignedUnmergedLines:
        styledUnmergedLines.append(
            line[0] + ' ' + (
                getStyledText([TEXT_BRIGHT, TEXT_RED], line[1] + ' ' + line[2])
            )
        )

    styledUntrackedLines = []
    for line in alignedUntrackedLines:
        styledUntrackedLines.append(
            line[0] + ' ' + getStyledText([TEXT_CYAN], line[1])
        )

    styledBranchLines = []
    for line in alignedBranchLines:
        # Entire line is bright if it's the current branch
        # Remote Ahead/Behind are cyan if branch differs from its remote
        #   We know a branch differs from its remote if the remote ahead/behind
        #   string (column 2) contains any digits
        isCurrentBranch = (re.search(CURRENT_BRANCH_INDICATOR, line[0]))
        differsFromRemote = re.search('[0-9]', line[2])

        formats = [TEXT_BRIGHT] if isCurrentBranch else []
        remoteFormats = formats + ([TEXT_CYAN] if differsFromRemote else [])

        styledBranchLines.append(
            getStyledText(formats, line[0]) + ' ' +
            getStyledText(formats, line[1]) + ' ' +
            getStyledText(remoteFormats, line[2]) + ' ' +
            getStyledText(formats, line[3]) + ' ' +
            getStyledText(formats, line[4])
        )

    #---------------------------------------------------------------------------
    # Print all our beautifully formatted output
    #---------------------------------------------------------------------------
    previousSectionHadOutput = False
    for section in options[KEY_OPTIONS_SELECTED_OUTPUT]:
        if section == OPTIONS_OUTPUT_BRANCH_ALL or section == OPTIONS_OUTPUT_BRANCH_CURRENT:
            sectionLines = styledBranchLines
        elif section == OPTIONS_OUTPUT_STAGE:
            sectionLines = styledStageLines
        elif section == OPTIONS_OUTPUT_STASHES:
            sectionLines = styledStashLines
        elif section == OPTIONS_OUTPUT_UNMERGED:
            sectionLines = styledUnmergedLines
        elif section == OPTIONS_OUTPUT_UNTRACKED:
            sectionLines = styledUntrackedLines
        elif section == OPTIONS_OUTPUT_WORK_DIR:
            sectionLines = styledWorkDirLines
        else:
            print('Whoa! Something went wrong! Unknown --custom section: ' + section)
            sys.exit(1)

        if previousSectionHadOutput:
            print()
        for line in sectionLines:
            print(line)
        previousSectionHadOutput = True if len(sectionLines) > 0 else False

    #---------------------------------------------------------------------------
    # Notify user if git returned something we didn't know how to handle
    #---------------------------------------------------------------------------
    rawUnknownFileList = fileStatuses[KEY_FILE_STATUSES_UNKNOWN]
    if len(rawUnknownFileList) > 0:
        print('git returned some unexpected output:')
        print('')
        for unknownOutput in rawUnknownFileList:
            print(unknownOutput)

        print('\nPlease notify the gitsummary author.')

#-------------------------------------------------------------------------------
def shellPromptHelper(options):
    """
    Orchestrate output for the shell prompt helper functionality

    Output is a single line of space-separated values as specified in options:
        - The following values are the number of corresponding entities:
            - STASHES, STAGE, WORK_DIR, UNMERGED, UNTRACKED

        - The following values are either numbers or "_" if current branch
          does not have a remote tracking branch:
            - AHEAD_REMOTE, BEHIND_REMOTE

        - The following values are either numbers or "_" if current branch
          does not have a target branch
            - AHEAD_TARGET, BEHIND_TARGET

        - The following values are strings or '_' if not applicable:
            - BRANCH_NAME, TARGET_NAME

    Args
        Dictionary options - A dictionary with the following key:
                                KEY_OPTIONS_SELECTED_OUTPUT : List of String
    """

    #---------------------------------------------------------------------------
    # Set configuration options
    #---------------------------------------------------------------------------
    configToUse = fsGetConfigToUse()
    if configToUse[KEY_RETURN_STATUS]:
        gitsummaryConfig = configToUse[KEY_RETURN_VALUE]
    else:
        for line in configToUse[KEY_RETURN_MESSAGES]:
            print(line)
        sys.exit()

    #---------------------------------------------------------------------------
    # Get all required output
    #---------------------------------------------------------------------------
    optionsAsSet = set(options[KEY_OPTIONS_SELECTED_OUTPUT])

    # Get a description of HEAD if we're in detached head state
    currentBranch = gitGetCurrentBranch()
    if currentBranch == '':
        currentBranch = gitGetCommitDescription('HEAD')

    localBranches = gitGetLocalBranches()

    if OPTIONS_OUTPUT_STASHES in options[KEY_OPTIONS_SELECTED_OUTPUT]:
        numStashes = len(gitGetStashes())

    # Getting file statuses is expensive, so only do it if output requiring
    # file statuses has been requested
    fileStatusesRequired = (
        len(optionsAsSet.intersection(
            [
                OPTIONS_OUTPUT_STAGE,
                OPTIONS_OUTPUT_WORK_DIR,
                OPTIONS_OUTPUT_UNMERGED,
                OPTIONS_OUTPUT_UNTRACKED,
            ]
        )) > 0
    )

    if fileStatusesRequired:
        fileStatuses = gitGetFileStatuses()

        numStage = len(fileStatuses[KEY_FILE_STATUSES_STAGE])
        numWorkDir = len(fileStatuses[KEY_FILE_STATUSES_WORK_DIR])
        numUnmerged = len(fileStatuses[KEY_FILE_STATUSES_UNMERGED])
        numUntracked = len(fileStatuses[KEY_FILE_STATUSES_UNTRACKED])

    # Remote tracking branch stats
    remoteRequired = (
        len(optionsAsSet.intersection(
            [
                 OPTIONS_OUTPUT_AHEAD_REMOTE,
                 OPTIONS_OUTPUT_BEHIND_REMOTE,
            ]
        )) > 0
    )

    if remoteRequired:
        remoteBranch = gitGetRemoteTrackingBranch(currentBranch)

        numAheadRemote = (
            '_' if remoteBranch == ''
            else len(gitGetCommitsInFirstNotSecond(currentBranch, remoteBranch, True))
        )

        numBehindRemote = (
            '_' if remoteBranch == ''
            else len(gitGetCommitsInFirstNotSecond(remoteBranch, currentBranch, True))
        )

    # Target tracking branch stats
    targetRequired = (
        len(optionsAsSet.intersection(
            [
                 OPTIONS_OUTPUT_AHEAD_TARGET,
                 OPTIONS_OUTPUT_BEHIND_TARGET,
            ]
        )) > 0
    )

    if targetRequired:
        targetBranch = utilGetTargetBranch(
            gitsummaryConfig,
            currentBranch,
            localBranches
        )

        numAheadTarget = (
            '_' if targetBranch == ''
            else len(gitGetCommitsInFirstNotSecond(currentBranch, targetBranch, True))
        )

        numBehindTarget = (
            '_' if targetBranch == ''
            else len(gitGetCommitsInFirstNotSecond(targetBranch, currentBranch, True))
        )

    #---------------------------------------------------------------------------
    # Assemble output in the requested order
    #---------------------------------------------------------------------------
    outputString = ''
    for output in options[KEY_OPTIONS_SELECTED_OUTPUT]:

        if output == OPTIONS_OUTPUT_STASHES:
            outputString = outputString + ' ' + str(numStashes)

        if output == OPTIONS_OUTPUT_STAGE:
            outputString = outputString + ' ' + str(numStage)

        if output == OPTIONS_OUTPUT_WORK_DIR:
            outputString = outputString + ' ' + str(numWorkDir)

        if output == OPTIONS_OUTPUT_UNMERGED:
            outputString = outputString + ' ' + str(numUnmerged)

        if output == OPTIONS_OUTPUT_UNTRACKED:
            outputString = outputString + ' ' + str(numUntracked)

        if output == OPTIONS_OUTPUT_AHEAD_REMOTE:
            outputString = outputString + ' ' + str(numAheadRemote)

        if output == OPTIONS_OUTPUT_BEHIND_REMOTE:
            outputString = outputString + ' ' + str(numBehindRemote)

        if output == OPTIONS_OUTPUT_AHEAD_TARGET:
            outputString = outputString + ' ' + str(numAheadTarget)

        if output == OPTIONS_OUTPUT_BEHIND_TARGET:
            outputString = outputString + ' ' + str(numBehindTarget)

        if output == OPTIONS_OUTPUT_BRANCH_NAME:
            outputString = outputString + ' ' + (
                currentBranch if currentBranch != '' else '_'
            )

        if output == OPTIONS_OUTPUT_TARGET_BRANCH:
            outputString = outputString + ' ' + (
                targetBranch if targetBranch != '' else '_'
            )

    print(outputString)

#-------------------------------------------------------------------------------
# Filesystem Interface Layer
#
# These functions form the interface with the filesystem, for operations other
# than running git.
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
def fsGetConfigFullyQualifiedFilename():
    """
    Return the fully qualified path to the closest CONFIG_FILENAME

    Algorithm is to look in current directory, then parent, repeating until
    the config file is found, stopping at filesystem root.

    Return
        String|None The fully qualified path to the config file, or None if it
                    doesn't exist
    """

    returnVal = None
    folderToExamine = os.getcwd()

    # splitdrive()[1] gives the current path
    #   - Unix filesystems   : current path, as expected
    #   - Windows filesystems: current path, excluding drive letters and UNC
    #     paths
    while (
        not returnVal and
        os.path.splitdrive(folderToExamine)[1] not in ['/', '\\']
    ):
        pathToTest = os.path.join(folderToExamine, CONFIG_FILENAME)
        if os.path.isfile(pathToTest):
            returnVal = pathToTest
        else:
            folderToExamine = os.path.dirname(folderToExamine)

    return returnVal

#-------------------------------------------------------------------------------
def fsGetConfigToUse():
    """
    Get the configuration object to use -- either user-specified or default

    If a user configuration file is found, it is parsed and validated.
    Validation errors are returned (see below).

    CONFIG_DEFAULT is used if no user config file is found.

    Return
        Dictionary - A dictionary containing the following keys:
            KEY_RETURN_STATUS   - Boolean     - Whether the configuration
                                                returned is valid
            KEY_RETURN_MESSAGES - List of str - Errors encountering when parsing
                                                user config file
            KEY_RETURN_VALUE    - Dictionary  - The configuration object,
                                                possibly empty if there were
                                                errors processing user's
                                                configuration file
    """
    errors = []
    configObjectToUse = {}

    userConfigFile = fsGetConfigFullyQualifiedFilename()
    if userConfigFile == None:
        configObjectToUse = CONFIG_DEFAULT
    else:
        configParseResult = fsGetValidatedUserConfig(userConfigFile)
        if configParseResult[KEY_RETURN_STATUS]:
            configObjectToUse = configParseResult[KEY_RETURN_VALUE]
        else:
            errors.append('There were problems with your configuration file.')
            errors.append('Configuration file: ' + userConfigFile)
            for error in configParseResult[KEY_RETURN_MESSAGES]:
                errors.append('    ' + error)

    returnVal = {
        KEY_RETURN_STATUS: len(errors) == 0,
        KEY_RETURN_MESSAGES: errors,
        KEY_RETURN_VALUE: configObjectToUse
    }

    return returnVal

#-------------------------------------------------------------------------------
def fsGetValidatedUserConfig(fullyQualifiedFilename):
    """
    Get the user specified gitsummary configuration

    Validate the contents and return errors if appropriate.

    Return
        Dictionary - A dictionary containing the following keys:
            KEY_RETURN_STATUS   - Boolean     - Whether the configuration
                                                returned is valid
            KEY_RETURN_MESSAGES - List of str - Errors encountering when parsing
                                                user config file
            KEY_RETURN_VALUE    - Dictionary  - The user-specified configuration
    """
    errors = []
    configObject = {}

    # Read the file, removing comments
    try:
        inputFile = open(fullyQualifiedFilename)
        configFileContents = ''

        for line in inputFile:
            # Strip out lines that contain only a comment
            if not re.search('^[ \t]*\/\/', line):
                configFileContents += line
        inputFile.close()

    except Exception as e:
        errors.append('Error reading ' + fullyQualifiedFilename + ': ' + str(e))

    # Parse the file as a json object
    if len(errors) == 0:
        try:
            configObject = json.loads(configFileContents)
            errors += utilValidateGitsummaryConfig(
                configObject
            )[KEY_RETURN_MESSAGES]
        except Exception as e:
            errors.append('Error parsing ' + fullyQualifiedFilename + ': ' + str(e))

    returnVal = {
        KEY_RETURN_STATUS: len(errors) == 0,
        KEY_RETURN_MESSAGES: errors,
        KEY_RETURN_VALUE: configObject
    }

    return returnVal

#-------------------------------------------------------------------------------
# Git Interface Layer
#
# These functions form the lower layer interface with git. They are the only
# functions with knowledge of the format of git commands.
#
# All of these functions use git plumbing commands, so should be immune to
# git changes.
#
# Limitations of gitGet* functions:
#   - They will fail with exceptions if the current working directory is not
#     tracked by git.
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
def gitGetCommitDescription(fullHash):
    """
    Get a description for the specified commit using 'git describe --always'.
    Thus output will be one of:
        - tagname if the commit corresponds to a tag
        - fancy description involving tagname and current hash if the commit
          doesn't correspond to a tag, but there's at least one tag
        - short hash if there are no tags in the repo

    Args
        String fullHash - the full hash of the commit in question.
                          'HEAD' (and probably other commitish things) will
                          also work.

    Return
        String - The output from 'git describe --always'
    """

    description = gitUtilGetOutput(['describe', '--always'])[0]

    return description

#-------------------------------------------------------------------------------
def gitGetCommitsInFirstNotSecond(branch1, branch2, topologicalOrder):
    """
    Get a list of commits that exist in branch1 but not branch2.

    The returned list will be appropriate even if one or both of branch1 and
    branch2 do not exist:
        branch1 doesn't exist - return = []
        branch2 doesn't exist - return = [ all commits in branch1 ]
        both don't exist      - return = []

    Args
        String  branch1          - The fully qualified name of the first branch
                                       Examples: "myBranch", "origin/myBranch"
        String  branch2          - The fully qualified name of the second branch
        Boolean topologicalOrder - Whether the commits should be:
                                    - topology order (True), or
                                    - reverse chronological (False)
                                 - This uses 'git rev-list --topo-order' when True

    Return
        List of Strings - Each element is the full hash of a commit that exists
                          in branch1 but not branch2
    """
    HEAD_REF_PREFIX = 'refs/heads/'
    REMOTE_REF_PREFIX = 'refs/remotes/'

    topoFlag = '--topo-order' if topologicalOrder else ''

    # We need to use this round-about for-each-ref approach since rev-list
    # (our ultimate goal) returns a non-zero exit code if either branch1 or
    # branch2 don't have any refs
    localBranchRefs = gitUtilGetOutput(
        ['for-each-ref', HEAD_REF_PREFIX, '--format=%(refname)']
    )

    remoteBranchRefs = gitUtilGetOutput(
        ['for-each-ref', REMOTE_REF_PREFIX, '--format=%(refname)']
    )

    branch1Exists = (
        (HEAD_REF_PREFIX + branch1) in localBranchRefs or
        (REMOTE_REF_PREFIX + branch1) in remoteBranchRefs
    )

    branch2Exists = (
        (HEAD_REF_PREFIX + branch2) in localBranchRefs or
        (REMOTE_REF_PREFIX + branch2) in remoteBranchRefs
    )

    if not branch1Exists:
        commitList = []
    elif not branch2Exists:
        commitList = gitUtilGetOutput(['rev-list', topoFlag, branch1])
    else:
        commitList = gitUtilGetOutput(['rev-list', topoFlag, branch1, '^' + branch2])
    # Expected output:
    # [full hash1]
    # [full hash2]
    # etc.

    return commitList

#-------------------------------------------------------------------------------
def gitGetCurrentBranch():
    """
    Get the name of the current branch.

    Return
        String - The name of the current branch
               - '' if HEAD does not correspond to a branch
                 (i.e. detached HEAD state)
    """
    output = gitUtilGetOutput(['status', '--branch', '--porcelain=2'])
    # Expected output: a bunch of lines starting with '#', where we only care
    # about:
    #   # branch.head BRANCH
    # BRANCH will be '(detached)' if detached head state
    parsedBranch = ''
    for line in output:
        match = re.search('^# branch.head (.+)$', line)
        if (match):
            parsedBranch = match.group(1)

    currentBranch = parsedBranch if parsedBranch != '(detached)' else ''

    return currentBranch

#-------------------------------------------------------------------------------
def gitGetFileStatuses():
    """
    Get file statuses for:
        - differences between the stage and HEAD
        - differences between the working directory and the stage
        - untracked files

    Return
        Dictionary with the following contents:
            KEY_FILE_STATUSES_STAGE:     []   - differences between the stage and
                                                HEAD
            KEY_FILE_STATUSES_UNKNOWN:   []   - unknown git output
            KEY_FILE_STATUSES_UNMERGED:  []   - unmerged changes
            KEY_FILE_STATUSES_UNTRACKED: []   - non-git tracked files
            KEY_FILE_STATUSES_WORK_DIR:  []   - differences between the working
                                                directory and the stage

        The elements of each list have the following formats (all keys prepended
        with 'KEY_FILE_STATUSES_', but ommitted here for brevity)

        STAGE: Dictionary of the form:
            TYPE           : String - The single letter code from 'git status --short'
            FILENAME       : String - The name of the file that's different
            NEW_FILENAME   : String - The new filename if the TYPE was one of
                                      'C' or 'R'
            HEURISTIC_SCORE: String - The value (0-100) that git assigns when
                                      deciding if the file was renamed/copied

        WORK_DIR: Dictionary of the form:
            TYPE           : String - The single letter code from 'git status --short'
            FILENAME       : String - The name of the file that's different

        UNKNOWN: String - The raw git output that couldn't be parsed

        UNMERGED: Dictionary of the form:
            TYPE           : String - The single letter code from 'git status --short'
            FILENAME       : String - The name of the file that's unmerged

        UNTRACKED: String - The name of the file that's untracked

    """

    fileStatuses = {
        KEY_FILE_STATUSES_STAGE: [],
        KEY_FILE_STATUSES_UNKNOWN: [],
        KEY_FILE_STATUSES_UNMERGED: [],
        KEY_FILE_STATUSES_UNTRACKED: [],
        KEY_FILE_STATUSES_WORK_DIR: [],
    }

    output = gitUtilGetOutput(['status', '--porcelain=2'])

    #---------------------------------------------------------------------------
    # Each line of output describes one file.
    # That description specifies how the file differs between:
    #   - the index (stage) and HEAD (X)
    #   - the working directory and the stage (Y)
    #
    # Each line of output will match one of the following patterns:
    #   1 <XY> <sub> <mH> <mI> <mW> <hH> <hI> <path>
    #   2 <XY> <sub> <mH> <mI> <mW> <hH> <hI> <X><score> <path>[tab]<origPath>
    #   u <XY> <sub> <m1> <m2> <m3> <mW> <h1> <h2> <h3> <path>
    #   ? <path>
    #
    # These correspond to, respectively:
    #   - a changed file
    #   - a renamed or copied file
    #   - an unmerged file
    #   - an untracked file
    #
    # See the manpage for 'git status --porcelain=2' for full details
    #     Note: It says it can indicate when a file is copied, however this
    #           thread says that's false:
    #               https://marc.info/?l=git&m=141730775928542&w=2
    #---------------------------------------------------------------------------

    for outputLine in output:
        lineType = outputLine[0]

        if lineType in ['1', '2', 'u']:
            stageCode = outputLine[2]
            workDirCode = outputLine[3]
        else:
            stageCode = ''
            workDirCode = ''

        #-----------------------------------------------------------------------
        # Changed file
        # 1 <XY> <sub> <mH> <mI> <mW> <hH> <hI> <path>
        #-----------------------------------------------------------------------
        if lineType == '1':
            match = re.search('^([^ ]+ ){8}(.+)$', outputLine)
            filename = match.group(2)

            if stageCode != '.':
                fileStatuses[KEY_FILE_STATUSES_STAGE].append(
                    {
                        KEY_FILE_STATUSES_TYPE: stageCode,
                        KEY_FILE_STATUSES_FILENAME: filename,
                    }
                )

            if workDirCode != '.':
                fileStatuses[KEY_FILE_STATUSES_WORK_DIR].append(
                    {
                        KEY_FILE_STATUSES_TYPE: workDirCode,
                        KEY_FILE_STATUSES_FILENAME: filename,
                    }
                )

        #-----------------------------------------------------------------------
        # Renamed or copied file
        # 2 <XY> <sub> <mH> <mI> <mW> <hH> <hI> <X><score> <path>[tab]<origPath>
        #-----------------------------------------------------------------------
        elif lineType == '2':
            match = re.search('^([^ ]+ ){8}[A-Z]([^ ]+) (.+)\t(.+)$', outputLine)

            heuristicScore = match.group(2)
            newFilename = match.group(3)
            filename = match.group(4)

            if stageCode != '.':
                fileStatuses[KEY_FILE_STATUSES_STAGE].append(
                    {
                        KEY_FILE_STATUSES_TYPE: stageCode,
                        KEY_FILE_STATUSES_FILENAME: filename,
                        KEY_FILE_STATUSES_NEW_FILENAME: newFilename,
                        KEY_FILE_STATUSES_HEURISTIC_SCORE: heuristicScore,
                    }
                )

            # Only the stage tracks whether a file has been renamed or copied
            # (and the corresponding heuristic score).
            # Since the working directory status is relative to the stage, the
            # modified filename must be the renamed/copied one
            if workDirCode != '.':
                fileStatuses[KEY_FILE_STATUSES_WORK_DIR].append(
                    {
                        KEY_FILE_STATUSES_TYPE: workDirCode,
                        KEY_FILE_STATUSES_FILENAME: newFilename,
                    }
                )

        #-----------------------------------------------------------------------
        # Unmerged file
        #   u <XY> <sub> <m1> <m2> <m3> <mW> <h1> <h2> <h3> <path>
        #-----------------------------------------------------------------------
        elif lineType == 'u':
            match = re.search('^([^ ]+ ){10}(.+)$', outputLine)
            filename = match.group(2)

            fileStatuses[KEY_FILE_STATUSES_UNMERGED].append(
                {
                    KEY_FILE_STATUSES_TYPE: stageCode,
                    KEY_FILE_STATUSES_FILENAME: filename,
                }
            )

        #-----------------------------------------------------------------------
        # Untracked file
        # ? <path>
        #-----------------------------------------------------------------------
        elif lineType == '?':
            filename = outputLine[2:]
            fileStatuses[KEY_FILE_STATUSES_UNTRACKED].append(filename)

        #-----------------------------------------------------------------------
        # Unknown git output
        #-----------------------------------------------------------------------
        else:
            fileStatuses[KEY_FILE_STATUSES_UNKNOWN].append(outputLine)

    return fileStatuses

#-------------------------------------------------------------------------------
def gitGetLocalBranches():
    """
    Get a list of local branch names.

    Return
        List of String - The list of branch names
    """

    branchRefs = gitUtilGetOutput(
        ['for-each-ref', 'refs/heads', '--format=%(refname)']
    )
    # Expected output:
    # refs/head/BRANCHNAME1
    # refs/head/BRANCHNAME2
    # <etc>

    if len(branchRefs) == 0:
        # This corresponds to the state immediately after 'git init', in which
        # case the list of branches is just the current branch
        return [ gitGetCurrentBranch() ]

    localBranches = []
    for ref in branchRefs:
        localBranches.append(ref.replace('refs/heads/', ''))

    return localBranches

#-------------------------------------------------------------------------------
def gitGetRemoteTrackingBranch(localBranch):
    """
    Get the fully qualified name of the specified branch's remote tracking
    branch.

    Args
        String localBranch - Name of the local branch.
                             '' is ok, which will result in '' being returned

    Return
        String - The fully qualified name of the corresponding remote tracking
                 branch
               - '' if localBranch is ''
               - '' if localBranch has no remote tracking branch
    """
    remoteTrackingBranch = ''

    #---------------------------------------------------------------------------
    # If there are any refs:
    #   - 'git for-each-ref' will tell us the remote branch
    #   - So just scan that output for 'localBranch'
    #
    # If there are no refs:
    #   - There's only one branch
    #   - If 'localBranch' is not the current branch, the remote is '' by definition
    #   - If 'localBranch' is the current branch, 'git status' will tell us
    #     the remote

    # Use a tab to separate fields (like git status) so branch names can have
    # spaces
    refsOutput = gitUtilGetOutput(
        [
            'for-each-ref',
            '--format=%(refname:short)\t%(upstream:short)',
        ]
    )
    # Expected output:
    # [branchname] [fully qualified remote branch name]
    # [Repeat for all local branches]

    if len(refsOutput) > 0:
        # There are refs, so find 'localBranch' in the output
        for line in refsOutput:
            split = line.split('\t')
            if localBranch == split[0]:
                remoteTrackingBranch = split[1]
    else:
        # No refs, so there's only one branch
        statusOutput = gitUtilGetOutput(['status', '--branch', '--porcelain=2'])
        # Expected output: a bunch of lines starting with '#', where we only care
        # about:
        #   # branch.head BRANCH
        #   # branch.upstream REMOTE/BRANCH

        # First pull out the info we're interested in
        branchValue = None
        remoteValue = None

        for line in statusOutput:
            branchMatch = re.search('^# branch.head (.+)$', line)
            if (branchMatch):
                branchValue = branchMatch.group(1)
            else:
                remoteMatch = re.search('^# branch.upstream (.+)$', line)
                if (remoteMatch):
                    remoteValue = remoteMatch.group(1)

        if localBranch == branchValue and remoteValue != None:
            remoteTrackingBranch = remoteValue

    return remoteTrackingBranch

#-------------------------------------------------------------------------------
def gitGetStashes():
    """
    Get the list of stashes in the current repository.

    Return
        List of Dictionaries - Each element has the following keys:
            KEY_STASH_FULL_HASH  : String - The full hash of this stash
            KEY_STASH_NAME       : String - The name of the stash (i.e. stash@{n})
            KEY_STASH_DESCRIPTION: String - The descriptive text
    """
    # We want to use 'git reflog refs/stash', but it exits with status 1 if
    # there are no stashes.
    #
    # We can get around that by listing all refs and searching for 'refs/stash'
    # so we know if any stashes exist, and thus whether it's safe to use
    # 'git reflog refs/stash'
    refs = gitUtilGetOutput(['for-each-ref', '--format=%(refname)'])

    if not 'refs/stash' in refs:
        # No stash ref exists, so there can't be any stashes.
        return []

    # refs/stash exists, so we can now do what we wanted to do in the first
    # place -- list the stashes
    stashes = []

    output = gitUtilGetOutput(['reflog', '--no-abbrev-commit', 'refs/stash'])
    # Expected output:
    # [full hash] refs/stash@{0}: [description]
    # [full hash] refs/stash@{1}: [description]
    # etc.

    for oneStash in output:
        split = oneStash.split(' ', 2)
        nameMatch = re.search('^refs/([^:]+})', split[1])
        name = nameMatch.group(1)
        stashes.append(
            {
                KEY_STASH_FULL_HASH  : split[0],
                KEY_STASH_NAME       : name,
                KEY_STASH_DESCRIPTION: split[2],
            }
        )

    return stashes

#-------------------------------------------------------------------------------
# Git Utility Layer
#
# Pretty boring layer -- just one function. Maybe there will be more in the
# future.
#
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
def gitUtilGetOutput(command):
    """
    Get the output from running the specified git command.

    If there's an error, print the command and its output, then call sys.exit(1).

    Args
        List command - The git command to run, *excluding* the 'git' part
                       (so this function can add optional args like
                       --no-optional-locks)

    Return
        List of String - Each element is one line of output from the executed
                         command
    """
    global GLOBAL_GIT_NO_OPTIONAL_LOCKS

    optionalLocksArg = ['--no-optional-locks' ] if GLOBAL_GIT_NO_OPTIONAL_LOCKS else []

    fullCommand = ['git'] + optionalLocksArg + command

    try:
        output = subprocess.check_output(
            fullCommand,
            stderr = subprocess.STDOUT,
            universal_newlines = True
        )

    except subprocess.CalledProcessError as e:
        print('Failure: ' + str(e.cmd))
        print(e.output)
        sys.exit(1)
    else:
        returnVal = output.splitlines()

    return returnVal

#-------------------------------------------------------------------------------
# Utility Layer
#
# These are utility functions that build various objects required to create
# appropriate output. They don't run git directly, but may use functions from
# the git layer.
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
def utilGetAheadBehindString(ahead, behind):
    """
    Get a string of the form '+ahead -behind' that is used to indicate number
    of commits a branch is ahead/behind another.

    Args
        Number | '' ahead  - The number of commits ahead
        Number | '' behind - The number of commits behind

    Return
        String - The formatted string
                 Special formatting:
                    - Leave '' unchanged
                    - Use '.' instead of '+-0'
                    - Max width for each is 4 ([+-]xxx)
                    - If either ahead or behind is greater than 999, show
                      '>999', without the +-
    """
    if ahead == '':
        aheadString = ''
    elif ahead == 0:
        aheadString = '.'
    elif ahead > 999:
        aheadString = '>999'
    else:
        aheadString = '+' + str(ahead)

    if behind == '':
        behindString = ''
    elif behind == 0:
        behindString = '.'
    elif behind > 999:
        behindString = '>999'
    else:
        behindString = '-' + str(behind)

    formattedString = aheadString.rjust(4) + '  ' + behindString.ljust(4)

    return formattedString

#-------------------------------------------------------------------------------
def utilGetBranchAsFiveColumns(currentBranch, branch, targetBranch):
    """
    Get the specified branch formatted as five columns

    Args
        String currentBranch - The name of the current checked out branch
                               (So we can flag it if it's 'branch')
        String branch        - The name of the branch to be formatted
        String targetBranch  - The name of the target branch
                               '' if there is no target branch

    Return
        List of String - First element : CURRENT_BRANCH_INDICATOR if branch is
                                         the current branch (otherwise '')
                       - Second element: branch name
                       - Third element : commits ahead/behind remote branch
                       - Fourth element: commits ahead/behind target branch
                       - Fifth element : name of target branch
    """
    remoteBranch = gitGetRemoteTrackingBranch(branch)

    currentBranchIndicator = CURRENT_BRANCH_INDICATOR if branch == currentBranch else ''
    aheadOfRemote = (
        '' if remoteBranch == ''
        else len(gitGetCommitsInFirstNotSecond(branch, remoteBranch, True))
    )

    behindRemote = (
        '' if remoteBranch == ''
        else len(gitGetCommitsInFirstNotSecond(remoteBranch, branch, True))
    )

    aheadOfTarget = (
        '' if targetBranch == ''
        else len(gitGetCommitsInFirstNotSecond(branch, targetBranch, True))
    )

    behindTarget = (
        '' if targetBranch == ''
        else len(gitGetCommitsInFirstNotSecond(targetBranch, branch, True))
    )

    return [
        currentBranchIndicator,
        branch,
        utilGetAheadBehindString(aheadOfRemote, behindRemote),
        utilGetAheadBehindString(aheadOfTarget, behindTarget),
        targetBranch,
    ]

#-------------------------------------------------------------------------------
def utilGetBranchOrder(gitsummaryConfig, branchList):
    """
    Return the branches in branchList in the order specified by the
    gitsummaryConfig.

    - The order of patterns in gitsummaryConfig is the order that matching
      branches will be returned
    - For branches that match one particular pattern in gitsummaryConfig, they
      will be returned in alphabetical order.
    - Branches that don't match any patterns in gitsummaryConfig will be listed
      last (in alphabetical order as well).

    Args
        Dictionary     gitsummaryConfig - Dictionary containing all the
                                          gitsummary configuration
        List of String branchList       - The list of branches to be put in
                                          order

    Return
        List of String - The branches in order as per gitsummaryConfig

    """
    originalBranchList = sorted(branchList)
    returnVal = []

    # First the branches that match gitsummaryConfig patterns
    for branchPattern in gitsummaryConfig[KEY_CONFIG_BRANCH_ORDER]:
        for branch in [x for x in originalBranchList if x not in returnVal]:
            if re.search(branchPattern, branch):
                returnVal.append(branch)

    # Then the branches that don't match any config patterns
    returnVal += [x for x in originalBranchList if x not in returnVal]

    return returnVal

#-------------------------------------------------------------------------------
def utilGetColumnAlignedLines(
    maxWidth,
    truncIndicator,
    variableColumn,
    columnWidths,
    lines
):
    """
    Get an array of lines (broken into columns) where columns are aligned and the
    entire line is at most 'maxWidth' characters. Column alignment is achived
    by padding or truncation as required.

    To achieve column alignment:
        - each column other than 'variableColumn' will be the widest width of
          that column among all lines
        - the width of 'variableColumn' will be either the widest width among
          all lines, or truncated to ensure no lines are longer than maxWidth

    This function can be called with an empty List of lines, in which case an
    empty List will be returned.

    Args
        Number maxWidth       - The maximum line length
                                -1 indicates no max length
        String truncIndicator - A string with which to replace the last
                                len(truncIndicator) characters of a column if it
                                needs to be truncated.
                                Replacement of characters happens after the
                                truncation.
        Number variableColumn - The index (0-based) of the variable width column
        List   columnWidths   - List of widths (Number) required for each column.
                                The value corresponding to the variable width
                                column will be ignored
        List   lines          - List of lines, where each element is itself a
                                list of Strings (the columns).
                                Example:
                                [
                                    ['line1-col1', 'line1-col2', 'line1-col3'],
                                    ['line2-col1', 'line2-col2', 'line2-col3'],
                                ]

    Return
        List - A list of "lines", where each element is itself a list of Strings
               (the padded/truncated columns). Example:
                    [
                        ['line1-col1       ', 'line1-col2    ', 'line1-col3-b'],
                        ['line2-col1-bla'   , 'line2-col2-bla', 'line2-col3-b'],
                    ]
    """
    if len(lines) == 0:
        return []

    alignedLines = []

    # Determine how much (if any) must be truncated
    if maxWidth == -1:
        truncation = 0
    else:
        totalWidth = sum(columnWidths) + len(columnWidths) - 1
        truncation = totalWidth - maxWidth if totalWidth > maxWidth else 0

    # Determine required width of variable width column
    variableColumnWidth = columnWidths[variableColumn] - truncation

    # Gracefully handle tiny screen width
    if variableColumnWidth < 0:
        variableColumnWidth = 1

    for line in lines:
        columns = []

        for i, column in enumerate(line):
            if i != variableColumn:
                # This is a column to be padded out so all lines align
                formatString = '{0:<' + str(columnWidths[i]) + '}'
                formattedColumn = formatString.format(column)
            else:
                # This is a column that needs to be padded or truncated to
                # ensure max line width is 'requiredWidth'
                formatString = (
                    '{0:<' +
                    str(variableColumnWidth) +
                    '.' +
                    str(variableColumnWidth) +
                    '}'
                )
                formattedColumn = formatString.format(column)

                # If we truncated this column, replace the last n characters
                # with the requested truncation indicator
                if len(column) > variableColumnWidth and truncIndicator != '':
                    formattedColumn = (
                        formattedColumn[0:-len(truncIndicator)] + truncIndicator
                    )

            columns.append(formattedColumn)
        alignedLines.append(columns)

    return alignedLines

#-------------------------------------------------------------------------------
def utilGetMaxColumnWidths(lines):
    """
    Get the maximum width of each line of the specified lines.

    This function can be called with an empty List of lines, in which case an
    empty List will be returned.

    Args
        List lines - List of "lines", where each element is itself a list of
                     Strings (the columns in the line)
                     Example:
                        [
                            ['col1', 'col2', 'col3'],
                            ['ab1' , 'ab2' , 'ab3' ],
                            ['a1'  , 'a2'  , 'a3' ],
                        ]

    Return
        List - A list of the maximum width of each column among the specified
               input lines.
    """
    if len(lines) == 0:
        return []

    numColumns = len(lines[0])
    maxColumnWidths = []

    for columnIndex in range(numColumns):
        maxColumnWidth = 0
        for line in lines:
            maxColumnWidth = max(maxColumnWidth, len(line[columnIndex]))
        maxColumnWidths.append(maxColumnWidth)

    return maxColumnWidths

#-------------------------------------------------------------------------------
def utilGetRawBranchesLines(
    gitsummaryConfig,
    currentBranch,
    localBranches,
    showAllBranches
):
    """
    Get the "raw" lines for the specified branches, including the headings line.

    Args
        Dictionary     gitsummaryConfig - Dictionary containing all the
                                          gitsummary configuration
        String         currentBranch    - The name of the current branch.
                                          Used to determine which branch line
                                          should have the CURRENT_BRANCH_INDICATOR
        List of String localBranches    - All local branches, in the order they
                                          should appear in the returned list
        Boolean        showAllBranches  - Whether to show all branches (True)
                                          or just the current branch (False)

    Return
        List of 'lines', where each line is itself a List of columns

        Each line has 5 columns:
            current-branch indicator,
            name,
            remote +/-,
            target +/-,
            target name

        Example:
            [
              [ '' , ''       , '  Remote', '  Target', ''],
              [ '>', 'dev'    , '+1  -2'  , '+3  -4'  , 'master' ],
              [ '' , 'branch1', '+1  -2'  , '+3  -4'  , 'dev' ],
            ]
    """
    # Title line
    # Leading spaces so they're centered
    rawBranchLines = [
        ['', '', '  Remote', '  Target', ''],
    ]

    if showAllBranches:
        branchesToList = localBranches
    else:
        # Make sure we're not showing a branch line for detached head state,
        # since we've got logic for that below
        if currentBranch != '':
            branchesToList = [currentBranch]
        else:
            branchesToList = []

    for branch in branchesToList:
        targetBranch = utilGetTargetBranch(
            gitsummaryConfig,
            branch,
            localBranches
        )

        rawBranchLines.append(
            utilGetBranchAsFiveColumns(
                currentBranch,
                branch,
                targetBranch
            )
        )

    # If we're in detached head state, add a branch line using the output of
    # 'git describe --always' as the branch name.
    # in detached head state
    if currentBranch == '':
        description = gitGetCommitDescription('HEAD')
        rawBranchLines.append(
            utilGetBranchAsFiveColumns(
                description,
                description,
                ''
            )
        )

    return rawBranchLines

#-------------------------------------------------------------------------------
def utilGetRawStageLines(fileStatuses):
    """
    Get the "raw" lines for all staged files.

    Args
        Dictionary with the following key (among others):
            KEY_FILE_STATUSES_STAGE: List of Dictionaries as returned by
                                     gitGetFileStatuses()

        Note: We pass the full fileStatuses object rather than just the List we
              need since that would required testing doit(), which is only
              testable manually.

    Return
        List of 'lines', where each line is itself a List of columns

        Each line has 3 columns:
            'Stage' title (first line only),
            changeType,
            filename

        Example:
            [
                [ 'Stage', 'M'     , 'file1' ],
                [ ''     , 'A'     , 'file2' ],
                [ ''     , 'R(100)', 'file3 -> newFile3' ],
            ]
    """
    rawStagedLines = []

    rawStagedList = fileStatuses[KEY_FILE_STATUSES_STAGE]

    for i, stagedFile in enumerate(rawStagedList):
        rawStagedLines.append(
            ['Stage' if i == 0 else ''] +
            utilGetStagedFileAsTwoColumns(stagedFile)
        )

    return rawStagedLines

#-------------------------------------------------------------------------------
def utilGetRawStashLines():
    """
    Get the "raw" lines for all stashes.

    Return
        List of 'lines', where each line is itself a List of columns

        Each line has 3 columns:
            'Stashes' title (first line only),
            name,
            description

        Example:
            [
                [ 'Stashes', 'stash@{0}', 'WIP on branch xyz' ],
                [ ''       , 'stash@{1}', 'WIP on branch abc' ],
            ]
    """
    rawStashLines = []

    rawStashList = gitGetStashes()

    for i, oneStash in enumerate(rawStashList):
        rawStashLines.append(
            ['Stashes' if i == 0 else ''] +
            utilGetStashAsTwoColumns(oneStash)
        )

    return rawStashLines

#-------------------------------------------------------------------------------
def utilGetRawUnmergedLines(fileStatuses):
    """
    Get the "raw" lines for all unmerged files.

    Args
        Dictionary with the following key (among others)
            KEY_FILE_STATUSES_UNMERGED: List of Dictionaries as returned by
                                        gitGetFileStatuses()

        Note: We pass the full fileStatuses object rather than just the List we
              need since that would required testing doit(), which is only
              testable manually.

    Return
        List of 'lines', where each line is itself a List of columns

        Each line has 3 columns:
            'Unmerged' title (first line only),
            changeType,
            filename

        Example:
            [
              [ 'Unmerged', 'A', 'file1' ],
              [ '',         'M', 'file2' ],
            ]
    """

    rawUnmergedLines = []

    rawUnmergedList = fileStatuses[KEY_FILE_STATUSES_UNMERGED]

    for i, unmergedFile in enumerate(rawUnmergedList):
        rawUnmergedLines.append(
            ['Unmerged' if i == 0 else ''] +
            utilGetUnmergedFileAsTwoColumns(unmergedFile)
        )

    return rawUnmergedLines

#-------------------------------------------------------------------------------
def utilGetRawUntrackedLines(fileStatuses):
    """
    Get the "raw" lines for all untracked files.

    Args
        Dictionary with the following key (among others):
            KEY_FILE_STATUSES_UNTRACKED: List of Dictionaries as returned by
                                         gitGetFileStatuses()

        Note: We pass the full fileStatuses object rather than just the List we
              need since that would required testing doit(), which is only
              testable manually.

    Return
        List of 'lines', where each line is itself a List of columns

        Each line has 2 columns:
            'Untracked' title (first line only),
            filename

        Example:
            [
              [ 'Untracked', 'file1' ],
              [ ''         , 'file2' ],
            ]
    """
    rawUntrackedLines = []

    rawUntrackedList = fileStatuses[KEY_FILE_STATUSES_UNTRACKED]

    for i, untrackedFile in enumerate(rawUntrackedList):
        rawUntrackedLines.append(
            [
                'Untracked' if i == 0 else '',
                untrackedFile,
            ]
        )

    return rawUntrackedLines

#-------------------------------------------------------------------------------
def utilGetRawWorkDirLines(fileStatuses):
    """
    Get the "raw" lines for all workdir files.

    Args
        Dictionary with the following key (among others)
            KEY_FILE_STATUSES_WORK_DIR: List of Dictionaries as returned by
                                        gitGetFileStatuses()

        Note: We pass the full fileStatuses object rather than just the List we
              need since that would required testing doit(), which is only
              testable manually.

    Return
        List of 'lines', where each line is itself a List of columns

        Each line has 3 columns:
            'Work Dir' title (first line only),
            changeType,
            filename

        Example:
            [
              [ 'Work Dir', 'M', 'file1' ],
              [ '',         'D', 'file2' ],
            ]
    """

    rawWorkDirLines = []

    rawWorkDirList = fileStatuses[KEY_FILE_STATUSES_WORK_DIR]

    for i, workDirFile in enumerate(rawWorkDirList):
        rawWorkDirLines.append(
            ['Work Dir' if i == 0 else ''] +
            utilGetWorkDirFileAsTwoColumns(workDirFile)
        )

    return rawWorkDirLines

#-------------------------------------------------------------------------------
def utilGetStagedFileAsTwoColumns(stagedFile):
    """
    Get the specified stagedFile formatted as two columns

    Args
        Dictionary stagedFile - One stagedFile as returned by gitGetFileStatuses

    Return
        List of String - First element:  Change type (with heuristic score if
                                         appropriate)
                                         Examples: 'A', 'D', 'M', 'R100', 'R80'
                       - Second element: Filename (including new filename if
                                         change was a rename or copy)
    """
    changeType = stagedFile[KEY_FILE_STATUSES_TYPE]
    filename = stagedFile[KEY_FILE_STATUSES_FILENAME]
    newFilename = (
        '' if KEY_FILE_STATUSES_NEW_FILENAME not in stagedFile
        else stagedFile[KEY_FILE_STATUSES_NEW_FILENAME]
    )
    score = (
        '' if KEY_FILE_STATUSES_HEURISTIC_SCORE not in stagedFile
        else stagedFile[KEY_FILE_STATUSES_HEURISTIC_SCORE]
    )

    changeDetails = changeType + ('' if score == '' else '(' + score + ')')
    fileDetails = filename + ('' if newFilename == '' else (' -> ' + newFilename))

    return [
        changeDetails,
        fileDetails,
    ]

#-------------------------------------------------------------------------------
def utilGetStashAsTwoColumns(stash):
    """
    Get the specified stash formatted as two columns

    Args
        Dictionary stash - One stash as returned by gitGetStashes()

    Return
        List of String - First element : Stash name
                       - Second element: Stash description
    """
    return [
        stash[KEY_STASH_NAME],
        stash[KEY_STASH_DESCRIPTION],
    ]

#-------------------------------------------------------------------------------
def utilGetStyledText(styles, text):
    """
    Return the specified text in the specified style. As a convenience, 'text'
    is returned with no change if 'styles' is an empty list.

    Args
        List   styles - List of global TEXT_* constants corresponding to
                        styles that should be applied
        String text   - The text to format

    Return
        String The specified text wrapped in ANSI formatting escape characters.
               The original text is returned unchanged if 'styles' is empty
    """

    ESCAPE_MAPPING = {
        TEXT_BRIGHT: '1',
        TEXT_NORMAL: '0',

        TEXT_BLACK: '30',
        TEXT_BLUE: '34',
        TEXT_CYAN: '36',
        TEXT_GREEN: '32',
        TEXT_MAGENTA: '35',
        TEXT_RED: '31',
        TEXT_YELLOW: '33',
        TEXT_WHITE: '37'
    }

    if len(styles) == 0:
        return text

    styleList = ''
    for i, style in enumerate(styles):
        styleList += ('' if i == 0 else ';') + ESCAPE_MAPPING[style]

    escapeStart = '\033[' + styleList + 'm'
    escapeEnd = '\033[' + ESCAPE_MAPPING[TEXT_NORMAL] + 'm'

    return escapeStart + text + escapeEnd

#-------------------------------------------------------------------------------
def utilGetTargetBranch(gitsummaryConfig, branch, localBranches):
    """
    Return the name of the target branch associated with 'branch', as specified
    in 'gitsummaryConfig' (if that target branch exists).

    Args
        Dictionary     gitsummaryConfig - Dictionary containing all the
                                          gitsummary configuration
        String         branch           - The name of the branch we're interested
                                          in
        List of String localBranches    - List of all local branches

    Return
        String - The target branch. '' if no target branch
    """
    defaultTarget = gitsummaryConfig[KEY_CONFIG_DEFAULT_TARGET]
    targetBranch = None

    # See if current branch matches one in the config file
    for branchConfig in gitsummaryConfig[KEY_CONFIG_BRANCHES]:
        if re.search(branchConfig[KEY_CONFIG_BRANCH_NAME], branch):
           thisTarget = branchConfig[KEY_CONFIG_BRANCH_TARGET]
           targetBranch = thisTarget if thisTarget in localBranches else ''
           break

    # If we didn't match a branch from the user config, then use the default
    if targetBranch == None:
        targetBranch = defaultTarget if defaultTarget in localBranches else ''

    return targetBranch

#-------------------------------------------------------------------------------
def utilGetUnmergedFileAsTwoColumns(unmergedFile):
    """
    Get the specified unmergedFile formatted as two columns

    Args
        Dictionary unmergedFile - One unmergedFile as returned by
                                  gitGetFileStatuses

    Return
        List of String - First element:  Change type
                                         Examples: 'A', 'M'
                       - Second element: Filename
    """
    return [
        unmergedFile[KEY_FILE_STATUSES_TYPE],
        unmergedFile[KEY_FILE_STATUSES_FILENAME],
    ]

#-------------------------------------------------------------------------------
def utilGetWorkDirFileAsTwoColumns(workDirFile):
    """
    Get the specified workDirFile formatted as two columns

    Args
        Dictionary workDirFile  - One workDirFile as returned by
                                  gitGetFileStatuses

    Return
        List of String - First element:  Change type
                                         Examples: 'D', 'M'
                       - Second element: Filename
    """
    return [
        workDirFile[KEY_FILE_STATUSES_TYPE],
        workDirFile[KEY_FILE_STATUSES_FILENAME],
    ]

#-------------------------------------------------------------------------------
def utilNoopGetStyledText(styles, text):
    """
    Return the specified text unmodified. This is used as a replacement for
    utilGetStyledText() when no escape codes should be generated

    Args

        List   styles - Ignored
        String text   - The text to be returned

    Return
        String The unmodified text
    """
    return text

#-------------------------------------------------------------------------------
def utilPrintHelp(commandName):
    """
    Print the output corresponding to '--help'.

    Args
        String commandName - The name this script was invoked with
    """
    print('Usage:')
    print('    ' + commandName + ' [OPTIONS]')
    print('    ' + commandName + ' [shell-prompt-helper] [OPTIONS]')
    print()
    print('In the first form, print a summary of the current git repository\'s status:')
    print('    - stashes, staged changes, working directory changes, unmerged changes,')
    print('      untracked files,')
    print('    - list of local branches, including the following for each:')
    print('          - number of commits ahead/behind its target branch')
    print('          - number of commits ahead/behind its remote branch')
    print('          - the name of its target branch')
    print()
    print('In the second form, print a single line of space-separated values that can be')
    print('easily parsed to provide a fancy shell prompt:')
    print('    - number of:')
    print('          stashes, staged changes, working directory changes, unmerged changes,')
    print('          untracked files,')
    print('          commits ahead of remote branch, commits behind remote branch,')
    print('          commits ahead of target branch, commits behind target branch')
    print('    - current branch name, target branch name')
    print()
    print('Also in the second form, values that have no meaning will be replaced with "_":')
    print('    - number of commits ahead/behind remote if there is no remote branch')
    print('    - number of commits ahead/behind target if there is no target branch')
    print()
    print('Options:')
    print('    --custom SECTIONS')
    print('        - Show only the specified SECTIONS of output, in the order specified')
    print('        - Valid section names for the first form above are:')
    print('              stashes, stage, workdir, unmerged, untracked,')
    print('              branch-all, branch-current')
    print('        - Valid section names for the second form above are:')
    print('              stashes, stage, workdir, unmerged, untracked,')
    print('              ahead-remote, behind-remote, ahead-target, behind-target,')
    print('              branch-name, target-branch')
    print('')
    print('    --color')
    print('        - Force the use of colored output even if stdout is not a tty')
    print('')
    print('    --no-color')
    print('        - Do not show colored output')
    print('')
    print('    --no-optional-locks')
    print('        - Use git\'s --no-optional-locks option. Useful if you want to run')
    print('          gitsummary in the background or a loop')
    print('')
    print('    --max-width N')
    print('        - Format output for a maximum width of N columns, regardless of')
    print('          current terminal width')
    print('')
    print('    --help')
    print('        - Show this output')
    print('')
    print('    --helpconfig')
    print('        - Show information for the gitsummary configuration file')
    print('')
    print('    --version')
    print('        - Show current version')

#-------------------------------------------------------------------------------
def utilPrintHelpConfig():
    """
    Print help output describing the configuration file
    """

    print("""The gitsummary configuration file ("{configFilename}") is a json-formatted
file used to specify:
    - the order in which branches are printed
    - branch names and their corresponding targets

Any line beginning with "//" (with optional preceding whitespace) is treated as
a comment and thus ignored.

The following is a sample configuration file that matches the built-in defaults:

   {{
       // Specify the order in which to display branches
       //     - Branches that match the first regular expression are displayed
       //       first (in alphabetical order), followed by branches matching
       //       the second regular expression, and so on
       //     - Branches not matching any of the regular expressions are
       //       listed last (also in alphabetical order)
       "branchOrder": [
           "^master$",
           "^develop$",
           "^hotfix-",
           "^release-"
       ],

       // Specify the default target branch if none of the regular expressions
       // in "branches" (see below) match. "" is a valid value.
       "defaultTarget": "develop",

       // Specify branches and their corresponding target branches
       //     - When displaying branch information, the branch name is
       //       matched against the "name" regular expressions below, in
       //       successive order, until a match is made
       //     - The "target" of the first match will be shown as the branch's
       //       target branch
       "branches": [
           {{
               "name"  : "^master$",
               "target": ""
           }},
           {{
               "name"  :"^develop$",
               "target": "master"
           }},
           {{
               "name"  :"^hotfix-.*",
               "target": "master"
           }},
           {{
               "name"  :"^release-.*",
               "target": "master"
           }}
       ]
    }}

Gitsummary will look for {configFilename} in the current directory. If
not found, it will look in successive parent folders all the way up to the root
of the filesystem.

    """.format(
        configFilename = CONFIG_FILENAME,
    ))

#-------------------------------------------------------------------------------
def utilValidateGitsummaryConfig(configObject):
    """
    Validate the specified configObject

    Test that all required keys are present and the correct type, and there are
    no unexpected keys.

    Return
        Dictionary - With the following keys:
            KEY_RETURN_STATUS  : Boolean - Whether the configObject is valid
            KEY_RETURN_MESSAGES: List    - List of messages appropriate for user
    """
    errors = []

    #---------------------------------------------------------------------------
    # Identify top level unexpected keys
    #---------------------------------------------------------------------------
    for key in configObject:
        if key not in [
            KEY_CONFIG_BRANCH_ORDER,
            KEY_CONFIG_DEFAULT_TARGET,
            KEY_CONFIG_BRANCHES
        ]:
            errors.append('Unexpected configuration option: ' + key)

    #---------------------------------------------------------------------------
    # branchOrder
    #---------------------------------------------------------------------------
    branchOrderErrors = utilValidateKeyPresenceAndType(
        configObject,
        KEY_CONFIG_BRANCH_ORDER,
        [],
        '',
        'array'
    )
    errors += branchOrderErrors

    if len(branchOrderErrors) == 0:

        # Make sure all branch names are valid regular expressions
        for i, branch in enumerate(configObject[KEY_CONFIG_BRANCH_ORDER]):
            # Make sure it's a string
            if not isinstance(branch, ''.__class__):
                errors.append(
                    KEY_CONFIG_BRANCH_ORDER + ': Element ' + str(i) +
                    ' must be a string'
                )
            else:
                # Make sure it's a valid regular expression
                try:
                    re.compile(branch)
                except:
                    errors.append(
                        KEY_CONFIG_BRANCH_ORDER + ': Element ' + str(i) +
                        ' is not a valid regular expression'
                    )

    #---------------------------------------------------------------------------
    # defaultTarget
    #---------------------------------------------------------------------------
    errors += utilValidateKeyPresenceAndType(
        configObject,
        KEY_CONFIG_DEFAULT_TARGET,
        '',
        '',
        'string'
    )

    #---------------------------------------------------------------------------
    # branches
    #---------------------------------------------------------------------------
    branchesErrors = utilValidateKeyPresenceAndType(
        configObject,
        KEY_CONFIG_BRANCHES,
        [],
        '',
        'array'
    )
    errors += branchesErrors

    if len(errors) == 0:
        # Validate each branch
        for i, branch in enumerate(configObject[KEY_CONFIG_BRANCHES]):
            # Branch Name
            branchErrors = utilValidateKeyPresenceAndType(
                branch,
                KEY_CONFIG_BRANCH_NAME,
                '',
                'branch ' + str(i) + ': ',
                'string'
            )
            errors += branchErrors

            if len(errors) == 0:
                # Make sure branch name is a valid regular expression
                try:
                    re.compile(branch[KEY_CONFIG_BRANCH_NAME])
                except:
                    errors.append(
                        'branch ' + str(i) + ': ' + KEY_CONFIG_BRANCH_NAME +
                        ' is not a valid regular expression'
                     )

            # Branch Target
            errors += utilValidateKeyPresenceAndType(
                branch,
                KEY_CONFIG_BRANCH_TARGET,
                '',
                'branch ' + str(i) + ': ',
                'string'
            )

            # Branch Unexpected Keys
            for key in branch:
                if key not in [KEY_CONFIG_BRANCH_NAME, KEY_CONFIG_BRANCH_TARGET]:
                    errors.append(
                        'Unexpected configuration option for branch ' + str(i) +
                        ': ' + key
                    )

    returnVal = {
        KEY_RETURN_STATUS: len(errors) == 0,
        KEY_RETURN_MESSAGES: errors
    }

    return returnVal

#-------------------------------------------------------------------------------
def utilValidateKeyPresenceAndType(
    testObject,
    key,
    sampleType,
    msgPrefix,
    userFriendlyType
):
    """
    Validate the the specified key is in the testObject and the value is the
    same type as sampleType

    Args
        Dictionary testObject       - The object we're testing
        String     key              - The key to look for
        Mixed      sampleType       - An object of the same type we want key's
                                      value to be
        String     msgPrefix        - The string to be used as a prefix for
                                      errors
        String     userFriendlyType - The name of the type to be shown in
                                      error message

    Return
        List of String - The errors encountered. Empty if no errors.
    """
    errors = []

    if key not in testObject:
        errors.append(msgPrefix + 'Missing ' + key)
    else:
        if not isinstance(testObject[key], sampleType.__class__):
            errors.append(msgPrefix + key + ' must be a ' + userFriendlyType)

    return errors

#-------------------------------------------------------------------------------
def main():
    global GLOBAL_GIT_NO_OPTIONAL_LOCKS

    # Default output, in order, to be used if user doesn't specify any
    if len(sys.argv) > 1 and sys.argv[1] == 'shell-prompt-helper':
        requestedCmd = shellPromptHelper
        firstOptionIndex = 2
        defaultOptions = {
            KEY_OPTIONS_SELECTED_OUTPUT: [
                OPTIONS_OUTPUT_STASHES,
                OPTIONS_OUTPUT_STAGE,
                OPTIONS_OUTPUT_WORK_DIR,
                OPTIONS_OUTPUT_UNMERGED,
                OPTIONS_OUTPUT_UNTRACKED,
                OPTIONS_OUTPUT_AHEAD_REMOTE,
                OPTIONS_OUTPUT_BEHIND_REMOTE,
                OPTIONS_OUTPUT_AHEAD_TARGET,
                OPTIONS_OUTPUT_BEHIND_TARGET,
                OPTIONS_OUTPUT_BRANCH_NAME,
                OPTIONS_OUTPUT_TARGET_BRANCH,
            ],
        }
    else:
        requestedCmd = fullRepoOutput
        firstOptionIndex = 1
        defaultOptions = {
            KEY_OPTIONS_COLOR: OPTIONS_COLOR_AUTO,
            KEY_OPTIONS_MAX_WIDTH: OPTIONS_MAX_WIDTH_AUTO,
            KEY_OPTIONS_SELECTED_OUTPUT: [
                OPTIONS_OUTPUT_STASHES,
                OPTIONS_OUTPUT_STAGE,
                OPTIONS_OUTPUT_WORK_DIR,
                OPTIONS_OUTPUT_UNMERGED,
                OPTIONS_OUTPUT_UNTRACKED,
                OPTIONS_OUTPUT_BRANCH_ALL,
            ],
        }

    options = defaultOptions.copy()

    # Parse the command line options
    i = firstOptionIndex
    while i < len(sys.argv):
        if sys.argv[i] == '--custom':
            customDone = False
            options[KEY_OPTIONS_SELECTED_OUTPUT] = []

            i += 1
            while i < len(sys.argv) and not customDone:
                arg = sys.argv[i]
                if arg.startswith('--'):
                    customDone = True
                elif arg not in defaultOptions[KEY_OPTIONS_SELECTED_OUTPUT]:
                    print('Unknown --custom option: ' + arg)
                    sys.exit(1)
                else:
                    options[KEY_OPTIONS_SELECTED_OUTPUT].append(sys.argv[i])
                    i += 1

        elif sys.argv[i] == '--color':
            options[KEY_OPTIONS_COLOR] = OPTIONS_COLOR_YES
            i += 1

        elif sys.argv[i] == '--no-color':
            options[KEY_OPTIONS_COLOR] = OPTIONS_COLOR_NO
            i += 1

        elif sys.argv[i] == '--no-optional-locks':
            GLOBAL_GIT_NO_OPTIONAL_LOCKS = True
            i += 1

        elif sys.argv[i] == '--max-width':
            i += 1
            if (i < len(sys.argv)):
                customWidth = sys.argv[i]
                if not re.match('^[1-9][0-9]+', customWidth):
                    print(
                        '--max-width value of ' +
                        '"' + customWidth + '"' +
                        ' must be numeric and greater than 0')
                    sys.exit(1)
            else:
                print('--max-width option is missing a width value')
                sys.exit(1)

            options[KEY_OPTIONS_MAX_WIDTH] = customWidth
            i += 1

        elif sys.argv[i] == '--help':
            utilPrintHelp(sys.argv[0])
            sys.exit(0)

        elif sys.argv[i] == '--helpconfig':
            utilPrintHelpConfig()
            sys.exit(0)

        elif sys.argv[i] == '--version':
            print(VERSION)
            sys.exit(0)

        else:
            print('Unknown command line argument: ' + sys.argv[i])
            print('See "' + sys.argv[0] + ' --help"')
            sys.exit(1)

    requestedCmd(options)

#-------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
