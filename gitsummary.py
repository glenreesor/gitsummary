#!/usr/bin/env python3

#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License, version 3,
#  as published by the Free Software Foundation.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import re
import subprocess
import sys

#-----------------------------------------------------------------------------
# Keys to dictionaries so errors will be caught by linter rather than at runtime
#-----------------------------------------------------------------------------
KEY_COMMIT_SHORT_HASH = 'shortHash'
KEY_COMMIT_DESCRIPTION = 'description'

KEY_FILE_STATUSES_STAGED = 'staged'
KEY_FILE_STATUSES_MODIFIED = 'modified'
KEY_FILE_STATUSES_UNTRACKED = 'untracked'
KEY_FILE_STATUSES_UNKNOWN = 'unknown'

KEY_FILE_STATUSES_TYPE = "type"
KEY_FILE_STATUSES_FILENAME = "filename"
KEY_FILE_STATUSES_NEW_FILENAME = "newFilename"
KEY_FILE_STATUSES_HEURISTIC_SCORE = "heuristicScore"

KEY_STASH_FULL_HASH = 'fullHash'
KEY_STASH_NAME = 'name'
KEY_STASH_DESCRIPTION = 'description'

#-----------------------------------------------------------------------------
# Other constants so we can catch typos by linting
#-----------------------------------------------------------------------------
TEXT_BOLD = 'bold'
TEXT_FLASHING = 'flashing'
TEXT_GREEN = 'green'
TEXT_MAGENTA = 'magenta'
TEXT_NORMAL = 'normal'
TEXT_YELLOW = 'yellow'
TEXT_RED = 'red'

