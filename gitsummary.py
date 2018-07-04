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
    topoFlag = '--topo-order' if topologicalOrder else ''
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
    output = gitUtilGetOutput(['git', 'rev-parse', '--abbrev-ref', '@'])
    # Expected output:
    # HEAD | [branchName]

    currentBranch = '' if output[0] == 'HEAD' else output[0]

    return currentBranch

#-----------------------------------------------------------------------------
def gitGetFileStatuses():
    """
    Get statuses for all files that differ from the corresponding committed files.

    Return
        Dictionary with the following contents:
            KEY_FILE_STATUSES_STAGED: []         - staged files are different
            KEY_FILE_STATUSES_MODIFIED: []       - working dir files are different
            KEY_FILE_STATUSES_UNTRACKED: []      - not git tracked files
            KEY_FILE_STATUSES_UNKNOWN: []        - unknown git output

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
        fields = outputLine.split(' ')

        #---------------------------------------------------------------------
        # Different types of changes have different output formats. Get the
        # data that we'll assemble later.
        #   - filename       (all types)
        #   - newFilename    (only renames or copies)
        #   - heuristicScore (only renames or copies)
        #---------------------------------------------------------------------
        parseCode = TRACKED
        if fields[0] == '1':
            filename = fields[8]

        elif fields[0] == '2':
            pathSplit = fields[9].split('\t')

            filename = pathSplit[1]
            newFilename = pathSplit[0]
            heuristicScore = fields[8][1:]

        elif fields[0] == 'u':
            filename = fields[10]

        elif fields[0] == '?':
            parseCode = UNTRACKED
            filename = fields[1]

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
            # We're looking at an output line where field[1] is the 'XY' that
            # indicates how the committed file differs from the stage ('X') and
            # the working dir ('Y').
            #
            # So append this file info to the appropriate list, based on the XY
            # value.
            for position in [0, 1]:
                code = fields[1][position: position + 1]

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
                        KEY_FILE_STATUSES_STAGED if position == 0
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

    localBranches = gitUtilGetOutput(
        ['git', 'rev-parse', '--abbrev-ref', '--branches']
    )
    # Expected output:
    # [branch1 name]
    # [branch2 name]
    # etc.

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
    localBranches = gitGetLocalBranches()
    if localBranch not in localBranches:
        remoteTrackingBranch = ''
    else:
        # We use 'git for-each-ref' rather than just 'rev-parse @' since the
        # latter results in an error if there's no corresponding remote
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
    stashesExist = False
    stashes = []

    # 'git show-ref refs/stash' exits with status 1 if there are no stashes.
    # So brute force it by listings all refs and seeing if there are any stashes
    output = gitUtilGetOutput(['git', 'show-ref'])
    # Expected output:
    # [long hash] refs/[heads | remotes | tags]/[name]
    # [long hash] refs/[heads | remotes | tags]/[name]
    # etc.

    for outputLine in output:
        if 'refs/stash' in outputLine:
            stashesExist = True

    if stashesExist:
        # We know there's at least one stash, so now get the complete list
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
def gitUtilRepositoryIsInitialState():
    """
    Return whether the git repository is in the initial state immediately
    after 'git init'.

    This is important to know because there are no refs at this point, and
    most (all?) of our gitGet* functions use git commands that operate on refs.

    Return
        Boolean - Whether the current repository is in that state
    """
    output = gitUtilGetOutput(
        [
            'git',
            'for-each-ref',
            '--count=1',
            '--format=%(*refname)'
        ]
    )

    return True if len(output) == 0 else False
