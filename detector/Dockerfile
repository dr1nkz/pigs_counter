FROM python:3.10.12

WORKDIR /app

# RUN apt-get update && apt-get install ffmpeg libsm6 libxext6 git -y
COPY ./script.sh .
RUN /bin/bash ./script.sh

# RUN apt-get install --quiet -y --no-install-recommends   gstreamer1.0-gl   gstreamer1.0-opencv   gstreamer1.0-plugins-bad   gstreamer1.0-plugins-good   gstreamer1.0-plugins-ugly   gstreamer1.0-tools   libgstreamer-plugins-base1.0-dev   libgstreamer1.0-0   libgstreamer1.0-dev \
#     OPENCV_VER="master" \
#     TMPDIR=$(mktemp -d) \
#     cd "${TMPDIR}" \
#     git clone --branch ${OPENCV_VER} --depth 1 --recurse-submodules --shallow-submodules https://github.com/opencv/opencv-python.git opencv-python-${OPENCV_VER} \
#     cd opencv-python-${OPENCV_VER} \
#     export ENABLE_CONTRIB=0 \
#     export ENABLE_HEADLESS=1 \
#     export CMAKE_ARGS="-DWITH_GSTREAMER=ON" \
#     python3 -m pip wheel . --verbose \
#     python3 -m pip install opencv_python*.whl
