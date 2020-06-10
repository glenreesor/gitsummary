#!/bin/bash

# Simple script to demonstrate `gmon` in action

# Whether to use gitsummaryShellHelper.sh to create the fake shell prompt
USE_SHELL_PROMPT_HELPER=true

#-------------------------------------------------------------------------------
# Do everything
#
# Args: None
#-------------------------------------------------------------------------------
function doit()
{
    #--------------------------------------------------------------------------
    # Easier to remember branches and filenames
    #--------------------------------------------------------------------------
    BRANCH1='feature-endor-shield-generator'
    BRANCH2='feature-ds2-defences-phase2'

    FILE1='controller-turbolaser.f77'
    FILE2='view-model-ion-cannons.f77'

    #--------------------------------------------------------------------------
    # Set up a local/remote pair prior to scripting with some branches, where
    # local will end up with two branches behind master.
    #
    # Put it all in /tmp to be safe
    #--------------------------------------------------------------------------
    workFolder=$(mktemp --directory /tmp/gmon-demo.XXX)
    cd $workFolder

    # Create remote with some branches
    # master
    git init remote
    cd $workFolder/remote

    touch .gitignore
    git add .gitignore
    git commit -m 'my message'

    modifyAndCommitFile $FILE1
    modifyAndCommitFile $FILE2

    # Make develop a few commits ahead of master
    git checkout -b develop
    modifyAndCommitFile $FILE1
    modifyAndCommitFile $FILE1
    modifyAndCommitFile $FILE1

    # Make branch1 a few commits ahead of develop
    git checkout -b $BRANCH1
    modifyAndCommitFile $FILE1
    modifyAndCommitFile $FILE2

    # Make branch2 a few commits ahead of develop
    git checkout -b $BRANCH2 develop
    modifyAndCommitFile $FILE1
    modifyAndCommitFile $FILE1
    modifyAndCommitFile $FILE1
    modifyAndCommitFile $FILE1
    modifyAndCommitFile $FILE2

    # Clone to create local repo and checkout all branches so they'll show up in
    # gitsummary output
    cd $workFolder
    git clone remote local
    cd $workFolder/local

    git checkout master
    git checkout develop
    git checkout $BRANCH1
    git checkout $BRANCH2

    # Back to remote so we can make local behind by some commits
    cd $workFolder/remote

    # First on BRANCH2
    modifyAndCommitFile $FILE1
    modifyAndCommitFile $FILE1
    modifyAndCommitFile $FILE1
    modifyAndCommitFile $FILE1

    # And now on BRANCH1
    git checkout $BRANCH1
    modifyAndCommitFile $FILE2
    modifyAndCommitFile $FILE2

    # And finally back to local so we can start the demo
    cd $workFolder/local

    # Delay so we see if there were any errors ^^
    echo
    echo
    echo "git repo: $workFolder"
    echo
    echo "Press Enter to clear screen then again to start the demo"

    read

    clear

    #--------------------------------------------------------------------------
    # Start of things to be visible
    #--------------------------------------------------------------------------
    read

    echo -n "$(getShellPrompt)"

    # Start gmon
    p  1 2 "# Better use gmon so I don't screw up again."
    p  1 0 "empireterm -baud 9600 -e gmon"
    terminology --background black.png --title='/home/darth/dev (2)' --geometry=80x13+0+395 -e "cd /tmp/$workFolder ; gmon" > /dev/null 2>&1 &
    p  0 0 ''
    sleep 3

    # Fetch and pull
    p  0 2 "# Wonder if my protege has made any progress with our defences."
    pe 1 0 true "git fetch"
    p  0 0 ''
    sleep 3

    p  0 2 "# Ooooh nice! He also got started on the shield generator :+1:"
    p  0 2 "# Or as The Big Guy likes to say, the Shield Genahrayta ¯\_(ツ)_/¯"
    p  0 2 "# Better pull in his changes."

    pe 1 0 false "git pull"
    p  0 0 ''
    sleep 2

    # Grab reference file
    p  0 2 "# Don't want to repeat our mistakes from last time ..."
    pe 1 0 false "mkdir reference"

    # Hack -- do this first so the prompt printed after `cp` below properly
    # shows the new file
    sleep 1
    touch reference/ds1-thermal-exhaust-port.cobol
    p  0 0  "cp ~tarkin/design/ds1-thermal-exhaust-port.cobol reference"
    p  0 0 ''
    sleep 2

    # Update .gitignore
    pe 0 0 false "echo reference >> .gitignore"
    pe 2 0 false "git add .gitignore"
    pe 2 0 true "git commit -m 'Ignore reference/ stuff'"
    p  0 0 ''
    sleep 2

    # Make other changes
    p  0 2 "# Can't believe he used the wrong volume formula :picard-facepalm:"
    pe 2 0 false "echo 'ds2Volume = 22/7 * r^2' >> $FILE2"
    pe 2 0 false "echo 'I rock!' > README.md"
    pe 2 0 false 'git add README.md'
    pe 2 0 false "git add $FILE2"
    pe 2 0 true "git commit -m 'Fix DS volume calculation'"
    p  0 0 ''
    sleep 2

    # Commit and push
    p  0 2 "# My work is done! Time to merge."
    pe 1 0 true "git push"
    p  0 0 ''
    sleep 2

    # Switch to develop and merge
    pe 0 0 true "git checkout develop"
    pe 2 0 true "git merge $BRANCH2 -m 'Merge latest and greatest'"
    pe 2 0 true "git push"
    p  2 0 ''
    p  2 0 '# What could go wrong?'

    #--------------------------------------------------------------------------
    # Wait for 'ENTER' then cleanup
    #--------------------------------------------------------------------------
    read
    cd /tmp
    rm -rf $workFolder
}

