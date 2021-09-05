#!/usr/bin/env python

import pandas
from collections import defaultdict
import tempfile
import os
import decimal

import omero.clients
import omero.cli
import omero
from omero.rtypes import rint, rdouble, rstring, unwrap
from omero_metadata.populate import ParsingContext
from omero.util.metadata_utils import NSBULKANNOTATIONSRAW

"""
This script parses data_table.csv files, 1 per embryo to create
a Point for each row.
"""

# colors picked to match figures in the paper
colors = {
    'chr1': (38, 47, 143),
    'chr2': (249, 16, 30),
    'chr3': (91, 180, 43),
    'chr4': (226, 44, 144),
    'chr5': (248, 217, 48),
    'chr6': (15, 65, 11),
    'chr7': (121, 103, 186),
    'chr8': (158, 41, 48),
    'chr9': (111, 198, 149),
    'chr10': (43, 106, 124),
    'chr11': (18, 10, 98),
    'chr12': (143, 200, 73),
    'chr13': (233, 146, 202),
    'chr14': (144, 51, 157),
    'chr15': (93, 9, 69),
    'chr16': (242, 22, 80),
    'chr17': (248, 184, 110),
    'chr18': (17, 20, 8),
    'chr19': (121, 159, 92),
    'chr20': (250, 106, 33),
    'chr21': (113, 87, 23),
    'chr22': (152, 215, 215),
    'chrX': (172, 188, 219),
    'chrY': (94, 65, 94),
}

projectB_name = "idr0101-payne-insitugenomeseq/experimentB"
projectA_name = "idr0101-payne-insitugenomeseq/experimentA"

def get_dataset(B, embryo_id):
    for dataset in B.listChildren():
        if dataset.name == "Embryo_%02d" % embryo_id:
            return dataset


def get_image(dataset, name_contains):
    imgs = [image for image in dataset.listChildren() if name_contains in image.name]
    assert len(imgs) < 2
    if len(imgs) == 1:
        return imgs[0]


def create_roi(updateService, image, shapes):
    roi = omero.model.RoiI()
    # Give ROI a name if first shape has one
    name = unwrap(shapes[0].textValue)
    if name:
        roi.name = rstring(name)
    roi.setImage(image._obj)
    for shape in shapes:
        roi.addShape(shape)
    return updateService.saveAndReturnObject(roi)


def delete_rois(conn, im):
    result = conn.getRoiService().findByImage(im.id, None)
    to_delete = []
    for roi in result.rois:
        to_delete.append(roi.getId().getValue())
    if to_delete:
        print("Deleting existing {} rois".format(len(to_delete)))
        conn.deleteObjects("Roi", to_delete, deleteChildren=True, wait=True)


def rgba_to_int(red, green, blue, alpha=255):
    return int.from_bytes([red, green, blue, alpha], byteorder="big", signed=True)


def get_omero_col_type(dtype):
    """Returns s for string, d for double, l for long/int"""
    if dtype == "int":
        return "l"
    elif dtype == "float":
        return "d"
    return "s"


base_path = "/uod/idr/filesets/idr0101-payne-insitugenomeseq/"

# For local testing
# base_path = "/Users/wmoore/Desktop/IDR/idr0101/data/idr0101-payne-insitugenomeseq/"

# ExperimentA
tables_path_A = base_path + "20210127-ftp/annotations/pgp1f/data_tables/fov%02d_data_table.csv"
bounds_path_A = base_path + "20210127-ftp/annotations/pgp1f/cell_bounds/fov%02d_cell_bounds.txt"

# for Experiment B, we have tables sent later with corrected coordinates for processed images
tables_path_B = base_path + "20210421-ftp/annotations/embryo/data_tables/embryo%02d_data_table.csv"
bounds_path_B = base_path + "20210127-ftp/annotations/embryo/embryo_bounds/embryo%02d_bounds.txt"


