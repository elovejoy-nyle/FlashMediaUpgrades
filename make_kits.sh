#!/bin/bash
# Notes:
# What you need for this script to run nice:
# Your Series README.pdf in the same dir
# USB_Media dir with *.ZNX and configured hgauto.ini 
# SD_Card dir with *.zld in FCDATA01/PROGRAM and configured autoexec.ini in FCDATA01
# A dir named ALLUNIT_RECIPES with all unit recipies 
#
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



#for i in `ls ALLUNIT_RECIPES/`
#do
#echo $i
#mkdir -p OUTPUT/$i"_upgrade_kit"
#cp README-INSTRUCTIONS.pdf OUTPUT/$i"_upgrade_kit"
#cp -R USB_Media/ OUTPUT/$i"_upgrade_kit"
#cp -R SD_Card/ OUTPUT/$i"_upgrade_kit"
#cp -R ALLUNIT_RECIPES/$i OUTPUT/$i"_upgrade_kit"
#done

