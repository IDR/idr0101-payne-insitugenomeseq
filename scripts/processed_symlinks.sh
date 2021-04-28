
# Usage
# $ cd embryo_01/cell01/
# $ ../path/to/processed_symlinks.sh

# Create /pattern/ directory for all pattern files
mkdir -p "pattern"
cd "pattern"

c=1
t=1

# For each Z-stack tif, symlink from name like cell001_t01_c01.tif
filepath=$(printf "../cy%02d_ch%02d.tif" $t $c)
echo $filepath

while [ -f $filepath ]
do
    symlink=$(printf "cell001_t%02d_c%02d.tif" $t $c)
    echo $filepath
    echo $symlink

    # relative symlink up one dir
    ln -s $filepath $symlink

    if [[ $c -gt 3 ]]
    then
    c=1
    t=$[$t+1]
    else
    c=$[$c+1]
    fi

    filepath=$(printf "../cy%02d_ch%02d.tif" $t $c)
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
    for ((time=1; time < $t; time++))
    do
        echo "Handle $time timepoint $stain"
        symlink=$(printf "cell001_t%02d_c%02d.tif" $time $c)
        echo $symlink 
        ln -s ../$stain $symlink
    done
    c=$[$c+1]
done

# Create the pattern file
t=$[$t-1]
echo "cell001_t<01-$t>_c<01-08>.tif" > cell001.pattern
