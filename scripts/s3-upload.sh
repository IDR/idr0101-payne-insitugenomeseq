#!/usr/bin/bash

DATE=${DATE:-$(date '+%Y%m%d')}

function upload {
    rm /data/idr0101-payne-insitugenomeseq/${DATE}-zarr/$1/data.zarr/.zattrs
    rm /data/idr0101-payne-insitugenomeseq/${DATE}-zarr/$1/data.zarr/.zgroup
    mv /data/idr0101-payne-insitugenomeseq/${DATE}-zarr/$1/data.zarr/0 /data/idr0101-payne-insitugenomeseq/${DATE}-zarr/$1/data.zarr/$1.zarr
    aws --profile idr-upload --endpoint-url=https://s3.embassy.ebi.ac.uk s3 cp --recursive /data/idr0101-payne-insitugenomeseq/${DATE}-zarr/$1/data.zarr/ s3://idr-upload/idr0101/
}

upload $1
upload $1_hyb
upload $1_stain
