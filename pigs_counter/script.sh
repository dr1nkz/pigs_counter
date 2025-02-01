apt-get update && apt-get install --quiet -y --no-install-recommends \
  gstreamer1.0-gl \
  gstreamer1.0-opencv \
  gstreamer1.0-plugins-bad \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-ugly \
  gstreamer1.0-tools \
  libgstreamer-plugins-base1.0-dev \
  libgstreamer1.0-0 \
  libgstreamer1.0-dev \
  gstreamer1.0-rtspв

OPENCV_VER="master"
TMPDIR=$(mktemp -d)

# Build and install OpenCV from source.
cd "${TMPDIR}"
git clone --branch ${OPENCV_VER} --depth 1 --recurse-submodules --shallow-submodules https://github.com/opencv/opencv-python.git opencv-python-${OPENCV_VER}
cd opencv-python-${OPENCV_VER}
export ENABLE_CONTRIB=0
export ENABLE_HEADLESS=1
# We want GStreamer support enabled.
export CMAKE_ARGS="-DWITH_GSTREAMER=ON"
python3 -m pip wheel . --verbose

# Install OpenCV
pip install numpy==1.26
python3 -m pip install opencv_python*.whl