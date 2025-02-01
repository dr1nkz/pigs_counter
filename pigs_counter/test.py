import cv2


def stream(address):  # , camera, event_id):
    """
    Запуск модели
    """

    # cv2.namedWindow('stream', cv2.WINDOW_NORMAL)
    cap = cv2.VideoCapture(address)
    print(cap)
    print(cap.isOpened())
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f'fps:{fps}  width:{width}  height:{height}')
    out = cv2.VideoWriter('appsrc ! videoconvert' +
                          ' ! video/x-raw,format=I420' +
                          ' ! x264enc speed-preset=ultrafast bitrate=600 key-int-max=' + str(fps * 2) +
                          ' ! video/x-h264,profile=baseline' +
                          ' ! rtspclientsink location=rtsp://mediamtx:8554/mystream ',
                          cv2.CAP_GSTREAMER, 0, fps, (width, height), True)
    # out = cv2.VideoWriter('appsrc ! videoconvert ! '
    #     'x264enc noise-reduction=10000 speed-preset=ultrafast tune=zerolatency ! '
    #     'rtph264pay config-interval=1 pt=96 !'
    #     'tcpserversink host=172.19.0.2 port=8554 sync=false',
    #     0, fps, (width, height))

    if not out.isOpened():
        raise Exception("can't open video writer")

    while cap.isOpened():  # and end_time is None:
        # Кадр с камеры
        ret, frame = cap.read()
        if not ret:
            break
        # cv2.imshow('stream', frame)
        out.write(frame)
        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #     break

    # cv2.destroyAllWindows()
    cap.release()


stream('videos/1.mp4')
