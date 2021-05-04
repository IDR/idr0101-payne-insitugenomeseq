#!/usr/bin/env python

import pandas
import mimetypes
from collections import defaultdict

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
dataset_name = "Embryo_%02d"
image_name = "cell%03d_processed"


def get_image(project, embryo_id, cell_id):
    for dataset in project.listChildren():
        print("dataset", dataset.name, dataset_name % embryo_id)
        if dataset.name == dataset_name % embryo_id:
            for image in dataset.listChildren():
                print("image", image.name, image_name % embryo_id)
                if image.name == image_name % cell_id:
                    return image


def create_roi(updateService, image, name, shapes):
    roi = omero.model.RoiI()
    # NB: $ populate metadata Image:1 --file data.csv NEEDS roi names
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
    "/uod/idr/filesets/idr0101-payne-insitugenomeseq/20210127-ftp/annotations/"
)
# For local testing
# tables_path = "/Users/wmoore/Desktop/IDR/idr0101/20210421-ftp/annotations/"

tables_path += "embryo/data_tables/embryo%02d_data_table.csv"


def populate_metadata(image, file_name):
    """Links the csv file to the image and parses it to create OMERO.table"""
    mt = mimetypes.guess_type(file_name, strict=False)[0]
    fileann = conn.createFileAnnfromLocalFile(
        file_name, mimetype=mt, ns=NSBULKANNOTATIONSRAW
    )
    fileid = fileann.getFile().getId()
    image.linkAnnotation(fileann)
    client = image._conn.c
    ctx = ParsingContext(
        client, image._obj, fileid=fileid, file=file_name, allow_nan=True
    )
    ctx.parse()


def main(conn):

    project = conn.getObject("Project", attributes={"name": project_name})
    print("Project", project.id)
    conn.SERVICE_OPTS.setOmeroGroup(project.getDetails().group.id.val)

    # For each embryo, we don't know how many cells are present
    # Simply start at 1 and keep checking until None found
    for embryo_id in range(1, 58):
        cell_id = 1
        image = get_image(project, embryo_id, cell_id)
        while image is not None:
            print("Processing image", image.id, image.name)
            process_image(conn, image, embryo_id, cell_id)
            cell_id += 1
            image = get_image(project, embryo_id, cell_id)


def process_image(conn, image, embryo_id, cell_id):
    updateService = conn.getUpdateService()
    pix_size_x = image.getPixelSizeX()
    pix_size_y = image.getPixelSizeY()
    pix_size_z = image.getPixelSizeZ()

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
    # for index, row in df.iterrows():
    for index, row in df.loc[df['cell_id'] == cell_id].iterrows():
        chr_id = row["chr"]
        max_chr = max(max_chr, chr_id)
        rows_by_chr[chr_id].append(row)

    # Create 1 ROI for each chr
    for chr_id in range(max_chr):
        if chr_id not in rows_by_chr:
            continue
        print(chr_id, "creating ROI with %s points" % (len(rows_by_chr[chr_id])))

        points = []
        # create a Point for each row
        for row in rows_by_chr[chr_id]:
            point = omero.model.PointI()
            point.textValue = rstring(row["chr_name"])
            # For Processed images we use x_um, y_um, z_um
            # x in pixels = x_um * 9.2306
            # y in pixels = y_um * 9.2306
            # z in pixels = z_um / 2.5
            point.x = rdouble(row["x_um"] * 9.2306)
            point.y = rdouble(row["y_um"] * 9.2306)
            point.theZ = rint(int(round(row["z_um"] / 2.5)))
            # For Hybrid images (embryo01_hyb.ims for embryo 1) use x_um_abs, y_um_abs, z_um_abs
            # point.x = rdouble(row["x_um_abs"] / pix_size_x)
            # point.y = rdouble(row["y_um_abs"] / pix_size_y)
            # point.theZ = rint(int(round(row["z_um_abs"] / pix_size_z)))
            if chr_id <= len(colors):
                # point.fillColor = rint(rgba_to_int(*colors[chr_id - 1]))
                point.strokeColor = rint(rgba_to_int(*colors[chr_id - 1]))
            # point.theT = rint(0)

            points.append(point)

        roi = create_roi(updateService, image, row["chr_name"], points)

        # Need to get newly saved shape IDs
        shapes = list(roi.copyShapes())
        print("saved shapes", len(shapes))
        for row, shape in zip(rows_by_chr[chr_id], shapes):
            # checks that the order of shapes is same as order of rows
            assert shape.theZ.val == round(row["z_um"] / 2.5)
            row["roi"] = roi.id.val
            row["shape"] = shape.id.val
            df2 = df2.append(row)

    csv_name = "embryo_rois_%02d.csv" % embryo_id
    # Add # header roi, shape, other-col-types...
    with open(csv_name, "w") as csv_out:
        csv_out.write("# header roi,l," + ",".join(col_types) + "\n")

    df2.to_csv(csv_name, mode="a", index=False)

    # Create OMERO.table from csv
    populate_metadata(image, csv_name)


if __name__ == "__main__":
    with omero.cli.cli_login() as c:
        conn = omero.gateway.BlitzGateway(client_obj=c.get_client())
        main(conn)
        conn.close()
