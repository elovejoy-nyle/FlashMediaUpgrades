#!/bin/bash

for unit in ALLUNIT_RECIPES/*; do
    name=$(basename "$unit")
    outdir="OUTPUT/${name}_upgrade_kit"

    mkdir -p "$outdir"
    cp README-INSTRUCTIONS.pdf "$outdir/"
    cp -R USB_Media/ "$outdir/"
    cp -R SD_Card/ "$outdir/"
    cp -R "$unit" "$outdir/"
done


# Should make a script to generate the SD_Card and USB_Media Folders

## COMPRESS ALL
cd OUTPUT
for dir in */;
do
i="${dir%/}"
#echo $i
zip -r "${i}.zip" "$i" 
done

# directory structure 3 levels deep
: <<'END_COMMENT'
SD_Card/
└── FCDATA01
    ├── DATALOG
    ├── PROGRAM
    │   └── R513a1403.zld
    ├── RECIPE
    ├── TLS
    ├── TRACE
    └── autoexec.ini
USB_Media/
├── R513a1403.ZNX
└── hgauto.ini
ALLUNIT_RECIPES/
├── C125W_MP
│   └── FCDATA01
│       └── RECIPE
├── C125W_SP
│   └── FCDATA01
│       └── RECIPE
├── C185A_MP_CWP
│   └── FCDATA01
│       └── RECIPE
├── C185A_SP_CWP
│   └── FCDATA01
│       └── RECIPE
├── C185W_MP
│   └── FCDATA01
│       └── RECIPE
├── C185W_SP
│   └── FCDATA01
│       └── RECIPE
├── C250A_MP
│   └── FCDATA01
│       └── RECIPE
├── C250A_MP_CWP
│   └── FCDATA01
│       └── RECIPE
├── C250A_SP
│   └── FCDATA01
│       └── RECIPE
├── C250A_SP_CWP
│   └── FCDATA01
│       └── RECIPE
├── C270WM_MP
│   └── FCDATA01
│       └── RECIPE
├── C270WM_SP
│   └── FCDATA01
│       └── RECIPE
├── C90A_MP_CWP
│   └── FCDATA01
│       └── RECIPE
├── C90A_SP_CWP
│   └── FCDATA01
│       └── RECIPE
└── HPB
    └── FCDATA01
        └── RECIPE
END_COMMENT

# Notes:
# What you need for this script to run nice:
# Your Series README.pdf in the same dir
# USB_Media dir with *.ZNX and configured hgauto.ini 
# SD_Card dir with *.zld in FCDATA01/PROGRAM and configured autoexec.ini in FCDATA01
# A dir named ALLUNIT_RECIPES with all unit recipies 
#

#for i in `ls ALLUNIT_RECIPES/`
#do
#echo $i
#mkdir -p OUTPUT/$i"_upgrade_kit"
#cp README-INSTRUCTIONS.pdf OUTPUT/$i"_upgrade_kit"
#cp -R USB_Media/ OUTPUT/$i"_upgrade_kit"
#cp -R SD_Card/ OUTPUT/$i"_upgrade_kit"
#cp -R ALLUNIT_RECIPES/$i OUTPUT/$i"_upgrade_kit"
#done

