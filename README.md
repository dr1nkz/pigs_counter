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
### Run the app
```bash
docker compose up -d
```
## App
the **UI** (nodered) is running on http://**host_ip**:1855/ui<br/>
the **FILEBROWSER** is running on http://**host_ip**:80
