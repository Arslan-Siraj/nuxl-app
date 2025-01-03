# This Dockerfile builds OpenMS on NuXL branch, the TOPP tools, pyOpenMS and thidparty tools.

# hints:
# build image and give it a name (here: streamlitapp) with: docker build --no-cache -t streamlitapp:latest --build-arg GITHUB_TOKEN=<your-github-token> . 2>&1 | tee build.log 
# check if image was build: docker image ls
# run container: docker run -p 8501:8501 streamlitappsimple:latest
# debug container after build (comment out ENTRYPOINT) and run container with interactive /bin/bash shell
# prune unused images/etc. to free disc space (e.g. might be needed on gitpod). Use with care.: docker system prune --all --force

FROM ubuntu:22.04 AS setup-build-system
ARG OPENMS_REPO=https://github.com/Arslan-Siraj/OpenMS.git # https://github.com/OpenMS/OpenMS.git
ARG OPENMS_BRANCH=feature/NuXL
ARG PORT=8501
# GitHub token to download latest OpenMS executable for Windows from Github action artifact.
ARG GITHUB_TOKEN
# Streamlit app Gihub user name (to download artifact from).
ARG GITHUB_USER=Arslan-Siraj
# Streamlit app Gihub repository name (to download artifact from).
ARG GITHUB_REPO=nuxl-app

USER root

# Install required Ubuntu packages.
RUN apt-get -y update
RUN apt-get install -y --no-install-recommends --no-install-suggests g++ autoconf automake patch libtool make git gpg wget ca-certificates curl jq libgtk2.0-dev openjdk-8-jdk cron
RUN update-ca-certificates
RUN apt-get install -y --no-install-recommends --no-install-suggests libsvm-dev libeigen3-dev coinor-libcbc-dev libglpk-dev libzip-dev zlib1g-dev libxerces-c-dev libbz2-dev libomp-dev libhdf5-dev
RUN apt-get install -y --no-install-recommends --no-install-suggests libboost-date-time1.74-dev \
                                                                     libboost-iostreams1.74-dev \
                                                                     libboost-regex1.74-dev \
                                                                     libboost-math1.74-dev \
                                                                     libboost-random1.74-dev
RUN apt-get install -y --no-install-recommends --no-install-suggests qtbase5-dev libqt5svg5-dev libqt5opengl5-dev

# Download and install mamba.
ENV PATH="/root/mambaforge/bin:${PATH}"
RUN wget -q \
    https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-Linux-x86_64.sh \
    && bash Mambaforge-Linux-x86_64.sh -b \
    && rm -f Mambaforge-Linux-x86_64.sh
RUN mamba --version

# Setup mamba environment.
COPY environment.yml ./environment.yml
RUN mamba env create -f environment.yml

RUN echo "mamba activate streamlit-env" >> ~/.bashrc
SHELL ["/bin/bash", "--rcfile", "~/.bashrc"]
SHELL ["mamba", "run", "-n", "streamlit-env", "/bin/bash", "-c"]

# Install up-to-date cmake via mamba and packages for pyOpenMS build.
RUN mamba install cmake
RUN pip install --upgrade pip && python -m pip install -U setuptools nose Cython autowrap pandas numpy pytest

# Increase Git buffer size and timeout
RUN git config --global http.postBuffer 524288000
RUN git config --global http.lowSpeedTime 999999

# Clone OpenMS branch and the associcated contrib+thirdparties+pyOpenMS-doc submodules.
RUN git clone --recursive --depth=1 -b ${OPENMS_BRANCH} --single-branch ${OPENMS_REPO} && cd /OpenMS

