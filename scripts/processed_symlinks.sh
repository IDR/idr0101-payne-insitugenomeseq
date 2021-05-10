
# This script creates symlinks from processed tif stacks in 20210421-ftp
# and a corresponding pattern file to import as 5D images

# Usage:
# $ cd idr0101-payne-insitugenomeseq/
# $ ../path/to/idr0101-payne-insitugenomeseq/scripts/processed_symlinks.sh

# Create a new directory for all the pattern files
pattern_dir="20210421-processed"
mkdir $pattern_dir
cd $pattern_dir

filePaths="processed-filePaths.tsv"
curr_dir=$(pwd)

# Find all the 'cell00n' directories (these contain the .tif images)
files=$(find ../20210421-ftp -maxdepth 5 -mindepth 1 -type d -name "cell[0-9]*")
echo $files

# For each 'cell00n' dir....
for f in $files;
    do
    echo "-------------------"
    echo $f
    # e.g. ../20210421-ftp/processed/embryo/embryo01/cell001
    # we want dir like embryo/embryo01/cell001
    basepth="../20210421-ftp/processed/"
    pattern_path=${f/$basepth/""}
    # e.g. embryo/embryo01/cell001
    echo $pattern_path
    mkdir -p $pattern_path
    cd $pattern_path
    # e.g. pgp1/fov019/cell003
    # or embryo/embryo01/cell001

    # use current directory name for the imported image name
    imgname=$(basename $PWD)
    # imgname=${PWD##*/} 

    # Create /pattern/ directory for all pattern files
    # mkdir -p "pattern"
    # cd "pattern"

    c=1
    t=1

    # For each Z-stack tif, symlink from name like cell_t01_c01.tif
    filepath=$(printf "../../../$f/cy%02d_ch%02d.tif" $t $c)
    echo $filepath
    pwd
    # e.g. ../../../../20210421-ftp/processed/embryo/embryo01/cell001/cy01_ch01.tif

    while [ -f $filepath ]
    do
        symlink=$(printf "%s_t%02d_c%02d.tif" $imgname $t $c)

        # relative symlink up one dir
        ln -s $filepath $symlink

        if [[ $c -gt 3 ]]
        then
        c=1
        t=$[$t+1]
        else
        c=$[$c+1]
        fi

        filepath=$(printf "../../../$f/cy%02d_ch%02d.tif" $t $c)
    done

    # Handle other 'stain' files - across ALL timepoints
    # For each time-point, link to the same file as a new channel

    # stain_cenpa.tif
    # stain_dapi.tif
    # stain_hyb.tif
    # stain_lamin.tif

    c=5
    for stain in stain_cenpa.tif stain_dapi.tif stain_hyb.tif stain_lamin.tif
    do
        filepath=$(printf "../../../$f/$stain")
        echo $filepath
        if [ -f $filepath ]
        then
            echo "linking stain..."
            for ((time=1; time < $t; time++))
            do
                symlink=$(printf "%s_t%02d_c%02d.tif" $imgname $time $c) 
                ln -s $filepath $symlink
            done
            c=$[$c+1]
        fi
    done

    # Create the pattern file in e.g. 20210421-processed/embryo/embryo01/cell001
    t=$[$t-1]
    c=$[$c-1]
    echo "${imgname}_t<01-$t>_c<01-0$c>.tif" > $imgname.pattern

    # current dir is e.g. processed/embryo/embryo01/cell0001/
    # Go up 1 dir to get the container name
    cd ../
    dsname=$(basename $PWD)
    echo $dsname
    cellnumber=$(echo $dsname | tr -dc '0-9')
    # e.g "01"
    echo $cellnumber

    # Add pattern file to the filePaths.tsv
    # if dsname is embryo01 Dataset is 'Embryo_01'
    projectname="idr0101-payne-insitugenomeseq/experimentB/"
    datasetname=$(print "Embryo_%s" $cellnumber)

    # if dsname is fov001 Dataset is 'Fibroblasts_01'
    if [[ $dsname == *"fov"* ]]; then
        projectname="idr0101-payne-insitugenomeseq/experimentA/"
        datasetname=$(print "Fibroblasts_%s" $cellnumber)
    fi

    # remove first 2 chars './' from $f
    f=$(echo $f | cut -c3-)
    echo $f

    # Add row to the filePaths.tsv
    echo "Project:name:${projectname}Dataset:name:${datasetname}	/uod/idr/filesets/idr0101-payne-insitugenomeseq/$pattern_dir/$pattern_path/$imgname.pattern	${imgname}_processed" >> $curr_dir/$filePaths

# back to where we started so that the next cd $f works
cd $curr_dir
done