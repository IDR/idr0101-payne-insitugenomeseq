#!/usr/bin/env python

import pandas
import mimetypes
from collections import defaultdict
import tempfile
import os

import omero.clients
import omero.cli
import omero
from omero.rtypes import rint, rdouble, rstring
from omero_metadata.populate import ParsingContext
from omero.util.metadata_utils import NSBULKANNOTATIONSRAW

"""
This script parses data_table.csv files, 1 per embryo to create
a Point for each row.
"""

# colors picked to match figures in the paper
colors = [
    (38, 47, 143),
    (249, 16, 30),
    (91, 180, 43),
    (226, 44, 144),
    (248, 217, 48),
    (15, 65, 11),
    (121, 103, 186),
    (158, 41, 48),
    (111, 198, 149),
    (43, 106, 124),
    (18, 10, 98),
    (143, 200, 73),
    (233, 146, 202),
    (144, 51, 157),
    (93, 9, 69),
    (242, 22, 80),
    (248, 184, 110),
    (17, 20, 8),
    (121, 159, 92),
    (250, 106, 33),
    (113, 87, 23),
    (152, 215, 215),
    (172, 188, 219),
    (94, 65, 94),
]

project_name = "idr0101-payne-insitugenomeseq/experimentB"

def get_dataset(project, embryo_id):
    for dataset in project.listChildren():
        if dataset.name == "Embryo_%02d" % embryo_id:
            return dataset


def get_image(dataset, name_contains):
    imgs = [image for image in dataset.listChildren() if name_contains in image.name]
    assert len(imgs) < 2
    if len(imgs) == 1:
        return imgs[0]


def create_roi(updateService, image, shapes):
    roi = omero.model.RoiI()
    # NB: $ populate metadata Image:1 --file data.csv NEEDS roi names
    name = shapes[0].textValue.val
    roi.name = rstring(name)
    roi.setImage(image._obj)
    for shape in shapes:
        roi.addShape(shape)
    return updateService.saveAndReturnObject(roi)


def rgba_to_int(red, green, blue, alpha=255):
    return int.from_bytes([red, green, blue, alpha], byteorder="big", signed=True)


def get_omero_col_type(dtype):
    """Returns s for string, d for double, l for long/int"""
    if dtype == "int":
        return "l"
    elif dtype == "float":
        return "d"
    return "s"


tables_path = (
    "/uod/idr/filesets/idr0101-payne-insitugenomeseq/20210421-ftp/annotations/"
)
# For local testing
# tables_path = "/Users/wmoore/Desktop/IDR/idr0101/data/idr0101-payne-insitugenomeseq/20210421-ftp/annotations/"

tables_path += "embryo/data_tables/embryo%02d_data_table.csv"


def populate_metadata(image, file_path, file_name):
    """Links the csv file to the image and parses it to create OMERO.table"""
    mt = mimetypes.guess_type(file_name, strict=False)[0]
    # originalfile path will be ''
    fileann = conn.createFileAnnfromLocalFile(
        file_path, origFilePathAndName=file_name, mimetype=mt, ns=NSBULKANNOTATIONSRAW
    )
    fileid = fileann.getFile().getId()
    image.linkAnnotation(fileann)
    client = image._conn.c
    ctx = ParsingContext(
        client, image._obj, fileid=fileid, file=file_path, allow_nan=True
    )
    ctx.parse()


def process_image(conn, image, embryo_id, cell_id=None):

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
  

    # first, group rows by chr_id
    if cell_id is None:
        for index, row in df.iterrows():
            # chr_id based on cell AND chr for _hybridization images
            chr_id = (100 * row['cell_id']) + row['chr']       # e.g. 120
            max_chr = max(max_chr, chr_id)
            rows_by_chr[chr_id].append(row)
    else:
        # filter table rows by cell_id
        for index, row in df.loc[df['cell_id'] == cell_id].iterrows():
            chr_id = row['chr']
            max_chr = max(max_chr, chr_id)
            rows_by_chr[chr_id].append(row)

    def get_coord(row, xyz="x"):
        if cell_id is None:
            return row[xyz + "_um_abs"]
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
            if cell_id is None:
                point.textValue = rstring(f"cell{row['cell_id']}_{row['chr_name']}")
            else:
                point.textValue = rstring(row['chr_name'])
            # NB: switch X and Y (analysis used a different coordinate system)
            point.y = rdouble(get_coord(row, 'x') * 9.2306)
            point.x = rdouble(get_coord(row, 'y') * 9.2306)
            point.theZ = rint(int(round(get_coord(row, 'z') * 2.5)))
            if chr_id <= len(colors):
                point.strokeColor = rint(rgba_to_int(*colors[chr_id - 1]))

            points.append(point)

        roi = create_roi(updateService, image, points)

        # Need to get newly saved shape IDs
        shapes = list(roi.copyShapes())
        print("saved shapes", len(shapes))
        for row, shape in zip(rows_by_chr[chr_id], shapes):
            # checks that the order of shapes is same as order of rows
            assert shape.theZ.val == round(get_coord(row, 'z') * 2.5)
            row["roi"] = roi.id.val
            row["shape"] = shape.id.val
            df2 = df2.append(row)

    csv_name = "embryo_rois_%02d.csv" % embryo_id
    csv_path = os.path.join(tempfile.gettempdir(), csv_name)
    # Add # header roi, shape, other-col-types...
    with open(csv_path, "w") as csv_out:
        csv_out.write("# header roi,l," + ",".join(col_types) + "\n")

    df2.to_csv(csv_path, mode="a", index=False)

    # Create OMERO.table from csv
    populate_metadata(image, csv_path, csv_name)


def main(conn):
    project = conn.getObject("Project", attributes={"name": project_name})
    print("Project", project.id)
    conn.SERVICE_OPTS.setOmeroGroup(project.getDetails().group.id.val)

    for embryo_id in range(1, 58):
        dataset = get_dataset(project, embryo_id)
        hyb_image = get_image(dataset, name_contains="_hyb")
        print("Processing hyb_image", hyb_image.id, hyb_image.name)
        process_image(conn, hyb_image, embryo_id)

        cell_id = 1
        # process cell001_processed images
        # For each embryo, we don't know how many cells are present
        # Simply start at 1 and keep checking until None found
        image = get_image(dataset, name_contains="cell%03d_processed" % cell_id)
        while image is not None:
            print("Processing image", image.id, image.name)
            process_image(conn, image, embryo_id, cell_id)
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
