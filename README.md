# gitsummary

Summarize git repository and branch statuses

## Description
Use `gitsummary` to see a summary of your git repository:

* All stashes
* All staged, modified, and untracked files
* For each local branch:
   * Number of commits that differ between local and remote
   * Number of commits that differ between local and `dev`
     (`dev` will be compared to `master`)

Use `gitsummary branch` to see a summary of a particular branch:

* All stashes (regardless of what commit they're associated with)
* All staged, modified, and untracked files
* One-line descriptions for all commits that differ between local and remote
* Number of commits that differ between local and `dev`
(`dev` will be compared to `master`)


## Example - All Branches
![](https://raw.githubusercontent.com/glenreesor/gitsummary/master/doc/output.default.png)

`gitsummary` shows a snapshot of your git repository. This screenshot shows:

* There is one stash on commit `060c412`
* A list of staged, modified, and untracked files
* local `dev` has 2 commits that haven't been merged to local `master`
* local `feature-Make-Awesome`:
   * has 2 commits that haven't been pushed to its remote
   * has 2 commits that haven't been merged to local `dev`
   * is missing 1 commit from local `dev`

* local `feature-Make-Cross-Platform` does not have a corresponding remote,
 and is up to date with local `dev`

## Example - Current Branch
![](https://raw.githubusercontent.com/glenreesor/gitsummary/master/doc/output.currentBranch.png)

`gitsummary branch` shows complete information about the current branch

This screenshot shows local `feature-Make-Awesome`:

   * has two commits that haven't been pushed to origin
   (`Finish doing something awesome` and `Do something awesome - Part 1`)
   * has 2 commits that haven't been merged to local its 'target' branch
   (`dev`)
   * is missing 1 commit from its target branch (`dev`)

The specific commits relative to its target can be shown using `--target`

## Usage
```
Usage: gitsummary [repo | branch] [options]
    repo   - Show a summary of the current git repository, including:
                 - Stashes and staged/modified/untracked files
                 - All local branches
                 - For each branch, the number of commits differing from its
                   remote and merge target
                       - Commits Ahead: +n
                       - Commits Behind: -n
                       - No remote or merge target signified by blanks
           - This is the default if neither 'repo' nor 'branch' is specified.

             Options:
                 --n - Format output for a screen width of n characters

    branch - Show a summary of the current branch, including remote name,
             merge target name, commits differing from the remote, and
             number of commits differing from merge target.

           - Commits listed under "Local Branch" exist in the local branch but
             not the remote. Commits listed under "Remote" exist in the remote
             but not the local branch.
             Options:
                 BRANCH   - Any argument that doesn't start with -- is treated
                            as a branch to use for the comparison, instead of
                            the current branch
                 --hash   - Show commit hashes as well as descriptions
                 --target - Show the commits differing from the merge target
                            instead of just the number
                 --n      - Format output for a screen width of n characters
```

## Requirements
python3

## Installation
Easy! Just copy [gitsummary](https://raw.githubusercontent.com/glenreesor/gitsummary/master/gitsummary) to a folder in your path, and you're set!
