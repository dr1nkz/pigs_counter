FROM nodered/node-red:4.0.2

RUN npm install --no-update-notifier npm@latest && cd /data && npm install node-red-contrib-re-postgres node-red-dashboard node-red-contrib-ui-spinner node-red-node-ui-list node-red-contrib-filesystem

ADD data/auth_set/. /data/.
ADD data/flows/. /data/lib/flows/.

RUN mkdir /data/static

ADD data/static/. /data/static/.