def process_bounds(conn, image, image_id, file_path):

    bounds_pth = file_path % image_id
    print('bounds_pth', bounds_pth)

    updateService = conn.getUpdateService()

    with open(bounds_pth, 'r') as f:
        for l in f.readlines():
            if not l:
                continue
            coords = [float(n) for n in l.split(",")]
            if len(coords) == 6:
                x_start, y_start, z_start, x_length, y_length, z_length = coords
            else:
                x_start, y_start, x_length, y_length = coords
                z_start = -1    # don't set theZ
                z_length = 1    # single rectangle across all Z

            shapes = []
            for z in range(int(z_start), int(z_start + z_length)):
                rect = omero.model.RectangleI()
                # coords are in pixel units
                rect.x = rdouble(x_start)
                rect.y = rdouble(y_start)
                rect.width = rdouble(x_length)
                rect.height = rdouble(y_length)
                if z > -1:
                    rect.theZ = rint(z)
                shapes.append(rect)

            roi = create_roi(updateService, image, shapes)


def populate_metadata(image, file_path, file_name):
    """Parses csv to create OMERO.table"""
    client = image._conn.c
    ctx = ParsingContext(
        client, image._obj, file=file_path, allow_nan=True
    )
    ctx.parse()


def process_image(conn, image, embryo_id, tables_path, cell_id=None):

    if image.getROICount() > 0:
        return

    updateService = conn.getUpdateService()

    # Read csv for each embryo
    table_pth = tables_path % embryo_id
    df = pandas.read_csv(table_pth, delimiter=",")

    col_types = [get_omero_col_type(t) for t in df.dtypes]
    col_names = list(df.columns)

    # Create output table with extra columns
    df2 = pandas.DataFrame(columns=(["roi", "shape"] + col_names))

    rows_by_chr = defaultdict(list)
    max_chr = 0
  

    # first, group rows by chr_id (or hg38_chr ?? for experimentA)
    if cell_id is None:
        # experimentB only...
        for index, row in df.iterrows():
            # chr_id based on cell AND chr for _hybridization images
            chr_id = (100 * row['cell_id']) + row['chr']       # e.g. 120
            max_chr = max(max_chr, chr_id)
            rows_by_chr[chr_id].append(row)
    else:
        # filter table rows by cell_id
        if 'embryo' in tables_path:
            cell_key = 'cell_id'
            chr_key = 'chr'
        else:
            cell_key = 'fov_cell'
            chr_key = 'hg38_chr'
        for index, row in df.loc[df[cell_key] == cell_id].iterrows():
            chr_id = row[chr_key]
            max_chr = max(max_chr, chr_id)
            rows_by_chr[chr_id].append(row)

    def get_coord(row, xyz="x"):
        # corrected coords for experiment B _hyb
        if cell_id is None and 'embryo' in tables_path:
            return row[xyz + "_um_abs"]
        # experiment A or processed experiment B images
        return row[xyz + "_um"]

    # Create 1 ROI for each chr (per cell)
    for chr_id in range(max_chr):
        if chr_id not in rows_by_chr:
            continue
        print(chr_id, "creating ROI with %s points" % (len(rows_by_chr[chr_id])))

        points = []
        # create a Point for each row
        for row in rows_by_chr[chr_id]:
            point = omero.model.PointI()
            # NB: switch X and Y (analysis used a different coordinate system)
            point.y = rdouble(get_coord(row, 'x') * 9.2306)
            point.x = rdouble(get_coord(row, 'y') * 9.2306)
            # We don't want Python3 behaviour of rounding .5 to even number - always round up
            point.theZ = rint(int(decimal.Decimal(get_coord(row, 'z') * 2.5).quantize(decimal.Decimal('1'), rounding=decimal.ROUND_HALF_UP)))
            if 'embryo' in tables_path:
                # experimentB - get chr number from name
                chr_name = row['chr_name']
                if cell_id is None:
                    point.textValue = rstring(f"cell{row['cell_id']}_{row['chr_name']}")
                else:
                    point.textValue = rstring(row['chr_name'])
            else:
                # experimentA - no cell ID included in chr_id
                point.textValue = rstring('hg38_chr' + str(row['hg38_chr']))
                chr_name = 'chr' + str(row['hg38_chr'])
            if chr_name in colors:
                point.strokeColor = rint(rgba_to_int(*colors[chr_name]))

            points.append(point)

        roi = create_roi(updateService, image, points)

        # Need to get newly saved shape IDs
        shapes = list(roi.copyShapes())
        print("saved shapes", len(shapes))
        for row, shape in zip(rows_by_chr[chr_id], shapes):
            # checks that the order of shapes is same as order of rows
            assert shape.theZ.val == decimal.Decimal(get_coord(row, 'z') * 2.5).quantize(decimal.Decimal('1'), rounding=decimal.ROUND_HALF_UP)
            row["roi"] = roi.id.val
            row["shape"] = shape.id.val
            df2 = df2.append(row)

    if 'embryo' in tables_path:
        csv_name = "embryo_rois_%02d.csv" % embryo_id
    else:
        csv_name = "pgp1f_rois_%02d.csv" % embryo_id
    csv_path = os.path.join(tempfile.gettempdir(), csv_name)
    # Add # header roi, shape, other-col-types...
    with open(csv_path, "w") as csv_out:
        csv_out.write("# header roi,l," + ",".join(col_types) + "\n")

    df2.to_csv(csv_path, mode="a", index=False)

    # Create OMERO.table from csv
    populate_metadata(image, csv_path, csv_name)


