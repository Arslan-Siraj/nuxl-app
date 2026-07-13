# This Dockerfile builds OpenMS on NuXL branch, the TOPP tools, pyOpenMS and thidparty tools.

# hints:
# build image and give it a name (here: streamlitapp) with: docker build --no-cache -t streamlitapp:latest --build-arg GITHUB_TOKEN=<your-github-token> . 2>&1 | tee build.log 
# check if image was build: docker image ls
# run container: docker run -p 8501:8501 streamlitappsimple:latest
# debug container after build (comment out ENTRYPOINT) and run container with interactive /bin/bash shell
# prune unused images/etc. to free disc space (e.g. might be needed on gitpod). Use with care.: docker system prune --all --force

# This Dockerfile builds OpenMS on NuXL branch, the TOPP tools, pyOpenMS and thidparty tools.
# docker buildx build --load -t nuxlapp:latest .
FROM ubuntu:22.04 AS setup-build-system

ARG OPENMS_REPO=https://github.com/Arslan-Siraj/OpenMS.git
ARG OPENMS_BRANCH=develop
ARG PORT=8501

ENV OPENMS_DIR=/root/openms-development
ENV PORT=${PORT}

FROM setup-build-system AS compile-openms

RUN apt-get update && apt-get install -y --no-install-recommends \
    autoconf \
    automake \
    libtool \
    pkg-config \
    libssl-dev \
    git \
    build-essential \
    wget \
    curl \
    python3 \
    python3-pip \
    ca-certificates \
    gnupg \
    cron \
    jq \
    default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends --no-install-suggests \
    qt6-base-dev \
    libqt6svg6-dev \
    libqt6opengl6-dev \
    libqt6openglwidgets6 \
    libgl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN wget -O - https://apt.kitware.com/keys/kitware-archive-latest.asc 2>/dev/null \
    | gpg --dearmor - \
    | tee /usr/share/keyrings/kitware-archive-keyring.gpg >/dev/null \
    && echo "deb [signed-by=/usr/share/keyrings/kitware-archive-keyring.gpg] https://apt.kitware.com/ubuntu/ jammy main" \
    > /etc/apt/sources.list.d/kitware.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends cmake kitware-archive-keyring \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p ${OPENMS_DIR} \
    && cd ${OPENMS_DIR} \
    && git clone --branch ${OPENMS_BRANCH} --recurse-submodules ${OPENMS_REPO} OpenMS

RUN mkdir -p ${OPENMS_DIR}/contrib_build \
    && cd ${OPENMS_DIR}/contrib_build \
    && cmake -DBUILD_TYPE=ALL ${OPENMS_DIR}/OpenMS/contrib \
    && make -j"$(nproc || echo 2)"

ENV PATH="${OPENMS_DIR}/contrib_build/bin:${PATH}"
ENV LD_LIBRARY_PATH="${OPENMS_DIR}/contrib_build/lib:${LD_LIBRARY_PATH}"

RUN mkdir -p ${OPENMS_DIR}/openms_build \
    && cd ${OPENMS_DIR}/openms_build \
    && cmake \
        -DCMAKE_BUILD_TYPE=Release \
        -DHAS_XSERVER=OFF \
        -DPYOPENMS=OFF \
        -DGIT_TRACKING=OFF \
        -DENABLE_UPDATE_CHECK=OFF \
        -DBoost_USE_STATIC_LIBS=OFF \
        -DOPENMS_CONTRIB_LIBS=${OPENMS_DIR}/contrib_build \
        ${OPENMS_DIR}/OpenMS \
    && make -j"$(nproc || echo 2)"

