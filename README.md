# gitsummary

A better `git status`:
- stashes
- file statuses
- branch list
    - number of commits ahead/behind remote tracking branch
    - number of commits ahead/behind merge target

All nicely formatted with color.

## Example
![test](/doc/example.png)

In addition to the usual stashes and file statuses, this output is showing the
following branch information:

- `master`
    - In sync with its remote tracking branch
    - Has no merge target
- `develop`
    - In sync with its remote tracking branch
    - 5 commits ahead of its merge target (`master`)
- `hotfix-stabilize-reactor-core`
    - In sync with its remote tracking branch
    - 2 commits ahead of its merge target (`master`)
- `feature-ds2-defences-phase2`
    - 3 commits ahead of its remote tracking branch
    - 4 commits ahead of its merge target (`develop`)
- `feature-endor-shield-generator`
    - 2 commits behind its remote tracking branch
    - 5 commits ahead and 3 commits behind its merge target (`develop`)

## What is a 'Merge Target'?
A merge target is the branch that `gitsummary` is expecting a particular branch
to be merged into.

For any given branch, the merge target is determined by the first regular
expression that matches that branch:

Regular Expression  | Merge Target
------------------- | ------------
^master$            |   [None]
^develop$           |   master
^hotfix-            |   master
^release-           |   master
[everything else]   |   develop

You can specify your own merge targets in a `.gitsummaryconfig` file
(see below).

## Usage
```
Usage:
    ./gitsummary.py [--custom [sections]] | --help | --helpconfig | --version

Print a summary of the current git repository's status:
    - stashes, stage changes, working directory changes, unmerged changes,
      untracked files,
    - list of local branches, including the following for each:
          - number of commits ahead/behind its target branch
          - number of commits ahead/behind its remote branch
          - the name of its target branch

Flags:
    --custom [sections]
        - Show only the specified sections of output, in the order specified
        - Valid section names are:
              stashes, stage, workdir, untracked, unmerged, branch-all,
              branch-current

    --help
        - Show this output

    --helpconfig
        - Show information for the gitsummary configuration file

    --version
        - Show current version
```

## Requirements
python3

## Installation
Easy! Just copy [gitsummary.py][gitsummaryScript]
to a folder in your path, and you're set!

## Configuration File
The gitsummary configuration file (`.gitsummaryconfig`) is a json-formatted
file used to specify:

- the order in which branches are printed
- branch names and their corresponding targets

Any line beginning with `//` (with optional preceding whitespace) is treated as
a comment and thus ignored.

The following is a sample configuration file that matches the built-in defaults:
```
{
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
        {
            "name"  : "^master$",
            "target": ""
        },
        {
            "name"  :"^develop$",
            "target": "master"
        },
        {
            "name"  :"^hotfix-.*",
            "target": "master"
        },
        {
            "name"  :"^release-.*",
            "target": "master"
        }
    ]
}
```
Gitsummary will look for `.gitsummaryconfig` in the current directory. If
not found, it will look in successive parent folders all the way up to the root
of the filesystem.

[gitsummaryScript]: https://raw.githubusercontent.com/glenreesor/gitsummary/master/gitsummary.py