def main(conn):

    projectA = conn.getObject("Project", attributes={"name": projectA_name})
    print("Project A", projectA.id)
    conn.SERVICE_OPTS.setOmeroGroup(projectA.getDetails().group.id.val)

    for dataset in projectA.listChildren():
        for image in dataset.listChildren():
            fov_id = int(dataset.name.replace("Fibroblasts_", ""))
            print('image.name', image.name)
            if "_processed" not in image.name:
                delete_rois(conn, image)
                # Add bounds to _seq images as they seem to fit better than _hyb
                if "_seq" in image.name:
                    process_bounds(conn, image, fov_id, bounds_path_A)
                continue
            # name e.g. 'cell002_processed'
            cell_id = int(image.name.replace("cell", "").replace("_processed", ""))
            print("fov", fov_id, "cell", cell_id)
            delete_rois(conn, image)
            process_image(conn, image, fov_id, tables_path_A, cell_id)

    # Embryos - Project B...
    projectB = conn.getObject("Project", attributes={"name": projectB_name})
    print("Project B", projectB.id)

    for embryo_id in range(1, 58):
        dataset = get_dataset(projectB, embryo_id)
        # "I've adjusted some of the columns (x_um_abs, y_um_abs) in the embryo data tables such that
        # you can now lay the data points over the hybridization probe images (e.g. embryo01_hyb.ims for embryo 1)"
        hyb_image = get_image(dataset, name_contains="_hyb")
        print("Processing hyb_image", hyb_image.id, hyb_image.name)
        delete_rois(conn, hyb_image)
        process_image(conn, hyb_image, embryo_id, tables_path_B)
        # Add bounds to _hyb images as they seem to fit better than _seq (opposite of experimentA)
        process_bounds(conn, hyb_image, embryo_id, bounds_path_B)

        cell_id = 1
        # process cell001_processed images
        # For each embryo, we don't know how many cells are present
        # Simply start at 1 and keep checking until None found
        image = get_image(dataset, name_contains="cell%03d_processed" % cell_id)
        while image is not None:
            print("Processing image", image.id, image.name)
            delete_rois(conn, image)
            process_image(conn, image, embryo_id, tables_path_B, cell_id)
            cell_id += 1
            image = get_image(dataset, name_contains="cell%03d_processed" % cell_id)

# Usage:
# cd idr0101-payne-insitugenomeseq
# python scripts/csv_to_points.py

if __name__ == "__main__":
    with omero.cli.cli_login() as c:
        conn = omero.gateway.BlitzGateway(client_obj=c.get_client())
        main(conn)
        conn.close()