#-----------------------------------------------------------------------------
# Command layer
#
# These functions orchestrate the output for top level gitsummary commands
#-----------------------------------------------------------------------------
def cmdRepo():
    """
    Print the output corresponding to the 'repo' command. Example:

    Stashes   stash@{0} This is a stash
              stash@{1} This is another stash

    Staged    M filename1
              M filename2

    Modified  M filename1
              M filename2

    Untracked filename1
              filename2

                          Remote   Target
       master              .  .
     * dev                 .  .     .  .  master
       featureBranch       .  .     .  .  dev
    """
    #-------------------------------------------------------------------------
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
    #-------------------------------------------------------------------------

    # Stashes
    #   3 columns: 'Stashes' title (optional), name, description
    #   Example  : 'Stashes', 'stash@{0}', 'WIP on branch xyz'
    #              ''       , 'stash@{1}', 'WIP on branch abc'
    rawStashList = gitGetStashes()
    rawStashLines = []

    for i, oneStash in enumerate(rawStashList):
        rawStashLines.append(
            ['Stashes' if i == 0 else ''] +
            utilGetStashAsTwoColumns(oneStash)
        )

    fileStatuses = gitGetFileStatuses()

    # Staged Files
    #   3 columns: 'Staged' title (optional), changeType, filename
    #   Example  : 'Staged', 'M'     , 'file1'
    #              ''      , 'A'     , 'file2'
    #              '  '    , 'R(100)', 'file3 -> newFile3'
    rawStagedList = fileStatuses[KEY_FILE_STATUSES_STAGED]
    rawStagedLines = []

    for i, stagedFile in enumerate(rawStagedList):
        rawStagedLines.append(
            ['Staged' if i == 0 else ''] +
            utilGetStagedFileAsTwoColumns(stagedFile)
        )

    # Modified Files
    #   3 columns: 'Modified' title, changeType, filename
    #   Example  : 'Modified', 'M', 'file1'
    #              ''        , 'D', 'file2'
    rawModifiedList = fileStatuses[KEY_FILE_STATUSES_MODIFIED]
    rawModifiedLines = []

    for i, modifiedFile in enumerate(rawModifiedList):
        rawModifiedLines.append(
            ['Modified' if i == 0 else ''] +
            utilGetModifiedFileAsTwoColumns(modifiedFile)
        )

    # Untracked Files
    #   2 columns: 'Untracked' title, filename
    #   Example  : 'Untracked', 'file1'
    #              ''         , 'file2'
    rawUntrackedList = fileStatuses[KEY_FILE_STATUSES_UNTRACKED]
    rawUntrackedLines = []

    for i, untrackedFile in enumerate(rawUntrackedList):
        rawUntrackedLines.append(
            [
                'Untracked' if i == 0 else '',
                untrackedFile,
            ]
        )

    # Branch List
    #   5 columns:
    #       current-branch indicator (optional),
    #       name,
    #       remote +/-,
    #       target +/-,
    #       target name
    #   Example  : '*', 'dev'    , '+1  -2', '+3  -4', 'master'
    #              '' , 'branch1', '+1  -2', '+3  -4', 'dev'
    localBranches = gitGetLocalBranches()
    currentBranch = gitGetCurrentBranch()

    # Title line
    # Leading spaces so they're centered
    rawBranchLines = [
        ['', '', '  Remote', '  Target', ''],
    ]

    # Do master and dev first since they're the most important
    if 'master' in localBranches:
        rawBranchLines.append(
            utilGetBranchAsFiveColumns(currentBranch, 'master', '')
        )

    if 'dev' in localBranches:
        targetBranch = 'master' if 'master' in localBranches else ''
        rawBranchLines.append(
            utilGetBranchAsFiveColumns(currentBranch, 'dev', targetBranch)
        )

    # Now all the other branches
    targetBranch = 'dev' if 'dev' in localBranches else ''
    for branch in localBranches:
        if branch not in ['master', 'dev']:
            rawBranchLines.append(
                utilGetBranchAsFiveColumns(currentBranch, branch, targetBranch)
            )

    #-------------------------------------------------------------------------
    # For each section of output (stashes, staged, etc):
    #   - Determine maximum widths for each column of each line, so we can
    #     align columns within each section
    #
    # Each xyzMaxColumnWidths will be a List of numbers, where each number
    # is the maximum width of the corresponding column.
    #-------------------------------------------------------------------------
    stashesMaxColumnWidths = utilGetMaxColumnWidths(rawStashLines)
    stagedMaxColumnWidths = utilGetMaxColumnWidths(rawStagedLines)
    modifiedMaxColumnWidths = utilGetMaxColumnWidths(rawModifiedLines)
    untrackedMaxColumnWidths = utilGetMaxColumnWidths(rawUntrackedLines)
    branchesMaxColumnWidths = utilGetMaxColumnWidths(rawBranchLines)

    #-------------------------------------------------------------------------
    # Ensure that title column for each of stashes, staged, modified, and
    # untracked is the same width so they line up
    #-------------------------------------------------------------------------
    maxTitleWidths = max(
        stashesMaxColumnWidths[0] if len(stashesMaxColumnWidths) > 0 else 0,
        stagedMaxColumnWidths[0] if len(stagedMaxColumnWidths) > 0 else 0,
        modifiedMaxColumnWidths[0] if len(modifiedMaxColumnWidths) > 0 else 0,
        untrackedMaxColumnWidths[0] if len(untrackedMaxColumnWidths) > 0 else 0,
    )

    if len(stashesMaxColumnWidths) > 0:
        stashesMaxColumnWidths[0] = maxTitleWidths

    if len(stagedMaxColumnWidths) > 0:
        stagedMaxColumnWidths[0] = maxTitleWidths

    if len(modifiedMaxColumnWidths) > 0:
        modifiedMaxColumnWidths[0] = maxTitleWidths

    if len(untrackedMaxColumnWidths) > 0:
        untrackedMaxColumnWidths[0] = maxTitleWidths

    #-------------------------------------------------------------------------
    # Get all of our lines (still in columns) with each column padded or
    # truncated as required
    #-------------------------------------------------------------------------
    (SCREEN_WIDTH, SCREEN_HEIGHT) = os.get_terminal_size();
    TRUNCATION_INDICATOR = '...'

    alignedStashLines = utilGetColumnAlignedLines(
        SCREEN_WIDTH,
        TRUNCATION_INDICATOR,
        2,
        stashesMaxColumnWidths,
        rawStashLines,
    )

    alignedStagedLines = utilGetColumnAlignedLines(
        SCREEN_WIDTH,
        TRUNCATION_INDICATOR,
        2,
        stagedMaxColumnWidths,
        rawStagedLines,
    )

    alignedModifiedLines = utilGetColumnAlignedLines(
        SCREEN_WIDTH,
        TRUNCATION_INDICATOR,
        2,
        modifiedMaxColumnWidths,
        rawModifiedLines,
    )

    alignedUntrackedLines = utilGetColumnAlignedLines(
        SCREEN_WIDTH,
        TRUNCATION_INDICATOR,
        1,
        untrackedMaxColumnWidths,
        rawUntrackedLines,
    )

    alignedBranchLines = utilGetColumnAlignedLines(
        SCREEN_WIDTH,
        TRUNCATION_INDICATOR,
        1,
        branchesMaxColumnWidths,
        rawBranchLines,
    )

    #-------------------------------------------------------------------------
    # Final step: Create a single string for each line, with required colors
    #-------------------------------------------------------------------------
    styledStashLines = []
    for line in alignedStashLines:
        styledStashLines.append(
            line[0] + ' ' + utilGetStyledText([TEXT_GREEN], line[1]) + ' ' + line[2]
        )

    styledStagedLines = []
    for line in alignedStagedLines:
        styledStagedLines.append(
            line[0] + ' ' + utilGetStyledText([TEXT_GREEN], line[1] + ' ' + line[2])
        )

    styledModifiedLines = []
    for line in alignedModifiedLines:
        styledModifiedLines.append(
            line[0] + ' ' + utilGetStyledText([TEXT_RED], line[1] + ' ' + line[2])
        )

    styledUntrackedLines = []
    for line in alignedUntrackedLines:
        styledUntrackedLines.append(
            line[0] + ' ' + utilGetStyledText([TEXT_YELLOW], line[1])
        )

    styledBranchLines = []
    for line in alignedBranchLines:
        # Indicator, name, and remote need to be bold if the branch differs
        # from its remote.
        # We know a branch differs from its remote if the remote ahead/behind
        # string (column 2) contains any digits
        differsFromRemote = re.search('[0-9]', line[2])

        col0Format = [TEXT_MAGENTA] + ([TEXT_BOLD] if differsFromRemote else [])
        possiblyBoldFormat = [TEXT_BOLD] if differsFromRemote else []

        styledBranchLines.append(
            utilGetStyledText(col0Format, line[0]) + ' ' +
            utilGetStyledText(possiblyBoldFormat, line[1]) + ' ' +
            utilGetStyledText(possiblyBoldFormat, line[2]) + ' ' +
            line[3] + ' ' +
            line[4]
        )

    #-------------------------------------------------------------------------
    # Print all our beautifully formatted output
    #-------------------------------------------------------------------------
    previousSectionHadOutput = False
    for section in [
        styledStashLines,
        styledStagedLines,
        styledModifiedLines,
        styledUntrackedLines,
        styledBranchLines
    ]:
        if previousSectionHadOutput:
            print()
        for line in section:
            print(line)
        previousSectionHadOutput = True if len(section) > 0 else False

    #-------------------------------------------------------------------------
    # Notify user if git returned something we didn't know how to handle
    #-------------------------------------------------------------------------
    rawUnknownFileList = fileStatuses[KEY_FILE_STATUSES_UNKNOWN]
    if len(rawUnknownFileList) > 0:
        print('git returned some unexpected output:')
        print('')
        for unknownOutput in rawUnknownFileList:
            print(unknownOutput)

        print('\nPlease notify the gitsummary author.')

