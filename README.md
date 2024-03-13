# SoybeanWebsite
SoyDNGP is an advanced web server designed to utilize the power of convolutional neural network-based models for the prediction of agronomic traits in soybean. Built to serve the burgeoning field of agriculture, our server supports the analysis of a comprehensive range of traits. **SoyDNGP is open source, but only used for academic research. If commercial use is required, please contact us.**\
👉 --------------------2023.9.13 update--------------------\
👉 We have refactored SoyDNGP and added features such as customizing the model structure and training our own dataset. Please read https://github.com/IndigoFloyd/SoyDNGPNext for more information.\
⭐ **Star us if you like our work!**
# The structure of this website
This website is based on a webflow template, and the backend is driven by Flask. In order to ensure the high scalability of the data, we have chosen MongoDB as our database. And because the workers created by Gunicorn are independent of each other, their data is not connected, and the session of Flask is relatively unstable, we need to introduce Redis as the "global variable manager".\
The structure is as follows:\
**--templates**\
&emsp;**--index.html**: The entrance of our website.\
&emsp;**--learnmore.html**: The page which contains detailed introduction. Users could learn more about models and so on.\
&emsp;**--contact.html**: If users meet problems that they couldn't solve or have some suggestions, here they could contact us.\
&emsp;**--errors.html**: When an internal error occurs, the website will be redirected to this page.\
&emsp;**--lookup.html**: Input IDs and check traits options, users could look up needed data from our database. Multi-search is allowed, just make IDs split by ';'.\
&emsp;**--predict.html**: Users could upload their own file (\*.vcf) and choose traits to predict. They could also decide whether to join our database or not.\
&emsp;**--thanksforcontact.html**: If email is sent to us succesfully, the **contact.html** page will be redirected to here.\
# The structure of this project
**--templates**: Contains \*.html.\
**--static**\
&emsp;**--css**: Contains \*.css.\
&emsp;**--js**: Contains \*.js.\
&emsp;**--image**: Contains images showed on the websites.\
**--predict**\
&emsp;**--weight**: Contains the weights files.\
&emsp;**--n_trait.txt**: Contains quantitative traits.\
&emsp;**--p_trait.txt**: Contains qualitative traits.\
&emsp;**--snp.txt**: Contains mutation sites of Single-nucleotide polymorphism to be matched.\
# Diagrams
In order to demonstrate the operation principle of web pages more clearly, we have drawn two UML diagrams.
## The component diagram
![image](https://github.com/IndigoFloyd/SoybeanWebsite/blob/main/Component%20Diagram.png)
## The sequence diagram
![image](https://github.com/IndigoFloyd/SoybeanWebsite/blob/main/Sequence%20Diagram.png)
# How to deploy it
## Needed environment
1.&emsp;Needed packages are listed in the **requirements.txt**, use ```pip install -r requirements.txt``` to install them.\
2.&emsp;For softwares this project depends on, **Redis**, **MongoDB** and **Nginx** are significant. You can monitor the changes of Redis by commands ```127.0.0.1:6379>MONITOR```, and manage visualized Mongodb databases by **MongoDB Compass**, which is also officially recommended. A simple Flask built-in web server is prone to socket issues when under high pressure, as it is single-process and single-thread. Using **Gunicorn** to start significantly improves response speed and capability. In the configuration, workers specify the number of processes to start, and the CPU loss is averaged across each process. Gunicorn could be installed easily by ```pip install gunicorn``` on the Linux system.
## Some custom changes
## Start services
1.&emsp;Rewrite **nginx.conf**, ensure that the port forwarded by nginx and the address pointed to are correct, and that the port is opened in the local firewall. A simple example is as follow:
```
server {
        listen       80;
        server_name  xtlab.hzau.edu.cn;

        #charset koi8-r;

        #access_log  logs/host.access.log  main;

        location / {
            client_max_body_size 1024m;
            proxy_pass http://127.0.0.1:8000;  # Gunicorn's working port
            proxy_set_header Host $proxy_host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
}
```
Then, just start Nginx, MongoDB and Redis server. If you want to remote MongoDB, some **frp** configuration might be needed, and you should reset **/etc/mongod.conf**.
```
# network interfaces
net:
  port: 27017
  bindIp: 0.0.0.0
```
2.&emsp;Start Gunicorn.
```
# 20 workers and 300s timeout
gunicorn -w 20 --preload website:app --time 300 --max-requests 5
```