# Pull Linux compatible third-party dependencies and store them in directory thirdparty.
WORKDIR /OpenMS
RUN mkdir /thirdparty && \
    git submodule update --init THIRDPARTY && \
    cp -r THIRDPARTY/All/* /thirdparty && \
    cp -r THIRDPARTY/Linux/64bit/* /thirdparty && \
    chmod -R +x /thirdparty
ENV PATH="/thirdparty/LuciPHOr2:/thirdparty/MSGFPlus:/thirdparty/Sirius:/thirdparty/ThermoRawFileParser:/thirdparty/Comet:/thirdparty/Fido:/thirdparty/MaRaCluster:/thirdparty/MyriMatch:/thirdparty/OMSSA:/thirdparty/Percolator:/thirdparty/SpectraST:/thirdparty/XTandem:/thirdparty/crux:${PATH}"

# Build OpenMS
FROM setup-build-system AS compile-openms
WORKDIR /

# Set up build directory.
RUN mkdir /openms-build
WORKDIR /openms-build

# Configure.
RUN /bin/bash -c "cmake -DCMAKE_BUILD_TYPE='Release' -DCMAKE_PREFIX_PATH='/OpenMS/contrib-build/;/usr/;/usr/local' -DHAS_XSERVER=OFF -DBOOST_USE_STATIC=OFF -DPYOPENMS=OFF ../OpenMS -DPY_MEMLEAK_DISABLE=On"

# Build TOPP tools and clean up.
RUN make -j4 TOPP
RUN rm -rf src doc CMakeFiles

# Build pyOpenMS wheels and install via pip.
#RUN make -j4 pyopenms
#WORKDIR /openms-build/pyOpenMS
#RUN pip install dist/*.whl


WORKDIR /
RUN mkdir openms

# Copy TOPP tools bin directory, add to PATH.
RUN cp -r openms-build/bin /openms/bin
ENV PATH="/openms/bin/:${PATH}"

# Copy TOPP tools bin directory, add to PATH.
RUN cp -r openms-build/lib /openms/lib
ENV LD_LIBRARY_PATH="/openms/lib/:${LD_LIBRARY_PATH}"

# Copy share folder, add to PATH, remove source directory.
RUN cp -r OpenMS/share/OpenMS /openms/share
RUN rm -rf OpenMS
ENV OPENMS_DATA_PATH="/openms/share/"

# Remove build directory.
RUN rm -rf openms-build

# Clone OpenMS branch and the associcated contrib+thirdparties+pyOpenMS-doc submodules.
RUN git clone --recursive --depth=1 -b develop --single-branch ${OPENMS_REPO} && cd /OpenMS

# Pull Linux compatible third-party dependencies and store them in directory thirdparty.
#WORKDIR /OpenMS
#RUN git checkout develop

#RUN mkdir /thirdparty && \
#    git submodule update --init THIRDPARTY && \
#    cp -r THIRDPARTY/All/* /thirdparty && \
#    cp -r THIRDPARTY/Linux/64bit/* /thirdparty && \
#    chmod -R +x /thirdparty
#ENV PATH="/thirdparty/LuciPHOr2:/thirdparty/MSGFPlus:/thirdparty/Sirius:/thirdparty/ThermoRawFileParser:/thirdparty/Comet:/thirdparty/Fido:/thirdparty/MaRaCluster:/thirdparty/MyriMatch:/thirdparty/OMSSA:/thirdparty/Percolator:/thirdparty/SpectraST:/thirdparty/XTandem:/thirdparty/crux:${PATH}"

# Build pyopenms
#FROM setup-build-system AS compile-pyopenms
#WORKDIR /

# Set up build directory.
RUN mkdir /openms-build_py
WORKDIR /openms-build_py

# Configure.
RUN /bin/bash -c "cmake -DCMAKE_BUILD_TYPE='Release' -DCMAKE_PREFIX_PATH='/OpenMS/contrib-build/;/usr/;/usr/local' -DHAS_XSERVER=OFF -DBOOST_USE_STATIC=OFF -DPYOPENMS=ON ../OpenMS -DPY_MEMLEAK_DISABLE=On"


# Build pyOpenMS wheels and install via pip.
RUN make -j4 pyopenms
WORKDIR /openms-build_py/pyOpenMS
RUN pip install dist/*.whl

# Prepare and run streamlit app.
FROM compile-openms AS run-app
# Create workdir and copy over all streamlit related files/folders.

# note: specifying folder with slash as suffix and repeating the folder name seems important to preserve directory structure
WORKDIR /app
COPY app.py /app/app.py 
COPY src/ /app/src
COPY assets/ /app/assets
COPY example-data/ /app/example-data
COPY content/ /app/content
COPY .streamlit/config.toml /app/.streamlit/config.toml
COPY clean-up-workspaces.py /app/clean-up-workspaces.py
COPY settings.json /app/settings.json
COPY hooks/ /app/hooks
COPY gdpr_consent/ /app/gdpr_consent

# add cron job to the crontab
RUN echo "0 3 * * * /root/mambaforge/envs/streamlit-env/bin/python /app/clean-up-workspaces.py >> /app/clean-up-workspaces.log 2>&1" | crontab -

# create entrypoint script to start cron service and launch streamlit app
RUN echo "#!/bin/bash" > /app/entrypoint.sh
RUN echo "service cron start" >> /app/entrypoint.sh
RUN echo "mamba run --no-capture-output -n streamlit-env streamlit run app.py" >> /app/entrypoint.sh
# make the script executable
RUN chmod +x /app/entrypoint.sh

# Patch Analytics
RUN mamba run -n streamlit-env python hooks/hook-analytics.py

# Set Online Deployment
RUN jq '.online_deployment = true' settings.json > tmp.json && mv tmp.json settings.json

# Download latest OpenMS App executable for Windows from Github actions workflow.
RUN WORKFLOW_ID=$(curl -s "https://api.github.com/repos/$GITHUB_USER/$GITHUB_REPO/actions/workflows" | jq -r '.workflows[] | select(.name == "Build executable for Windows") | .id') \
    && SUCCESSFUL_RUNS=$(curl -s "https://api.github.com/repos/$GITHUB_USER/$GITHUB_REPO/actions/runs?workflow_id=$WORKFLOW_ID&status=success" | jq -r '.workflow_runs[0].id') \
    && ARTIFACT_ID=$(curl -s "https://api.github.com/repos/$GITHUB_USER/$GITHUB_REPO/actions/runs/$SUCCESSFUL_RUNS/artifacts" | jq -r '.artifacts[] | select(.name == "OpenMS-App") | .id') \
    && curl -LJO -H "Authorization: Bearer $GITHUB_TOKEN" "https://api.github.com/repos/$GITHUB_USER/$GITHUB_REPO/actions/artifacts/$ARTIFACT_ID/zip" -o /app/OpenMS-App

# Run app as container entrypoint.
EXPOSE $PORT

# List conda packages and filter
#RUN conda list --explicit | grep -E "python|plotly|pandas|numpy|mono" > package_versions_in_docker.txt

# List pip packages and filter, then append to the same file
#RUN pip list --format=freeze | grep -E "streamlit|streamlit-plotly-events|streamlit-aggrid|pyopenms|captcha" >> package_versions_in_docker.txt

ENTRYPOINT ["/app/entrypoint.sh"] 