#-----------------------------------------------------------------------------
# git interface layer
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
#   - They assume there is at least one commit, thus will produce unexpected
#     results or throw exceptions if run immediately after 'git init'.
#     It's too much of a pain to deal with this edge case.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
def gitGetCommitDetails(fullHash):
    """
    Get the details of the commit corresponding to the specified fullHash.

    Args
        String fullHash - the full hash of the commit in question

    Return
        Dictionary - With the following keys:
            KEY_COMMIT_SHORT_HASH : String
            KEY_COMMIT_DESCRIPTION: String
    """

    # Strictly speaking, 'git show' isn't a plumbing command.
    # But we're using it in a porcelain'ish way -- getting something formatted
    # nicely. So we should be good.
    output = gitUtilGetOutput(
        ['git', 'show', fullHash, '--pretty=%h %s', '--no-patch']
    )[0]
    # Expected output:
    # [short hash] [one line description]

    split = output.split(' ', 1)
    description = {
        KEY_COMMIT_SHORT_HASH : split[0],
        KEY_COMMIT_DESCRIPTION: split[1],
    }

    return description

#-----------------------------------------------------------------------------
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
        ['git', 'for-each-ref', HEAD_REF_PREFIX, '--format=%(refname)']
    )

    remoteBranchRefs = gitUtilGetOutput(
        ['git', 'for-each-ref', REMOTE_REF_PREFIX, '--format=%(refname)']
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
        commitList = gitUtilGetOutput(
            ['git', 'rev-list', topoFlag, branch1]
        )
    else:
        commitList = gitUtilGetOutput(
            ['git', 'rev-list', topoFlag, branch1, '^' + branch2]
        )
    # Expected output:
    # [full hash1]
    # [full hash2]
    # etc.

    return commitList

#-----------------------------------------------------------------------------
def gitGetCurrentBranch():
    """
    Get the name of the current branch.

    Return
        String - The name of the current branch
               - '' if HEAD does not correspond to a branch
                 (i.e. detached HEAD state)
    """
    output = gitUtilGetOutput(['git', 'status', '--branch', '--porcelain=2'])
    # Expected output: a bunch of lines starting with '#', where we only care
    # about:
    #   # branch.head BRANCH
    # BRANCH will be '(detached)' if detached head state
    parsedBranch = ''
    for line in output:
        match = re.match('^# branch.head (.+)$', line)
        if (match):
            parsedBranch = match.group(1)

    currentBranch = parsedBranch if parsedBranch != '(detached)' else ''

    return currentBranch

#-----------------------------------------------------------------------------
def gitGetFileStatuses():
    """
    Get statuses for all files that have been modified or are not tracked

    Return
        Dictionary with the following contents:
            KEY_FILE_STATUSES_STAGED:    []   - staged files
            KEY_FILE_STATUSES_MODIFIED:  []   - modified working dir files
            KEY_FILE_STATUSES_UNTRACKED: []   - non-git tracked files
            KEY_FILE_STATUSES_UNKNOWN:   []   - unknown git output

        The elements of each list have the following formats (all keys prepended
        with 'KEY_FILE_STATUSES_', but ommitted here for brevity)

        STAGED: Dictionary of the form:
            TYPE           : String - The single letter code from 'git status --short'
            FILENAME       : String - The filename
            NEW_FILENAME   : String - The new filename if the TYPE was one of
                                      'C' or 'R'
            HEURISTIC_SCORE: String - The value (0-100) that git assigns when
                                      deciding if the file was renamed/copied

        MODIFIED: Dictionary of the form:
            TYPE           : String - The single letter code from 'git status --short'
            FILENAME       : String - The filename

        UNTRACKED: String - The name of the file that's untracked

        UNKNOWN: String - The raw git output that couldn't be parsed
    """
    TRACKED = 'tracked'
    UNKNOWN_FORMAT = 'unknown-format'
    UNTRACKED = 'untracked'

    output = gitUtilGetOutput(['git', 'status', '--porcelain=2'])

    #-------------------------------------------------------------------------
    # Each line of output describes one file.
    # That description specifies how the committed file differs from:
    #   - that file in the index (stage)
    #   - that file in the working directory
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
    #-------------------------------------------------------------------------

    fileStatuses = {
        KEY_FILE_STATUSES_STAGED: [],
        KEY_FILE_STATUSES_MODIFIED: [],
        KEY_FILE_STATUSES_UNTRACKED: [],
        KEY_FILE_STATUSES_UNKNOWN: [],
    }

    for outputLine in output:
        #---------------------------------------------------------------------
        # Different types of changes have different output formats. Get the
        # data that we'll assemble later.
        #   - filename       (all types)
        #   - newFilename    (only renames or copies)
        #   - heuristicScore (only renames or copies)
        #---------------------------------------------------------------------
        parseCode = TRACKED

        # Note that we can't just split on spaces, since our filename may have
        # spaces in it

        if outputLine[0] == '1':
            # 1 <XY> <sub> <mH> <mI> <mW> <hH> <hI> <path>
            match = re.match('([^ ]+ ){8}(.+)$', outputLine)
            filename = match.group(2)

        elif outputLine[0] == '2':
            # 2 <XY> <sub> <mH> <mI> <mW> <hH> <hI> <X><score> <path>[tab]<origPath>
            match = re.match('^([^ ]+ ){8}[A-Z]([^ ]+) (.+)\t(.+)$', outputLine)
            heuristicScore = match.group(2)
            newFilename = match.group(3)
            filename = match.group(4)

        elif outputLine[0] == 'u':
            # u <XY> <sub> <m1> <m2> <m3> <mW> <h1> <h2> <h3> <path>
            match = re.match('^([^ ]+ ){10}(.+)$', outputLine)
            filename = match.group(2)

        elif outputLine[0] == '?':
            # ? <path>
            parseCode = UNTRACKED
            filename = outputLine[2:]

        else:
            parseCode = UNKNOWN_FORMAT

        #---------------------------------------------------------------------
        # Build the dictionaries that will be returned for each of staged,
        # modified, untracked, and unknown files. The latter being an unknown
        # format (shouldn't happen).
        #---------------------------------------------------------------------
        if parseCode == UNKNOWN_FORMAT:
            fileStatuses[KEY_FILE_STATUSES_UNKNOWN].append(outputLine)
        elif parseCode == UNTRACKED:
            fileStatuses[KEY_FILE_STATUSES_UNTRACKED].append(filename)
        else:
            # We're looking at an output line where outputLine[2:3] is the 'XY'
            # that indicates how the committed file differs from the stage ('X')
            # and the working dir ('Y').
            #
            # So append this file info to the appropriate list, based on the XY
            # value.
            for position in [2, 3]:
                code = outputLine[position: position + 1]

                # A code of '.' means this file is unchanged
                if code != '.':
                    thisFileStatus = {
                        KEY_FILE_STATUSES_TYPE: code,
                        KEY_FILE_STATUSES_FILENAME: filename,
                    }

                    # Get the info specific to renames or copies.
                    # Note that the git status manpage says it can indicate when a
                    # file is copied, however this thread says that's false:
                    #   https://marc.info/?l=git&m=141730775928542&w=2
                    #
                    # We'll be on the safe side and look for copies anyway.
                    if code in ['C', 'R']:
                        thisFileStatus[KEY_FILE_STATUSES_NEW_FILENAME] = newFilename
                        thisFileStatus[KEY_FILE_STATUSES_HEURISTIC_SCORE] = heuristicScore

                    keyToUse = (
                        KEY_FILE_STATUSES_STAGED if position == 2
                        else KEY_FILE_STATUSES_MODIFIED
                    )
                    fileStatuses[keyToUse].append(thisFileStatus)

    return fileStatuses

#-----------------------------------------------------------------------------
def gitGetLocalBranches():
    """
    Get a list of local branch names.

    Return
        List of String - The list of branch names
    """

    branchRefs = gitUtilGetOutput(
        ['git', 'for-each-ref', 'refs/heads', '--format=%(refname)']
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

#-----------------------------------------------------------------------------
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
    #-------------------------------------------------------------------------
    localBranches = gitGetLocalBranches()

    if localBranch not in localBranches:
        remoteTrackingBranch = ''
    elif len(localBranches) == 1:
        # There's only one branch -- the current one. So use 'git status' to
        # determine it's remote (if any).
        #
        # We use this approach since it also works when there are no refs
        # (which is the case immediately after 'git init')

        output = gitUtilGetOutput(['git', 'status', '--branch', '--porcelain=2'])
        # Expected output: a bunch of lines starting with '#', where we only care
        # about:
        #   # branch.upstream REMOTE/BRANCH
        remoteTrackingBranch = ''
        for line in output:
            match = re.match('^# branch.upstream (.+)$', line)
            if (match):
                remoteTrackingBranch = match.group(1)

    else:
        remoteTrackingBranch = gitUtilGetOutput(
            [
                'git',
                'for-each-ref',
                '--format=%(upstream:short)',
                'refs/heads/' + localBranch
            ]
        )[0]
        # Expected output:
        # [fully qualified branch name]

    return remoteTrackingBranch

#-----------------------------------------------------------------------------
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
    refs = gitUtilGetOutput(
        [
            'git',
            'for-each-ref',
            '--format=%(refname)',
        ]
    )

    if not 'refs/stash' in refs:
        # No stash ref exists, so there can't be any stashes.
        return []

    # refs/stash exists, so we can now do what we wanted to do in the first
    # place -- list the stashes
    stashes = []

    output = gitUtilGetOutput(
        ['git', 'reflog', '--no-abbrev-commit', 'refs/stash']
    )
    # Expected output:
    # [full hash] refs/stash@{0}: [description]
    # [full hash] refs/stash@{1}: [description]
    # etc.

    for oneStash in output:
        split = oneStash.split(' ', 2)
        nameMatch = re.match('^refs/([^:]+})', split[1])
        name = nameMatch.group(1)
        stashes.append(
            {
                KEY_STASH_FULL_HASH  : split[0],
                KEY_STASH_NAME       : name,
                KEY_STASH_DESCRIPTION: split[2],
            }
        )

    return stashes

#-----------------------------------------------------------------------------
def gitUtilFolderIsTracked():
    """
    Return whether the current folder is tracked by git.

    Return
        Boolean - Is it tracked?
    """
    isGitTracked = True

    # Something simple. We don't use gitUtilGetOutput() because it's called
    # in contexts where we know (or think we know) a folder is git tracked,
    # and will exit immediately if not.
    try:
        output = subprocess.check_output(
            ['git', 'for-each-ref', '--count=1', '--format=42'],
            stderr = subprocess.STDOUT,
            universal_newlines = True
        )

        # We're expecting an exception to be raised due to a non-zero exit
        # code. Check here as well, since it'll shut up the linter
        if gitUtilOutputSaysNotTracked(output):
            isGitTracked = False

    except subprocess.CalledProcessError as e:
        if gitUtilOutputSaysNotTracked(e.output):
            isGitTracked = False
        else:
            raise

    return isGitTracked

#-----------------------------------------------------------------------------
def gitUtilGetOutput(command):
    """
    Get the output from running the specified git command.

    It is assumed the current folder is git tracked. As a precaution, this
    function will call sys.exit() if it's not, indicating that this is a
    programming error.

    Non-zero exit codes will result in an error being thrown.

    Args
        List command - The git command to run, including the 'git' part

    Return
        List of String - Each element is one line of output from the executed
                         command
    """
    try:
        output = subprocess.check_output(
            command,
            stderr = subprocess.STDOUT,
            universal_newlines = True
        )

    except subprocess.CalledProcessError as e:
        if gitUtilOutputSaysNotTracked(e.output):
            msg = 'Current folder is not git tracked. '
            msg += 'This is a programming error in gitsummary.'
            print(msg)
            sys.exit()
        else:
            raise
    else:
        returnVal = output.splitlines()

    return returnVal

#-----------------------------------------------------------------------------
def gitUtilOutputSaysNotTracked(gitOutput):
    """
    Return whether the specified string matches the git message when the current
    folder (or any of it's parents) is not git tracked.

    Return
        Boolean - Whether it's git tracked or not
    """
    MAGIC_OUTPUT = 'Not a git repository'

    return True if MAGIC_OUTPUT in gitOutput else False

#-----------------------------------------------------------------------------
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

#-----------------------------------------------------------------------------
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
        List of String - First element : '*' if branch is the current branch
                                         (otherwise '')
                       - Second element: branch name
                       - Third element : commits ahead/behind remote branch
                       - Fourth element: commits ahead/behind target branch
                       - Fifth element : name of target branch
    """
    remoteBranch = gitGetRemoteTrackingBranch(branch)

    currentBranchIndicator = '*' if branch == currentBranch else ''
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

#-----------------------------------------------------------------------------
def utilGetColumnAlignedLines(
    requiredWidth,
    truncIndicator,
    variableColumn,
    columnWidths,
    lines
):
    """
    Get an array of lines (broken into columns) where columns are aligned and the
    entire line is exactly 'requiredWidth' characters.

    All columns except the 'variableColumn' one will be treated as fixed width,
    thus padding will be applied where appropriate.

    The 'variableColumn' column will be padded or truncated to ensure the total
    line width is exactly 'requiredWidth' characters.

    This function can be called with an empty List of lines, in which case an
    empty List will be returned.

    Args
        Number requiredWidth  - The required line length
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
                        ['line2-col1-bla   ', 'line2-col2-bla', 'line2-col3-b'],
                    ]
    """
    if len(lines) == 0:
        return []

    alignedLines = []

    # Get the width of all the static columns, so we can calculate how much is
    # left for the variable width columns
    staticWidth = sum(columnWidths) - columnWidths[variableColumn]
    numColumns = len(columnWidths)

    for line in lines:
        columns = []
        availableWidth = requiredWidth - staticWidth - (numColumns - 1)
        for i, column in enumerate(line):
            if i != variableColumn:
                # This is a column to be padded out to the required max width
                formatString = '{0:<' + str(columnWidths[i]) + '}'
                formattedColumn = formatString.format(column)
            else:
                # This is a column that needs to be padded or truncated to
                # ensure total line width is 'requiredWidth'
                formatString = (
                    '{0:<' +
                    str(availableWidth) +
                    '.' +
                    str(availableWidth) +
                    '}'
                )
                formattedColumn = formatString.format(column)

                # If we truncated this column, replace the last n characters
                # with the requested truncation indicator
                if len(column) > availableWidth and truncIndicator != '':
                    formattedColumn = (
                        formattedColumn[0:-len(truncIndicator)] + truncIndicator
                    )

            columns.append(formattedColumn)
        alignedLines.append(columns)

    return alignedLines

#-----------------------------------------------------------------------------
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

#-----------------------------------------------------------------------------
def utilGetModifiedFileAsTwoColumns(modifiedFile):
    """
    Get the specified modifiedFile formatted as two columns

    Args
        Dictionary modifiedFile - One modifiedFile as returned by
                                  gitGetFileStatuses

    Return
        List of String - First element:  Change type
                                         Examples: 'D', 'M'
                       - Second element: Filename
    """
    return [
        modifiedFile[KEY_FILE_STATUSES_TYPE],
        modifiedFile[KEY_FILE_STATUSES_FILENAME],
    ]

#-----------------------------------------------------------------------------
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

#-----------------------------------------------------------------------------
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

#-----------------------------------------------------------------------------
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
        TEXT_BOLD: '1',
        TEXT_FLASHING: '5',
        TEXT_GREEN: '32',
        TEXT_MAGENTA: '35',
        TEXT_NORMAL: '0',
        TEXT_RED: '31',
        TEXT_YELLOW: '33'
    }

    if len(styles) == 0:
        return text

    styleList = ''
    for i, style in enumerate(styles):
        styleList += ('' if i == 0 else ';') + ESCAPE_MAPPING[style]

    escapeStart = '\033[' + styleList + 'm'
    escapeEnd = '\033[' + ESCAPE_MAPPING[TEXT_NORMAL] + 'm'

    return escapeStart + text + escapeEnd

#-----------------------------------------------------------------------------
def main():
    if not gitUtilFolderIsTracked():
        print('This folder is not tracked by git.')
        sys.exit(1)

    cmdRepo()

#-----------------------------------------------------------------------------
if __name__ == '__main__':
    main()
