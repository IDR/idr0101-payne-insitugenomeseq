#! /bin/sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements
parallel --joblog $(date '+%Y%m%d')_convert.log --results $(date '+%Y%m%d')_convert ./convert.sh ::: "$@"
parallel --joblog $(date '+%Y%m%d')_upload.log --results $(date '+%Y%m%d')_upload ./s3-upload.sh ::: "$@"
rm -rf /data/idr0101-payne-insitugenomeseq/*-zarr/
sudo ./idrftp-aspera.sh /data/idr0101-payne-insitugenomeseq/
rm -rf /data/idr0101-payne-insitugenomeseq/*-ometiff/
