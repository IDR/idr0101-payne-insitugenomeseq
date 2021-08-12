
import pandas
import omero

import omero.cli

# Duplicate a row - E.g. for Embryo01
# Replace... e.g.

# Image Name: cell001_processed
# Assay Name: ??
# Source Name: ??
# Image File: cell001.pattern
# Comment [Image File Path]: /uod/idr/filesets/idr0101-payne-insitugenomeseq/20210421-processed/embryo/embryo01/cell001/
# Comment [Image File Type]: processed
# Channels: Chanlel 1: ch01; Channel 2: ch02; Channel 3: ch03; Channel 4: ch04; Channel 5: CENPA; Channel 6: DAPI; Channel 7: Hybridization probe; Channel 8: Lamin
# Processed Data File: 20210421-ftp/annotations/embryo/data_tables/embryo01_data_table.csv

# SET "A" or "B"
EXPERIMENT = "A"

project_name = "idr0101-payne-insitugenomeseq/experiment" + EXPERIMENT
table_path = "experiment%s/idr0101-experiment%s-annotation.csv" % (EXPERIMENT, EXPERIMENT)
output_path = "experiment%s/idr0101-experiment%s-annotation2.csv" % (EXPERIMENT, EXPERIMENT)

channel_names = "Channel 1 (Cy5): dibases AT, CG, GC and TA; Channel 2 (FITC): dibases AA, CC, GG and TT; Channel 3 (Cy3): dibases AC, CA, GT and TG; Channel 4 (TxRed): dibases AG, CT, GA and TC; Channel 5: DAPI; Channel 6: Hybridization probe"
if EXPERIMENT == "B":
    channel_names = "Channel 1 (Cy5): dibases AT, CG, GC and TA; Channel 2 (TxRed): dibases AC, CA, GT and TG; Channel 3 (Cy3): dibases AA, CC, GG and TT; Channel 4 (FITC) dibases AG, CT, GA and TC; Channel 5: CENP-A; Channel 6: DAPI; Channel 7: Hybridization probe; Channel 8: Lamin-B"

def main(conn):
    project = conn.getObject("Project", attributes={"name": project_name})
    print("Project", project.id)
    conn.SERVICE_OPTS.setOmeroGroup(project.getDetails().group.id.val)

    df2 = None
    for dataset in project.listChildren():
        for image in dataset.listChildren():
            if "_processed" not in image.name:
                continue

            df = pandas.read_csv(table_path, delimiter=",")
            col_names = list(df.columns)

            # Create output table with new rows
            if df2 is None:
                df2 = pandas.DataFrame(columns=(col_names))

            # Find rows for Dataset
            rslt_df = df.loc[df['Dataset Name'] == dataset.name]
            new_row = None
            for index, row in df.loc[df['Dataset Name'] == dataset.name].iterrows():
                # Use first matching row
                if new_row is None:
                    new_row = row

                    # cell001_processed -> cell001
                    cell_name = image.name.replace("_processed", "")
                    # Embryo_01 -> embryo01 or Fibroblasts_01 -> fibroblasts01
                    embryo_name = dataset.name.replace("_", "").lower()

                    file_path = "/uod/idr/filesets/idr0101-payne-insitugenomeseq/20210421-processed/"
                    if EXPERIMENT == "A":
                        # /uod/idr/filesets/idr0101-payne-insitugenomeseq/20210421-processed/pgp1/fov001/cell006/cell006.pattern
                        file_path += "pgp1/fov0%s/%s/" % (embryo_name.replace("fibroblasts", ""), cell_name)
                        data_file = "20210127-ftp/annotations/pgp1f/data_tables/fov%02d_data_table.csv" % (int(cell_name.replace("cell", "")))
                        source_name = dataset.name.replace("Fibroblasts_", "fov")
                    else:
                        file_path += "embryo/%s/%s/" % (embryo_name, cell_name)
                        data_file = "20210421-ftp/annotations/embryo/data_tables/%s_data_table.csv" % embryo_name
                        source_name = dataset.name.replace("Embryo_", "embryo")

                    new_row["Image Name"] = image.name
                    new_row["Assay Name"] = "In situ genome sequencing"
                    new_row["Source Name"] = source_name
                    new_row["Image File"] = "%s.pattern" % cell_name
                    new_row["Comment [Image File Path]"] = file_path
                    new_row["Comment [Image File Type]"] = "processed"
                    new_row["Channels"] = channel_names
                    new_row["Processed Data File"] = data_file

                    print("new_row", dataset.name, new_row)
                    df2 = df2.append(new_row, ignore_index=True)

    df2.to_csv(output_path, mode="a", index=False)


# This takes the idr0101-payne-insitugenomeseq/experimentB/idr0101-experimentB-annotation.csv
# and adds rows for all the processed cells.

# Usage:
# cd idr0101-payne-insitugenomeseq
# python scripts/processed_annotations.py

if __name__ == "__main__":
    with omero.cli.cli_login() as c:
        conn = omero.gateway.BlitzGateway(client_obj=c.get_client())
        main(conn)
        conn.close()