#gitsummary#

Summarize git file and branches status

##Description##
Use `gitsummary` to see a summary of your git repository:

* All staged, modified, and untracked files
* All stashes
* For each local branch:
   * All commits that differ between local and origin
   * All commits that differ between local and either your `dev` or `master`
     (it looks for `dev` first, and falls back to `master`)

##Example - All Branches##
![](https://raw.githubusercontent.com/glenreesor/gitsummary/master/doc/output.default.png)

`gitsummary` shows a snapshot of your git repository. This screenshot shows:

* local `dev` has commits that haven't been merged to local `master`
* local `feature-Make-Awesome`:
   * has two commits that haven't been pushed to origin
   * has some commits that haven't been merged to local `dev`
   * is missing some commits from local `dev`

* local `feature-Make-Cross-Platform` is in sync with its origin, and
  local `dev`

##Example - Current Branch##
![](https://raw.githubusercontent.com/glenreesor/gitsummary/master/doc/output.currentBranch.png)

`gitsummary --current` shows complete information about how the current
branch differs from the origin (left column) and from local `dev` (or `master`
if no `dev`) (right column)

This screenshot shows local `feature-Make-Awesome`:

   * has two commits that haven't been pushed to origin
   * is missing one commit from local `dev`
   * has two commits that haven't been merged to local `dev`

##Usage##
```
gitsummary [options]
    --branch NAME    - Show only the specified branch. Implies --long
    --compareto NAME - Compare to the specified local branch rather
                       than dev/master
    --current        - Show only the current branch. Implies --long
    --long           - Also show commits that differ between branch
                       and dev (or master if dev does't exist)
    --short          - Do not show commits that differ between branch and
                       dev (or master if dev does't exist)
                       This is the default when --current is not specified
```

##Requirements##
python3

##Installation##
Easy! Just copy `gitsummary` to a folder in your path, and you're set!
