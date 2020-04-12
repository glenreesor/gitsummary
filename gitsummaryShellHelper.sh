#!/bin/bash

git status > /dev/null 2>&1
if [ "$?" != "0" ]; then
    exit
fi

showNumStashes=true        ; symbolStashes=''
showNumStage=true          ; symbolStage=''
showNumWorkDir=true        ; symbolWorkDir=''
showNumUnmerged=true       ; symbolUnmerged=''
showNumUntracked=true      ; symbolUntracked=''

showNumAheadRemote=true    ; symbolAheadRemote='+'
showNumBehindRemote=true   ; symbolBehindRemote='-'

showNumAheadTarget=true    ; symbolAheadTarget='+'
showNumBehindTarget=true   ; symbolBehindTarget='-'

showTargetName=true        ; symbolTarget=''

showZeros=false

# ANSI Escape Sequences Reference
#   Bold   : 1
#
#   Black  : 30    Bright: 90
#   Blue   : 34    Bright: 94
#   Cyan   : 36    Bright: 96
#   Green  : 32    Bright: 92
#   Magenta: 35    Bright: 95
#   Red    : 31    Bright: 91
#   Yellow : 33    Bright: 93
#   White  : 37    Bright: 97

colorBranchName='\033[1m'
colorRemoteAhead='\033[96m'
colorRemoteBehind='\033[96m'
colorStage='\033[92m'
colorStashes='\033[32m'
colorTargetAhead=''
colorTargetBehind=''
colorTargetName=''
colorUnmerged='\033[91m'
colorUntracked='\033[36m'
colorWorkDir='\033[95m'

#-------------------------------------------------------------------------------
colorNormal='\033[0m'

gitSummaryOutput=( $(gitsummary.py --shellPromptHelper) )

numStashes=${gitSummaryOutput[0]}
numStage=${gitSummaryOutput[1]}
numWorkDir=${gitSummaryOutput[2]}
numUnmerged=${gitSummaryOutput[3]}
numUntracked=${gitSummaryOutput[4]}
branchName=${gitSummaryOutput[5]}
numAheadRemote=${gitSummaryOutput[6]}
numBehindRemote=${gitSummaryOutput[7]}
numAheadTarget=${gitSummaryOutput[8]}
numBehindTarget=${gitSummaryOutput[9]}
targetName=${gitSummaryOutput[10]}

output="${colorBranchName}${branchName}${colorNormal}"

if $showNumStashes && ( $showZeros || [ $numStashes != 0 ] ) ; then
    output="${output} ${colorStashes}${symbolStashes}${numStashes}${colorNormal}"
fi


if $showNumStage && ( $showZeros || [ $numStage != 0  ] ); then
    output="${output} ${colorStage}${symbolStage}${numStage}${colorNormal}"
fi

if $showNumWorkDir && ( $showZeros || [ $numWorkDir != 0 ] ); then
    output="${output} ${colorWorkDir}${symbolWorkDir}${numWorkDir}${colorNormal}"
fi

if $showNumUnmerged && ( $showZeros || [ $numUnmerged != 0 ] ); then
    output="${output} ${colorUnmerged}${symbolUnmerged}${numUnmerged}${colorNormal}"
fi

if $showNumUntracked && ( $showZeros || [ $numUntracked != 0 ] ); then
    output="${output} ${colorUntracked}${symbolUntracked}${numUntracked}${colorNormal}"
fi

if $showNumAheadRemote && ( $showZeros || [ \( $numAheadRemote != 0 -a $numAheadRemote != "_" \) ] ); then
    output="${output} ${colorRemoteAhead}${symbolAheadRemote}${numAheadRemote}${colorNormal}"
fi

if $showNumBehindRemote && ( $showZeros || [ \( $numBehindRemote != 0 -a $numBehindRemote != "_" \) ] ); then
    output="${output} ${colorRemoteBehind}${symbolBehindRemote}${numBehindRemote}${colorNormal}"
fi

if $showNumAheadTarget && ( $showZeros || [ $numAheadTarget != 0 ] ); then
    output="${output} ${colorTargetAhead}${symbolAheadTarget}${numAheadTarget}${colorNormal}"
fi

if $showNumBehindTarget && ( $showZeros || [ $numBehindTarget != 0 ] ); then
    output="${output} ${colorTargetBehind}${symbolBehindTarget}${numBehindTarget}${colorNormal}"
fi

if $showTargetName && [ $targetName != "_" ]; then
    output="${output} ${colorTargetName}${symbolTarget}${targetName}${colorNormal}"
fi

echo -e $output
