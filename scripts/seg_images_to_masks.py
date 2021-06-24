#!/usr/bin/env python

# Self contained script, based on Simon's script
# https://raw.githubusercontent.com/IDR/idr0052-walther-condensinmap/master/scripts/upload_and_create_rois.py
# and omero-roi package: https://github.com/ome/omero-rois

import os
import numpy as np
from PIL import Image, ImageSequence
from numpy.lib.arraysetops import isin
import omero
import omero.cli
from omero.gateway import BlitzGateway
from omero.gateway import ColorHolder
from omero.model import MaskI
from omero.rtypes import (
    rdouble,
    rint,
    rstring,
)

"""
This script adds seg_* binary images as masks onto *_processed images in OMERO
for idr0101 experimentA and experimentB
"""


projectB_name = "idr0101-payne-insitugenomeseq/experimentB"
projectA_name = "idr0101-payne-insitugenomeseq/experimentA"

base_path = "/uod/idr/filesets/idr0101-payne-insitugenomeseq/"

# For local testing
# base_path = "/Users/wmoore/Desktop/IDR/idr0101/data/idr0101-payne-insitugenomeseq/"

# for Experiment B, we have tables sent later with corrected coordinates for processed images
seg_images_path_B = base_path + "20210421-ftp/processed/embryo/embryo%s/cell001/"
# EperimentA
seg_images_path_A = base_path + "20210421-ftp/processed/pgp1/fov0%s/%s/"

MISSING_FILES = [
    "/uod/idr/filesets/idr0101-payne-insitugenomeseq/20210421-ftp/processed/embryo/embryo02/cell001/seg_nucleus.tif"
    ]

RGBA = (255, 255, 255, 128)


def mask_from_binary_image(binim, z, text=None, rgba=None):
    """
    Create a mask shape from a binary image (background=0)

    :param numpy.array binim: Binary 2D array, must contain values [0, 1] only
    :param z: Optional Z-index for the mask
    :return: An OMERO mask
    """

    # Find bounding box to minimise size of mask
    xmask = binim.sum(0).nonzero()[0]
    ymask = binim.sum(1).nonzero()[0]
    if any(xmask) and any(ymask):
        x0 = min(xmask)
        w = max(xmask) - x0 + 1
        y0 = min(ymask)
        h = max(ymask) - y0 + 1
        submask = binim[y0:(y0 + h), x0:(x0 + w)]
    else:
        return None

    mask = MaskI()
    # BUG in older versions of Numpy:
    # https://github.com/numpy/numpy/issues/5377
    # Need to convert to an int array
    # mask.setBytes(np.packbits(submask))
    mask.setBytes(np.packbits(np.asarray(submask, dtype=int)))
    mask.setWidth(rdouble(w))
    mask.setHeight(rdouble(h))
    mask.setX(rdouble(x0))
    mask.setY(rdouble(y0))

    if z is not None:
        mask.setTheZ(rint(z))
    if text is not None:
        mask.setTextValue(rstring(text))
    if rgba is not None:
        ch = ColorHolder.fromRGBA(*rgba)
        mask.setFillColor(rint(ch.getInt()))

    return mask


def delete_mask_rois(conn, im):
    result = conn.getRoiService().findByImage(im.id, None)
    to_delete = []
    for roi in result.rois:
        for shape in roi.copyShapes():
            if isinstance(shape, MaskI):
                to_delete.append(roi.getId().getValue())
                break
    if to_delete:
        print("Deleting existing {} rois".format(len(to_delete)))
        conn.deleteObjects("Roi", to_delete, deleteChildren=True, wait=True)


def create_roi(seg_path, text):
    im = Image.open(seg_path)
    # read each binary tif plane from stack
    planes = [np.asarray(plane) for plane in ImageSequence.Iterator(im)]
    roi = omero.model.RoiI()
    mask_count = 0
    for z, plane in enumerate(planes):
        mask = mask_from_binary_image(plane, z, text, RGBA)
        if mask is not None:
            mask_count += 1
            roi.addShape(mask)
    print("Added", mask_count, "masks to ROI")
    return roi


def main(conn):
    updateService = conn.getUpdateService()
    projectA = conn.getObject("Project", attributes={"name": projectA_name})
    print("Project A", projectA.id)
    conn.SERVICE_OPTS.setOmeroGroup(projectA.getDetails().group.id.val)

    for dataset in projectA.listChildren():
        for image in dataset.listChildren():
            print('image.name', image.name)
            if "_processed" not in image.name:
                continue

            # dataset e.g. Fibroblasts_01
            fov_id = dataset.name.replace("Fibroblasts_", "")
            # image e.g. cell002_processed
            cell_name = image.name.replace("_processed", "")
            images_path = seg_images_path_A % (fov_id, cell_name)
            
            delete_mask_rois(conn, image)

            for seg in ['nucleus']:
                seg_path = images_path + 'seg_%s.tif' % seg
                print('seg', seg)
                roi = create_roi(seg_path, seg)
                roi.setImage(image._obj)
                updateService.saveAndReturnObject(roi)

    projectB = conn.getObject("Project", attributes={"name": projectB_name})
    for dataset in projectB.listChildren():
        print("Dataset", dataset.name)
        for image in dataset.listChildren():
            if "_processed" not in image.name:
                continue

            # dataset e.g. Embryo_01
            print('Image', image.name)
            embryo_id = dataset.name.replace("Embryo_", "")
            images_path = seg_images_path_B % embryo_id

            delete_mask_rois(conn, image)

            for seg in ['nucleus', 'npbs', 'lamin', 'cenpa']:
                seg_path = images_path + 'seg_%s.tif' % seg
                if seg_path in MISSING_FILES:
                    continue
                print('seg', seg)
                roi = create_roi(seg_path, seg)
                roi.setImage(image._obj)
                updateService.saveAndReturnObject(roi)

# Usage:
# cd idr0101-payne-insitugenomeseq
# python scripts/seg_images_to_masks.py

if __name__ == "__main__":
    with omero.cli.cli_login() as c:
        conn = omero.gateway.BlitzGateway(client_obj=c.get_client())
        main(conn)
