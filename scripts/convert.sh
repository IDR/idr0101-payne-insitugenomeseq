#!/usr/bin/bash


today=$(date '+%Y%m%d')
function bf2raw {
    sudo docker run --rm -u 11615:1030 -v /data/:/data -v /nfs:/nfs --entrypoint /opt/bioformats2raw/bin/bioformats2raw idr0101 /data/idr0101-payne-insitugenomeseq/20201215-patterns/$1 /data/idr0101-payne-insitugenomeseq/${today}-zarr/$2 --series 0 --max_workers 1 --file_type zarr
}

function raw2ometiff {
    sudo docker run --rm -u 11615:1030 -v /data/:/data -v /nfs:/nfs --entrypoint /opt/raw2ometiff/bin/raw2ometiff idr0101 /data/idr0101-payne-insitugenomeseq/${today}-zarr/$1 /data/idr0101-payne-insitugenomeseq/${today}-ometiff/$2
}

mkdir -p /data/idr0101-payne-insitugenomeseq/${today}-zarr
mkdir -p /data/idr0101-payne-insitugenomeseq/${today}-ometiff

bf2raw $1/$1.pattern $1
raw2ometiff $1 $1.ome.tiff

bf2raw $1/$1_hyb.ims $1_hyb
raw2ometiff $1_hyb $1_hyb.ome.tiff

bf2raw $1/$1_stain.ims $1_stain
raw2ometiff $1_stain $1_stain.ome.tiff
