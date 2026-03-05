#.bin/bash

find . -type d -name "src" -exec bash -c 'find "$1" -name "**/*.pdf" -exec mv -t "$1" {} +' _ {} \;

echo ============== Done moving ======================

rm -v **/*.aux
rm -v **/*.bbl
rm -v **/*.blg
rm -v **/*.fdb_latexmk
rm -v **/*.fls
rm -v **/*.run.xml
rm -v **/*.synctex.gz
rm -v **/*.toc
rm -v **/*.lof
rm -v **/*.lolistedequation
rm -v **/*.lot
rm -v **/*-blx.bib
rm -v **/*.log
rm -v **/*.out
rm -v **/*.nav
rm -v **/*.snm
