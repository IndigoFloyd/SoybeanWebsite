# SoybeanWebsite
SoyDNGP, an advanced webserver designed to utilize the power of convolutional neural network-based models for the prediction of agronomic traits in soybean. Built to serve the burgeoning field of agriculture, our server supports the analysis of a comprehensive range of traits.
# The structure of this website
This website is based on a webflow template, and the backend is driven by Flask. In order to ensure high scalability of the data, we have chosen MongoDB as our database.\
The structure is as follows:\
**--templates**\
&emsp;**--index.html**: The entrance of our website.\
&emsp;**--learnmore.html**: The page which contains detailed introduction. Users could learn more about models and so on.\
&emsp;**--contact.html**: If users meet problems that they could't solve or have some suggestion, here they could contact us.\
&emsp;**--errors.html**: When internal error occurs, the website will be redirected to this page.\
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