#!/bin/bash

# Output a single line showing complete status of current git repo

#-------------------------------------------------------------------------------
# Things you may want to change
#-------------------------------------------------------------------------------
GITSUMMARY=gitsummary.py   # Include path if not in $PATH

# Specify contents and appearance
#   show:
#       - For numeric values, one of:
#           no      - Don't show it
#           num     - Show the numeric value if it's not zero
#           boolean - Show nothing if 0, otherwise just the prefix
#
#       - For strings values, one of:
#           no  - Don't show it
#           yes - Show it
#
#   prefix:
#       - String to show before the value (or string to show if corresponding
#         'show' is 'boolean')
#
#   suffix:
#       - String to show after the value (not used if corresponding 'show' is
#         'boolean')
#
#   styles:
#       - Space-separated list of terminal styles to use
#       - Valid values:
#           normal, bright, dim, overline, reverse, strike-through, underline
#           fg-black, fg-blue, fg-cyan, fg-green, fg-magenta, fg-red, fg-yellow, fg-white
#           bg-black, bg-blue, bg-cyan, bg-green, bg-magenta, bg-red, bg-yellow, bg-white

declare -A show prefix suffix styles

show['numStashes']=boolean      ; prefix['numStashes']=◆        ; suffix['numStashes']=''      ; styles['numStashes']='bright fg-green'
show['numStage']=num            ; prefix['numStage']=⦁        ; suffix['numStage']=''        ; styles['numStage']='bright fg-green'
show['numWorkDir']=num          ; prefix['numWorkDir']=⛌        ; suffix['numWorkDir']=''      ; styles['numWorkDir']='bright fg-magenta'
show['numUnmerged']=num         ; prefix['numUnmerged']=‼       ; suffix['numUnmerged']=''     ; styles['numUnmerged']='blink bright fg-red'
show['numUntracked']=boolean    ; prefix['numUntracked']='...'  ; suffix['numUntracked']=''    ; styles['numUntracked']='fg-cyan'

show['numAheadRemote']=num      ; prefix['numAheadRemote']='+'  ; suffix['numAheadRemote']=''  ; styles['numAheadRemote']='bright fg-cyan'
show['numBehindRemote']=num     ; prefix['numBehindRemote']='-' ; suffix['numBehindRemote']='' ; styles['numBehindRemote']='bright fg-cyan'

show['numAheadTarget']=num      ; prefix['numAheadTarget']=+    ; suffix['numAheadTarget']=''  ; styles['numAheadTarget']='dim'
show['numBehindTarget']=num     ; prefix['numBehindTarget']=-   ; suffix['numBehindTarget']='' ; styles['numBehindTarget']='dim'

show['branchName']=yes          ; prefix['branchName']=''       ; suffix['branchName']=''      ; styles['branchName']='bright fg-yellow'
show['targetBranch']=yes        ; prefix['targetBranch']='('    ; suffix['targetBranch']=')'   ; styles['targetBranch']='dim'

# String and corresponding style that separates values
separatorString=' ' ; separatorStyles=''

# List of values to be printed, in order
# Removing names from this list whose 'show' above are 'no' may result in
# small performance improvements
outputInOrder="numStashes branchName numStage numWorkDir numUnmerged numUntracked numAheadRemote numBehindRemote numAheadTarget numBehindTarget targetBranch"

# Maximum length of output
maxLength=75

#-------------------------------------------------------------------------------
# No changes should be required below here
#-------------------------------------------------------------------------------

# Global variables used by addToOutputPieces(), since returning multiple values
# from bash functions is a pain.
declare -A outputPieces
outputCurrentIndex=0
outputLength=0

