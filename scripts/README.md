README
------

This describes the conversion pipeline

Requirements
------------

-   Docker
-   the Docker image built from the Dockerfile in this repository which 
    includes the bioformats2raw and raw2ometiff utilities.
-   a Python virtual environment with awscli installed for the S3 upload

Note: the bioformat2raw feature allowing to export only the first series of
the source image is required for this pipeline.

Sources
-------

As the original files are Imaris IMS files, one per timepoint, a directory
called 20201215-patterns contains symlinks to the original data and pattern
files allowing to combine the individual cycles into a timelapse
representation.

Pipeline
--------

The conversion pipeline consists of three steps:

- convert the original IMS files into Zarr and OME-TIFF
- upload the Zarr files to S3
- copy the OME-TIFF files to NFS

The `convert.sh` script allows to do the conversion of one embryo dataset. It
executes `bioformat2raw` then `raw2ometiff` against the pattern file
describing the sequencing acquisition and the two standalone IMS files. Data is
generated in 2 folders `YYYYMMDD-zarr` and `YYYYMMDD-ometiff` where
`YYYYMMDD` is the date.

Alternatively, this can be executed using GNU `parallel` as follows:
Run the conversion in parallel. Tested with 4 embryos and the conversion lasted
for ~6h

```
parallel --joblog $(date '+%Y%m%d')_convert.log --results $(date '+%Y%m%d')_convert ./convert.sh ::: embryo01 embryo02 embryo03 embryo04
```

The parallel conversion was tested against four embryos and takes ~6h.

```
Seq     Host    Starttime       JobRuntime      Send    Receive Exitval Signal  Command
1       :       1608031486.525   15924.329      0       126441605       0       0       ./convert.sh embryo01
2       :       1608031486.528   18674.967      0       162863159       0       0       ./convert.sh embryo02
3       :       1608031486.531   20964.452      0       162886029       0       0       ./convert.sh embryo03
4       :       1608031486.534   21092.129      0       162885643       0       0       ./convert.sh embryo04
```

Te `s3-upload.sh` script renames the `0` group under `data.zarr` for each of
the 3 Zarr datasets generated for an embryo and uploads it to the S3 `idr-upload` bucket.

As above, the S3 upload can be executed in GNU `parallel` although the transfer
rates will be limited.

```
parallel --joblog $(date '+%Y%m%d')_upload.log --results $(date '+%Y%m%d')_upload ./s3-upload.sh ::: embryo01 embryo02 embryo03 embryo04
```

The command above executed against 3 embryos gave the following times:

```
Seq     Host    Starttime       JobRuntime      Send    Receive Exitval Signal  Command
3       :       1608124765.920    2175.603      0       89010431        0       0       DATE=20201215 ./s3-upload.sh embryo04
2       :       1608124765.916    4170.486      0       88970953        0       0       DATE=20201215 ./s3-upload.sh embryo03
1       :       1608124765.913    4452.721      0       89148788        0       0       DATE=20201215 ./s3-upload.sh embryo02
````

Remove the Zarr folder to avoid the data duplication on NFS and S3:

```
rm -rf /data/idr0101-payne-insitugenomeseq/*-zarr/
```

The `./idrftp-aspera.sh` script can be used to copy the converted OME-TIFF to NFS:

```
sudo ASPERA_SCP_PASS=<PASS> ./idrftp-aspera.sh /data/idr0101-payne-insitugenomeseq/
```

Remove the OME-TIFF folder to start the next conversion

```
rm -rf /data/idr0101-payne-insitugenomeseq/*-ometiff/
```
