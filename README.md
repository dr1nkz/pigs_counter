# Pigs counter
## First start
mediamtx is running in **network_mode: "host"**<br/>
### Set the variables in **pigs_counter/.env** file as follows
set the **CAM_ADDRESS** to rtsp://**host_ip**:8554/cam<br/>
set the **LADDER_CAM_ADDRESS** to rtsp://**host_ip**:8554/ladder_cam<br/>
### Set the address of cameras in **mediamtx/mediamtx.yml** file as follows
```yaml
paths:
  cam:
    source: CAM_ADDRESS
  ladder_cam:
    source: LADDER_CAM_ADDRESS
```
If you want to stream video as camera, you need to comment the previous string in **mediamtx/mediamtx.yml** and use the  following **ffmpeg** commands</br>
```bash
ffmpeg -re -stream_loop -1 -i cam.mp4 -c:v copy -f rtsp rtsp://localhost:8554/cam
ffmpeg -re -stream_loop -1 -i ladder_cam.mp4 -c:v copy -f rtsp rtsp://localhost:8554/ladder_cam
```
### Set up the model
Put the pigs model in **pigs_counter/pigs_yolo_nas_v1** and ladder_model in **pigs_counter/ladder_yolo_nas_v1**</br>
Set the values in **pigs_counter/.env** as follows</br>
```
MODEL_PATH = /pigs_counter/pigs_yolo_nas_v1/PIGS_YOLO_NAS_MODEL
LADDER_MODEL_PATH = /pigs_counter/ladder_yolo_nas_v1/LADDER_YOLO_NAS_MODEL
```
### Run the app
```bash
docker compose up -d
```
## App
the **UI** (nodered) is running on http://**host_ip**:1855/ui<br/>
the **FILEBROWSER** is running on http://**host_ip**:80