#-------------------------------------------------------------------------------
# Add the specified string to global $outputPieces[]. If it doesn't contain
# any escapes, then also add to global $outputLength.
#
# If strings contain escapes, it must not contain any characters that need to
# be included in the length calculation.
#
# Args
#   $1 - Boolean - Whether the string to be added contains escape characters.
#                  If it contains escape characters, it's length won't be
#                  added to $outputLength
#   $2 - String  - The string to be added
#-------------------------------------------------------------------------------
function addToOutputPieces()
{
    local containsEscape="$1"
    local string="$2"

    outputPieces[$outputCurrentIndex]="$string"

    if ! $containsEscape; then
        outputLength=$((outputLength + ${#string}))
    fi

    outputCurrentIndex=$((outputCurrentIndex + 1))
}

#-------------------------------------------------------------------------------
# Check the 'show' value for a non-numeric quantity. Exit if value is invalid.
#
# Args:
#   $1 - The name (for printing an error message)
#   $2 - The value to check
#-------------------------------------------------------------------------------
function check_showNonNumeric()
{
    local name="$1"
    local value="$2"

    if [ "$value" != "yes" ] && [ "$value" != "no" ]; then
        echo "Invalid value for show['$name']: '$value'"
        echo "It must be one of: yes, no"
        exit 1
    fi
}

#-------------------------------------------------------------------------------
# Check the 'show' value for a numeric quantity. Exit if value is invalid.
#
# Args:
#   $1 - The name (for printing an error message)
#   $2 - The value to check
#-------------------------------------------------------------------------------
function check_showNumeric()
{
    local name="$1"
    local value="$2"

    if [ "$value" != "num" ] && [ "$value" != "boolean" ] && [ "$value" != "no" ]; then
        echo "Invalid value for show['$name']: '$value'"
        echo "It must be one of: num, boolean, no"
        exit 1
    fi
}

#-------------------------------------------------------------------------------
# Print required output
#
# Args:
#      $1 - Whether to use test data (boolean)
#------------------------------------------------------------------------------
function doit()
{
    local useTestValues=$1

    declare -A MAP_TO_GITSUMMARY
    declare -A positions
    declare -A values

    local outputBranchIndex

    ALL_NAMES="numStashes numStage numWorkDir numUnmerged numUntracked numAheadRemote numBehindRemote numAheadTarget numBehindTarget branchName targetBranch"

    # Mapping of names in this script to corresponding ones used by gitsummary
    MAP_TO_GITSUMMARY['numStashes']='stashes'
    MAP_TO_GITSUMMARY['numStage']='stage'
    MAP_TO_GITSUMMARY['numWorkDir']='workdir'
    MAP_TO_GITSUMMARY['numUnmerged']='unmerged'
    MAP_TO_GITSUMMARY['numUntracked']='untracked'
    MAP_TO_GITSUMMARY['numAheadRemote']='ahead-remote'
    MAP_TO_GITSUMMARY['numBehindRemote']='behind-remote'
    MAP_TO_GITSUMMARY['numAheadTarget']='ahead-target'
    MAP_TO_GITSUMMARY['numBehindTarget']='behind-target'
    MAP_TO_GITSUMMARY['branchName']='branch-name'
    MAP_TO_GITSUMMARY['targetBranch']='target-branch'

    COLOR_NORMAL='\033[0m'

    if $useTestValues; then
        # Create an array of test values, where those values are the
        # quantity names, like numStashes etc.
        testValues=''

        # We need to know the position of each quantity so we can get it below
        currentPosition=0

        for name in $outputInOrder; do
            testValues="${testValues} ${name}"
            positions[$name]=$currentPosition
            ((currentPosition++))
        done

        gitsummaryOutput=($testValues)
    else
        # Translate names like 'numStashes' to 'stashes' as required by gitsummary
        options=""

        # We need to know the position of each quantity so we can get it below
        currentPosition=0

        for name in $outputInOrder; do
            options="${options} ${MAP_TO_GITSUMMARY[${name}]}"
            positions[$name]=$currentPosition
            ((currentPosition++))
        done

        gitsummaryOutput=( $($GITSUMMARY shell-prompt-helper --custom $options))
    fi

    # Grab the various values.
    # Bash will gracefully assign an empty string if ${currentPosition['bla']}
    # doesn't exist
    for name in $ALL_NAMES; do
        values[$name]=${gitsummaryOutput[${positions[$name]}]}
    done

    #---------------------------------------------------------------------------
    # Build the output string. In order to track the length and make it easy
    # to modify output if it's too long, we add the output pieces to an array
    # by calling addToOutputPieces().
    #---------------------------------------------------------------------------

    # The branch name will be shortened if the output line is too long, so
    # keep track of where it ends up in our array of output pieces.
    outputBranchIndex=-1

    for name in $outputInOrder; do

        #-----------------------------------------------------------------------
        # Determine what, if anything, needs to be included in the output
        #-----------------------------------------------------------------------

        # Whether we want this quantity to show up in the output
        showThis=false

        # Whether we want the value to be printed (false meaning just show
        # 'prefix' when the value is non-zero)
        showValue=false

        # Decide what showThis and showValue should be for this quantity
        if [ "$name" != "branchName" ] && [ "$name" != "targetBranch" ]; then
            check_showNumeric $name ${show[$name]}

            if [ "${show[$name]}" == "num" ] || [ "${show[$name]}" == "boolean" ]; then
                # We don't show 0 or "_" (the latter signifying a branch with no
                # remote)
                if [ "${values[$name]}" != "0" ] && [ "${values[$name]}" != "_" ]; then
                    showThis=true
                    if [ "${show[$name]}" == "num" ]; then
                        showValue=true
                    fi
                fi
            fi
        else
            check_showNonNumeric $name ${show[$name]}

            # Don't show values of "_", which signifies a branch with no target
            if [ "${show[$name]}" == "yes" ] && [ "${values[$name]}" != "_" ]; then
                showThis=true
                showValue=true
            fi
        fi

        #-----------------------------------------------------------------------
        # Add the required bits to our output
        #-----------------------------------------------------------------------
        if $showThis; then
            if [ $outputCurrentIndex -ne 0 ]; then
                # Separator
                addToOutputPieces true "$(getEscapeSequence "$separatorStyles")"
                addToOutputPieces false "$separatorString"
            fi

            # Style
            addToOutputPieces true "$(getEscapeSequence "${styles[$name]}")"

            # Prefix
            addToOutputPieces false "${prefix[$name]}"

            if $showValue; then
                if [ "$name" == "branchName" ]; then
                    # Remember this index so we can shorten the branch name if
                    # our line is too long
                    outputBranchIndex=$outputCurrentIndex
                fi

                # Value
                addToOutputPieces false "${values[$name]}"

                # Suffix
                addToOutputPieces false "${suffix[$name]}"
            fi

            # Reset style for next piece
            addToOutputPieces true "${COLOR_NORMAL}"
        fi
    done

    numOutputPieces=$outputCurrentIndex

    #-----------------------------------------------------------------------
    # Check the length and adjust if required
    #   - If we have a branch name:
    #       - Truncate it 
    #       - If truncating it doesn't remove enough characters then just show
    #         the (possibly truncated) branch name (instead of all the other
    #         requested output)
    #   - If we don't have a branch name:
    #       - Just truncate the entire line
    #
    # Note: We don't adjust any lengths if we're using test values, since test
    #       values result in output that is too long, so we won't get to see
    #       them
    #-----------------------------------------------------------------------

    showBranchNameOnly=false
    modifiedBranchName=""

    if ! $useTestValues && [ $outputLength -gt $maxLength ]; then
        numToRemove=$(($outputLength - $maxLength + 3))   # "3" is for "..."

        if [ "$outputBranchIndex" != "-1" ]; then
            branchName="${values[branchName]}"
            branchNameLength=${#branchName}

            if [ "$branchNameLength" -ge "$numToRemove" ]; then
                # Branch name has enough characters to truncate, so do that
                values[branchName]="${branchName:0:-$numToRemove}..."
            else
                # Branch name isn't long enough, so make the output just
                # the branch name, truncated if required
                values[branchName]="${branchName:0:$maxLength}"
                showBranchNameOnly=true
            fi
        else
            # No branchname, and line is too long. Can't imagine this ever
            # happening. Showing *something*, and fake it out by saying it's a
            # branch name
            values[branchName]="prompt length error"
            showBranchNameOnly=true
        fi
    fi

    #-----------------------------------------------------------------------
    # Create our output
    #-----------------------------------------------------------------------
    output=""

    if $showBranchNameOnly; then
        output="$(getEscapeSequence "${styles[branchName]}")${values[branchName]}${COLOR_NORMAL}"
    else
        currentIndex=0
        while [ $currentIndex -lt $numOutputPieces ]; do
            if [ "$currentIndex" == "$outputBranchIndex" ]; then
                # Use #values[branchName] since it may have been truncated above
                output="${output}${values[branchName]}"
            else
                output="${output}${outputPieces[$currentIndex]}"
            fi
            currentIndex=$((currentIndex + 1))
        done
    fi
    echo -e "$output"
}

#-------------------------------------------------------------------------------
# Get the ANSI escape sequence for the specified style list.
#
# Args:
#   $1 - The space-separated style list. e.g. "bright fg-blue"
#
# Return:
#   - The ANSI escape sequence
#-------------------------------------------------------------------------------
function getEscapeSequence()
{
    local styleList="$1"
    local styleCodes=''

    declare -A NAME_TO_CODE

    NAME_TO_CODE['normal']=0
    NAME_TO_CODE['bright']=1
    NAME_TO_CODE['dim']=2
    NAME_TO_CODE['blink']=5
    NAME_TO_CODE['overline']=53
    NAME_TO_CODE['reverse']=7
    NAME_TO_CODE['strike-through']=8
    NAME_TO_CODE['underline']=3

    NAME_TO_CODE['fg-black']=30
    NAME_TO_CODE['fg-blue']=34
    NAME_TO_CODE['fg-cyan']=36
    NAME_TO_CODE['fg-green']=32
    NAME_TO_CODE['fg-magenta']=35
    NAME_TO_CODE['fg-red']=31
    NAME_TO_CODE['fg-yellow']=33
    NAME_TO_CODE['fg-white']=37

    NAME_TO_CODE['bg-black']=40
    NAME_TO_CODE['bg-blue']=44
    NAME_TO_CODE['bg-cyan']=46
    NAME_TO_CODE['bg-green']=42
    NAME_TO_CODE['bg-magenta']=45
    NAME_TO_CODE['bg-red']=41
    NAME_TO_CODE['bg-yellow']=43
    NAME_TO_CODE['bg-white']=47

    separator=''

    for styleName in $styleList; do
        if [ "${NAME_TO_CODE[$styleName]}" == "" ]; then
            echo -e "\033[1;31mUnknown style: '$styleName\033[0m'"
            exit 1
        fi

        styleCodes="${styleCodes}${separator}${NAME_TO_CODE[$styleName]}"
        separator=';'
    done
    echo "\033[${styleCodes}m"
}

#-------------------------------------------------------------------------------
# Parse the command line args and run the show
#
# Args:
#      $1 - First command line arg
#      $2 - Second command line arg
#      etc
#------------------------------------------------------------------------------
function main()
{
    # Figure out if we're going to use test data
    useTestValues=false

    if [ "$1" == "--test" ]; then
        useTestValues=true
    fi

    # Early exit if we're not in a git-tracked folder
    # Don't use `git status` because it can be expensive
    if ! $useTestValues; then
        git rev-list HEAD --max-count=1 > /dev/null 2>&1
        if [ "$?" != "0" ]; then
            # There are no refs, but this could also correspond to the state
            # immediately after `git init`. So check for that by using
            # `git status` (which isn't expensive in this scenario)
            git status > /dev/null 2>&1
            if [ "$?" != "0" ]; then
                exit
            fi
        fi
    fi

    # Do everything
    doit $useTestValues
}

#-------------------------------------------------------------------------------
main "$@"
