#!/usr/bin/env python

import pandas
from collections import defaultdict

import omero.clients
import omero.cli
import omero
from omero.rtypes import rint, rdouble, rstring

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
image_name = "embryo%02d_seq"


def get_image(project, embryo_id):
    for dataset in project.listChildren():
        print("dataset", dataset.name, dataset_name % embryo_id)
        if dataset.name == dataset_name % embryo_id:
            for image in dataset.listChildren():
                print("image", image.name, image_name % embryo_id)
                if image.name == image_name % embryo_id:
                    return image


def create_roi(updateService, image, shapes):
    roi = omero.model.RoiI()
    roi.setImage(image._obj)
    for shape in shapes:
        roi.addShape(shape)
    return updateService.saveAndReturnObject(roi)


def rgba_to_int(red, green, blue, alpha=255):
    return int.from_bytes([red, green, blue, alpha], byteorder="big", signed=True)


tables_path = (
    "/uod/idr/filesets/idr0101-payne-insitugenomeseq/20210127-ftp/annotations/"
)
# TODO - remove
tables_path = "/Users/wmoore/Desktop/IDR/idr0101/annotations/"

tables_path += "embryo/data_tables/embryo%02d_data_table.csv"


def main(conn):

    project = conn.getObject("Project", attributes={"name": project_name})
    print("Project", project.id)
    conn.SERVICE_OPTS.setOmeroGroup(project.getDetails().group.id.val)
    updateService = conn.getUpdateService()

    for embryo_id in range(1, 2):
        image = get_image(project, embryo_id)
        assert image is not None
        pix_size_x = image.getPixelSizeX()
        pix_size_y = image.getPixelSizeY()
        pix_size_z = image.getPixelSizeZ()

        # Read csv for each embryo
        table_pth = tables_path % embryo_id
        df = pandas.read_csv(table_pth, delimiter=",")
        col_names = list(df.columns)

        # Create output table with extra columns
        df2 = pandas.DataFrame(columns=(["Roi", "Shape"] + col_names))

        rows_by_chr = defaultdict(list)
        max_chr = 0

        # first, group rows by chr_id
        for index, row in df.iterrows():
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
                point.x = rdouble(row["x_um_abs"] / pix_size_x)
                point.y = rdouble(row["y_um_abs"] / pix_size_y)
                point.theZ = rint(int(round(row["z_um_abs"] / pix_size_z)))
                point.theT = rint(0)
                if chr_id <= len(colors):
                    point.fillColor = rint(rgba_to_int(*colors[chr_id - 1]))
                    point.strokeColor = rint(rgba_to_int(*colors[chr_id - 1]))

                points.append(point)

            roi = create_roi(updateService, image, points)

            # Need to get newly saved shape IDs
            shapes = list(roi.copyShapes())
            print("saved shapes", len(shapes))
            for row, shape in zip(rows_by_chr[chr_id], shapes):
                # checks that the order of shapes is same as order of rows
                assert shape.theZ.val == round(row["z_um_abs"] / pix_size_z)
                row["Roi"] = roi.id.val
                row["Shape"] = shape.id.val
                df2 = df2.append(row)

        df2.to_csv("embryo_rois_%02d.csv" % embryo_id, index=False)


if __name__ == "__main__":
    with omero.cli.cli_login() as c:
        conn = omero.gateway.BlitzGateway(client_obj=c.get_client())
        main(conn)
        conn.close()
