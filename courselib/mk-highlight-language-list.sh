#!/bin/bash

# Create the highlight_language_classes.py file: lsit of all languages
# supported by highlight.js, which are allowed classes in even our most
# restricted HTML output.
#   ./mk-highlight-language-classes.sh > highlight_language_classes.py


TMPDIR=$(mktemp -d --suffix=.highlight)

cd $TMPDIR
git clone --depth=1 https://github.com/highlightjs/highlight.js.git

echo "# This file is generated by mk-highlight-language-list.sh."
echo "# Probably don't edit it by hand."
echo "LANG_CLASSES = ["
for LANG in `ls -1 highlight.js/src/languages | sed s/.js$//`
do
  echo "    'lang-$LANG',"
done
echo "]"

rm -rf $TMPDIR
