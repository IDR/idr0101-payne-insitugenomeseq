#!/usr/bin/env python

import omero.clients
import omero.cli
from omero.gateway import DatasetWrapper

"""
This script organises images imported into a single Dataset, into
multiple Datasets, based on their names. This wasn't possible to
do with bulk import as the images are all in the same fileset.
"""

project_name = "idr0101-payne-insitugenomeseq/experimentA"


def main(conn):

    project = conn.getObject("Project", attributes={"name": project_name})
    print("Project", project.id, project.getDetails().group.id.val)
    conn.SERVICE_OPTS.setOmeroGroup(project.getDetails().group.id.val)

    dataset01 = list(project.listChildren())[0]
    print("dataset01", dataset01)

    images_by_name = {}
    for image in dataset01.listChildren():
        images_by_name[image.name] = image

    for image_number in range(2, 26):
        # Create new Dataset
        dataset = DatasetWrapper(conn, omero.model.DatasetI())
        dataset.setName("Fibroblasts_%02d" % image_number)
        dataset.save()
        print("Dataset", dataset.id)
        pd_link = omero.model.ProjectDatasetLinkI()
        pd_link.child = omero.model.DatasetI(dataset.id, False)
        pd_link.parent = omero.model.ProjectI(project.id, False)
        pd_link = conn.getUpdateService().saveAndReturnObject(
            pd_link, conn.SERVICE_OPTS
        )
        print("pd_link", pd_link.id.val)

        for image_name in ["pgp1f [pgp1f_cycle01.nd2", "pgp1f_hyb [pgp1f_hyb.nd2"]:
            # Find the images
            name = "%s (series %02d)]" % (image_name, image_number)
            print(name)
            if name in images_by_name:
                img = images_by_name[name]
                print("linking image...", img.id)
                link = conn.getQueryService().findByQuery(
                    "select l from DatasetImageLink as l where l.parent.id=%i and l.child.id=%i"
                    % (dataset01.id, img.id),
                    None,
                    conn.SERVICE_OPTS,
                )
                link.parent = omero.model.DatasetI(dataset.id, False)
                conn.getUpdateService().saveObject(link, conn.SERVICE_OPTS)


if __name__ == "__main__":
    with omero.cli.cli_login() as c:
        conn = omero.gateway.BlitzGateway(client_obj=c.get_client())
        main(conn)