WORKDIR ${OPENMS_DIR}/OpenMS
RUN mkdir -p /thirdparty && \
    git submodule update --init THIRDPARTY && \
    cp -r THIRDPARTY/All/* /thirdparty 2>/dev/null || true && \
    cp -r THIRDPARTY/Linux/x86_64/* /thirdparty 2>/dev/null || true && \
    chmod -R +x /thirdparty || true

ENV PATH="/thirdparty/LuciPHOr2:/thirdparty/MSGFPlus:/thirdparty/Sirius:/thirdparty/ThermoRawFileParser:/thirdparty/Comet:/thirdparty/Fido:/thirdparty/MaRaCluster:/thirdparty/MyriMatch:/thirdparty/OMSSA:/thirdparty/Percolator:/thirdparty/SpectraST:/thirdparty/XTandem:/thirdparty/crux:${PATH}"

ENV PATH="/root/miniforge3/bin:${PATH}"
RUN wget -q https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh \
    && bash Miniforge3-Linux-x86_64.sh -b \
    && rm -f Miniforge3-Linux-x86_64.sh

RUN chmod o+x /root

COPY environment.yml /tmp/environment.yml
RUN /root/miniforge3/bin/mamba env create -f /tmp/environment.yml
RUN echo "mamba activate streamlit-env" >> ~/.bashrc
SHELL ["/bin/bash", "--rcfile", "~/.bashrc"]
SHELL ["mamba", "run", "-n", "streamlit-env", "/bin/bash", "-c"]

RUN python -m pip install --upgrade pip && \
    python -m pip install "setuptools<82" nose cython autowrap pandas numpy pytest && \
    python -m pip install nuxl-rescore==0.2.0 && \
    python -c "import pkg_resources; import nuxl_rescore; print('imports ok')"

# Pre-download and verify the MS2PIP XGBoost models.
# This prevents incomplete runtime downloads and
# "Model hash not recognized." warnings during the workflow.
RUN mkdir -p /root/.ms2pip && \
    curl -fL \
        --retry 5 \
        --retry-delay 3 \
        --connect-timeout 20 \
        --max-time 600 \
        "https://zenodo.org/records/13270668/files/model_20210416_HCD2021_B.xgboost" \
        -o /root/.ms2pip/model_20210416_HCD2021_B.xgboost && \
    curl -fL \
        --retry 5 \
        --retry-delay 3 \
        --connect-timeout 20 \
        --max-time 600 \
        "https://zenodo.org/records/13270668/files/model_20210416_HCD2021_Y.xgboost" \
        -o /root/.ms2pip/model_20210416_HCD2021_Y.xgboost && \
    echo "c086c599f618b199bbb36e2411701fb2866b24c8  /root/.ms2pip/model_20210416_HCD2021_B.xgboost" \
        | sha1sum -c - && \
    echo "22a5a137e29e69fa6d4320ed7d701b61cbdc4fcf  /root/.ms2pip/model_20210416_HCD2021_Y.xgboost" \
        | sha1sum -c -

SHELL ["/bin/bash", "-c"]

WORKDIR /
RUN mkdir -p /openms

RUN cp -r ${OPENMS_DIR}/openms_build/bin /openms/bin
ENV PATH="/openms/bin:${PATH}"

RUN cp -r ${OPENMS_DIR}/openms_build/lib /openms/lib
ENV LD_LIBRARY_PATH="/openms/lib:${LD_LIBRARY_PATH}"

RUN cp -r ${OPENMS_DIR}/OpenMS/share/OpenMS /openms/share
ENV OPENMS_DATA_PATH="/openms/share/"

FROM compile-openms AS run-app

RUN apt-get update && apt-get install -y --no-install-recommends redis-server nginx \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /var/lib/redis

RUN mkdir -p /workspaces-nuxl-app /mounted-data

ARG PORT=8501
ENV PORT=${PORT}

WORKDIR /app
COPY app.py /app/app.py
COPY src/ /app/src
COPY docs/ /app/docs
COPY assets/ /app/assets
COPY example-data/ /app/example-data
COPY content/ /app/content
COPY .streamlit/config.toml /app/.streamlit/config.toml
COPY clean-up-workspaces.py /app/clean-up-workspaces.py
COPY settings.json /app/settings.json
COPY hooks/ /app/hooks
COPY gdpr_consent/ /app/gdpr_consent
COPY default-parameters.json /app/default-parameters.json

RUN echo "0 3 * * * /root/miniforge3/envs/streamlit-env/bin/python /app/clean-up-workspaces.py >> /app/clean-up-workspaces.log 2>&1" | crontab -

ENV RQ_WORKER_COUNT=1
ENV REDIS_URL=redis://localhost:6379/0
ENV STREAMLIT_SERVER_COUNT=1

COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

RUN /root/miniforge3/bin/mamba run -n streamlit-env python /app/hooks/hook-analytics.py

RUN jq '.online_deployment = true' /app/settings.json > /app/tmp.json && mv /app/tmp.json /app/settings.json

RUN curl -L \
  -o /app/OpenMS-NuXLApp.zip \
  https://github.com/Arslan-Siraj/nuxl-app/releases/download/0.9.0/OpenMS-NuXLApp.zip

EXPOSE $PORT
ENTRYPOINT ["/app/entrypoint.sh"]
