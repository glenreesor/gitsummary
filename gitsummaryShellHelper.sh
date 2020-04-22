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
show['numStage']=num            ; prefix['numStage']=●          ; suffix['numStage']=''        ; styles['numStage']='bright fg-green'
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

#-------------------------------------------------------------------------------
# No changes should be required below here
#-------------------------------------------------------------------------------

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
        echo "Invalid value for $name: '$value'"
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
        echo "Invalid value for $name: '$value'"
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

    sep="$(getEscapeSequence "$separatorStyles")${separatorString}${COLOR_NORMAL}"

    # Loop through all possible quantities and create the appropriate output
    # (possibly empty if the corresponding 'show' value is 'no')
    for name in $outputInOrder; do

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

        # Print output as per showThis and showValue
        if $showThis; then
            if [ "$output" != "" ]; then
                output="${output}${sep}"
            fi

            output="${output}$(getEscapeSequence "${styles[$name]}")${prefix[$name]}"

            if $showValue; then
                output="${output}${values[$name]}${suffix[$name]}"
            fi

            output="${output}${COLOR_NORMAL}"
        fi
    done

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
    if ! $useTestValues; then
        git rev-list HEAD --max-count=1 > /dev/null 2>&1
        if [ "$?" != "0" ]; then
            exit
        fi
    fi

    # Do everything
    doit $useTestValues
}

#-------------------------------------------------------------------------------
main "$@"
