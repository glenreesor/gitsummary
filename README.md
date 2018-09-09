# gitsummary

A better `git status`
- stashes
- file statuses
- branch list
    - number of commits ahead/behind remote and merge target

All nicely formatted with color.

## Example
![](https://raw.githubusercontent.com/glenreesor/gitsummary/master/doc/output.default.png)

In addition to the usual stashes and file statuses, this output is showing the
following branch information:

- `master`
    - In sync with its remote branch
    - Has no merge target
- `dev`
    - In sync with its remote branch
    - 3 commits ahead of its merge target (`master`)
- `feature-make-awesome`
    - Has no remote branch
    - 2 commits behind its merge target (`dev`)
- `feature-make-faster`
    - 6 commits ahead of its remote
    - 7 commits ahead of its merge target (`dev`)
- `hf-fix-bad-bug`
    - Has no remote branch
    - 1 commit ahead of its merge target (`master`)

## What is a 'Merge Target'?
A merge target is the branch that `gitsummary` is expecting a particular branch
to be merged into.

The algorithm for determining merge targets is currently hard coded, but will
be configurable in a future version.

Branch Name Pattern | Merge Target | Comments
------------------- | ------------ | --------
master              |   [None]     |
dev                 |   master     | No target if master does not exist
hf*                 |   master     | No target if master does not exist. ('hf' is an abbreviation for 'hotfix')
*                   |   dev        |

(See below if you want to change `gitsummary` for your own branch merge targets.)

## Usage
```
Usage:
    /gitsummary.py [--custom [options]] | --help

Print a summary of the current git repository's status:
    - stashes, staged files, modified files, untracked files,
    - list of local branches, including the following for each:
          - number of commits ahead/behind its target branch
          - number of commits ahead/behind its remote branch
          - the name of its target branch
Flags:
    --custom [options]
        - Show only the specified sections of output
        - Valid section names are:
          'stashes', 'staged', 'modified', 'untracked', 'branch-all',
          'branch-current'

    --help
        - Show this output

    --version
        - Show current version
```

## Requirements
python3

## Installation
Easy! Just copy [gitsummary.py](https://raw.githubusercontent.com/glenreesor/gitsummary/master/gitsummary.py) to a folder in your path, and you're set!

## Customizing Branch Merge Targets
The logic for mapping branches to their merge targets is in
`gitsummary.py/utilGetTargetBranch()`,
and the corresponding tests are in `testGitsummary.py/Test_utilGetTargetBranch`.

The code is straight forward. For example, if you use `develop` instead of `dev`
and `hotfix` instead of `hf`, the body of `utilGetTargetBrahch()` would be:

```
    if branch == 'master':
        targetBranch = ''
    elif branch == 'develop':
        targetBranch = 'master' if 'master' in localBranches else ''
    elif branch.startswith('hotfix'):
        targetBranch = 'master' if 'master' in localBranches else ''
    else:
        targetBranch = 'develop' if 'develop' in localBranches else ''

    return targetBranch
```
