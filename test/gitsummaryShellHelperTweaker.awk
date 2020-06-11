# Copyright 2020 Glen Reesor
#
# This file is part of gitsummary.
#
# Gitsummary is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3,
# as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# ------------------------------------------------------------------------------
# Use this awk script to modify the configurable things in
# gitsummaryShellHelper.sh, thus making it easier to test
#
# Example:
#   awk -v showNum=num -v showString=yes -f gitsummaryShellHelperTweaker.awk ../gitsummaryShellHelper.sh | bash
#
#       - This will perform the following replacements and then run the
#         resulting script:
#           - change all 'show' values for numeric quantities (like numStashes)
#             to 'num'
#           - change all 'show' values for string quantities (like branchName)
#             to 'yes'
#           - first 'prefix' --> '_A_', second 'prefix' --> '_B_', etc.
#           - first 'suffix' --> '_a_', second 'prefix' --> '_b_', etc.
#           - first 'styles' string --> 'bg-black bright fg-blue',
#             second 'styles' string -->  another (unique) string (see below), etc
#           - separator -->  '|' and corresponding styles --> 'bg-green fg-yellow'
#           - test mode is turned on so every quantity will have a value
# ------------------------------------------------------------------------------

BEGIN {
    COL_SHOW = 1
    COL_PREFIX = 3
    COL_SUFFIX = 5
    COL_STYLES = 7

    PREFIXES="ABCDEFGHIJK"
    SUFFIXES="abcdefghijk"

    # Start at 1 for consistency with substr() (which is 1-based) which is used
    # for prefixes and suffixes
    STYLES[1] = "bg-black bright fg-blue"
    STYLES[2] = "bg-black bright fg-cyan"
    STYLES[3] = "bg-black bright fg-green"
    STYLES[4] = "bg-black bright fg-magenta"
    STYLES[5] = "bg-black bright fg-red"
    STYLES[6] = "bg-black bright fg-yellow"
    STYLES[7] = "bg-black bright fg-white"
    STYLES[8] = "bg-white fg-black"
    STYLES[9] = "bg-white fg-magenta"
    STYLES[10] = "bg-white fg-red"
    STYLES[11] = "bg-white fg-blue"

    prefixIndex = 1
    suffixIndex = 1
    stylesIndex = 1
}

{
    if ($1 ~ "^show.'") {
        #-----------------------------------------------------------------------
        # If this is a line with all the config, starting with 'show', then
        # we're going to replace the show, prefix, suffix, and styles values
        #-----------------------------------------------------------------------

        # Show
        if ($COl_SHOW ~ "(branchName)|(targetBranch)") {
            sub(/=.*$/, "=" showString, $COL_SHOW)
        } else {
            sub(/=.*$/, "=" showNum, $COL_SHOW)
        }
        print $COL_SHOW

        # Prefix
        sub(\
            /=.*$/,\
            "='_" substr(PREFIXES, prefixIndex, 1) "_'",\
            $COL_PREFIX\
        )
        print $COL_PREFIX
        prefixIndex += 1

        # Suffix
        sub(\
            /=.*$/,\
            "='_" substr(SUFFIXES, suffixIndex, 1) "_'",\
            $COL_SUFFIX\
        )
        print $COL_SUFFIX
        suffixIndex += 1

        # Styles
        sub(\
            /=.*$/,\
            "='" STYLES[stylesIndex] "'",\
            $COL_STYLES\
        )
        print $COL_STYLES
        stylesIndex += 1

    } else if ($1 ~ "^separatorString=") {
        #-----------------------------------------------------------------------
        # Change the separator string and styles
        #-----------------------------------------------------------------------
        print "separatorString='|'; separatorStyles='bg-green fg-yellow'"

    } else if ($0 ~ "^ *local useTestValues=") {
        #-----------------------------------------------------------------------
        # Turn on test mode
        #-----------------------------------------------------------------------
        print "local useTestValues=true"

    } else {
        #-----------------------------------------------------------------------
        # Not a line we want to change, so print it unchanged
        #-----------------------------------------------------------------------
        print $0
    }
}
