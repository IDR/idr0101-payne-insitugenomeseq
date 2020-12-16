FROM idr0101_bf2raw

USER root
RUN wget https://github.com/glencoesoftware/raw2ometiff/releases/download/v0.2.8/raw2ometiff-0.2.8.zip && unzip raw2ometiff-0.2.8.zip && rm raw2ometiff-0.2.8.zip
RUN mv raw2ometiff-0.2.8 /opt/raw2ometiff

USER 1000
ENTRYPOINT ["/bin/bash"]
