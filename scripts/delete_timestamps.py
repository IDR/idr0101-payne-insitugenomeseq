#!/usr/bin/env python

import omero
import omero.cli

"""
This script deletes PlaneInfo from all experimentA images in idr0101.
In fact, only pgp1_fov*_hyb and _seq images have a single invalid
timestamp for T=0, making iviewer show NaNs for other T indices.
"""

# projectB_name = "idr0101-payne-insitugenomeseq/experimentB"
projectA_name = "idr0101-payne-insitugenomeseq/experimentA"

def delete_timestamps(conn, image):

    params = omero.sys.ParametersI()
    params.addLong('pid', image.getPixelsId())
    z = 0
    c = 0
    query = "from PlaneInfo as Info where"\
        " Info.theZ=%s and Info.theC=%s and pixels.id=:pid" % (z, c)
    info_list = conn.getQueryService().findAllByQuery(
        query, params, conn.SERVICE_OPTS)

    for info in info_list:
        print('deleting PlaneInfo', info.id.val)
        conn.getUpdateService().deleteObject(info)


def main(conn):
    projectA = conn.getObject("Project", attributes={"name": projectA_name})
    print("Project A", projectA.id)
    conn.SERVICE_OPTS.setOmeroGroup(projectA.getDetails().group.id.val)

    for dataset in projectA.listChildren():
        for image in dataset.listChildren():
            print('image.name', image.name)
            delete_timestamps(conn, image)

    # projectB = conn.getObject("Project", attributes={"name": projectB_name})
    # print("Project B", projectB.id)
    # for dataset in projectB.listChildren():
    #     print("Dataset", dataset.name)
    #     for image in dataset.listChildren():
    #         delete_timestamps(conn, image)

# Usage:
# cd idr0101-payne-insitugenomeseq
# python scripts/delete_timestamps.py

if __name__ == "__main__":
    with omero.cli.cli_login() as c:
        conn = omero.gateway.BlitzGateway(client_obj=c.get_client())
        main(conn)