#-------------------------------------------------------------------------------
# Get a string to be used for the fake shell prompt.
#-------------------------------------------------------------------------------
function getShellPrompt()
{
    if $USE_SHELL_PROMPT_HELPER; then
        echo "$(gitsummaryShellHelper.sh) $ "
    else
        echo "$ "
    fi
}

#-------------------------------------------------------------------------------
# Modify and commit the specified file.
#
# Args:
#   $1 - The name of the file to operate on
#-------------------------------------------------------------------------------
function modifyAndCommitFile()
{
    local file=$1

    echo 'bla' >> $file
    git add $file
    git commit -m $file
}

#-------------------------------------------------------------------------------
# Print the specified text as if someone is typing it.
#
# Args:
#   $1 - The delay prior to printing the text (in seconds)
#   $2 - The delay between printing the text and showing the next simulated shell
#        prompt (in seconds)
#   #3 - The text to print
#-------------------------------------------------------------------------------
function p()
{
    local preDelay=$1
    local postDelay=$2
    local text=$3

    sleep $preDelay
    typing "$text"
    sleep $postDelay
    echo
    echo -n "$(getShellPrompt)"
}

#-------------------------------------------------------------------------------
# Print the specified text as if someone is typing it, then execute it.
#
# Args:
#   $1 - The delay prior to printing the text (in seconds)
#   $2 - The delay between printing the text and showing the next simulated shell
#        prompt (in seconds)
#   #3 - Whether to redirect output to /dev/null (bash boolean value)
#   #4 - The text to print and execute in a bash subshell
#-------------------------------------------------------------------------------
function pe()
{
    local preDelay=$1
    local postDelay=$2
    local redirectOutput=$3
    local text=$4

    sleep $preDelay
    typing "$text"

    echo
    if $redirectOutput; then
        bash -c "$text" > /dev/null 2>&1
    else
        bash -c "$text"
    fi
    sleep $postDelay
    echo -n "$(getShellPrompt)"
}

#-------------------------------------------------------------------------------
# Print the specified text as if someone is typing it. Text that doesn't start
# with '#' is highlighted using ANSI bright escape sequence.
#
# Args:
#   $1 - The text to "type"
#-------------------------------------------------------------------------------
function typing()
{
    local BASE_CHARS_PER_SECOND=75
    local stringToType=$1

    # Spit out the bright escape codes if required
    if [ "${stringToType:0:1}" != "#" ]; then
        echo -n -e '\033[0;1m'
    fi

    length=${#stringToType}
    index=0

    # Loop through the text one character at a time, inserting random delays
    # between words
    while [ $index -lt $length ]; do
        # Calculate the extra delay if we're between words
        if [ "${stringToType:$index:1}" == " " ]; then
            delayHundredthsSecond=$((1 + RANDOM %15))
        else
            delayHundredthsSecond=0
        fi

        bcCommand="scale = 4;"
        bcCommand="$bcCommand (1 / $BASE_CHARS_PER_SECOND) + $delayHundredthsSecond / 100"

        delay=$(echo "$bcCommand" | bc)
        sleep $delay

        echo -n "${stringToType:$index:1}"
        index=$((index + 1))
    done

    # Turn off bright mode
    if [ "${stringToType:0:1}" != "#" ]; then
        echo -n -e '\033[0;0m'
    fi
}

doit