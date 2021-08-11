# idr0101-payne-insitugenomeseq


See scripts/README.md for processing steps.

Data outline below, with notes on how data was used:

```

20201128-ftp
    embryo/embryo[01-57]/embryo01_[cycle01-19/hyb/stain].ims
    pgp1f/pgp1f_[cycle01-19/hyb].nd2
20201204-ftp
    embryo[09_cycle02/embryo25_cycle04].ims 
20201215-ometiff
    embryo[01-04][_hyb/_stain/''].ome.tiff
20201215-patterns
    embryo[01-57]
        embryo01_[cycle01-19/hyb/stain].ims
        embryo01.pattern
20201216-ometiff
    embryo[05-07][_hyb/_stain/''].ome.tiff
20201217-ometiff
    embryo[09-12][_hyb/_stain/''].ome.tiff
20201217-patterns
    pgp1f_cycle[01-18].nd2
    pgp1f.pattern
20201219-ometiff
    embryo[13-20][_hyb/_stain/''].ome.tiff
20201220-ometiff
    embryo[21-28][_hyb/_stain/''].ome.tiff
20201221-ometiff
    embryo[29-32][_hyb/_stain/''].ome.tiff
20201222-ometiff
    embryo[33-40][_hyb/_stain/''].ome.tiff
20201223-ometiff
    embryo[41-48][_hyb/_stain/''].ome.tiff
20201224-ometiff
    embryo[49-57][_hyb/_stain/''].ome.tiff
20210127-ftp
    annotations
        embryo
            data_tables
                embryo[01-57]_data_table.csv            not used - updated 20210421 for processed images
            embryo_bounds
                embryo[01-57]_bounds.txt                csv_to_points.py -> Rectangles
        pgp1f
            cell_bounds
                fov[01-25]_cell_bounds.txt              csv_to_points.py -> Rectangles
            data_tables
                fov[01-25]_data_table.csv               csv_to_points.py -> Points and OMERO.tables
20210421-ftp
    annotations/embryo/data_tables/
        embryo[01-57]_data_table.csv                    csv_to_points.py -> Points and OMERO.tables
    processed
        embryo
            embryo[01-57]/cell01/
                cy[01-19]_ch[01-04].tif                 symlinked from 20210421-processed
                seg_[cenpa/lamin/npbs/nucleus].tif      seg_images_to_masks.py -> Masks
                stain_[cenpa/dapi/hyb/lamin].tif        symlinked from 20210421-processed
        pgp1
            fov[000-025]/cell[001-00n]/
                cy[01-18]_ch[01-04].tif                 symlinked from 20210421-processed
                seg_nucleus.tif                         seg_images_to_masks.py -> Masks
                stain_[dapi/hyb].tif                    symlinked from 20210421-processed
            fov000/cell000 empty!
20210421-processed
    embryo/embryo[01-57]/cell001/cell001/
        cell001.pattern                                 imported via processed-filePaths.tsv below
        cell001_t[01-19]_c[01-08].tif                   symlinks to 20210421-ftp/processed/...
    pgp1/fov[001-025]/cell[002-006]/
        cell002.pattern                                 imported via processed-filePaths.tsv below
        cell002_t[01-18]_c[01-06].tif                   symlinks to 20210421-ftp/processed/...
    processed-filePaths.tsv
20210713-ftp
    embryo[01-57]_cell[001-004]_seg_nucleus.tif         seg_images_to_masks.py -> Masks
```
