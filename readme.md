# CIIPro: a new read-across portal to fill data gaps using public large-scale chemical and biological data #

[CIIPro](ciipro.rutgers.edu) is a website written in Python using the microframework [Flask](http://flask.pocoo.org/). CIIPro seeks to be a 
chemical analysis tool by allowing users to extract biological data associated with chemicals, find _in vitro_-_in vivo_
correlations, and use biological and chemical features to make assessments on a variety of chemical endpoints.  

The CIIPro website was created and is maintained by [Daniel P. Russo](www.danielprusso) ([@russodanielp](https://twitter.com/russodanielp))
within the [Zhu Research Group](https://zhu.camden.rutgers.edu/) at [Rutgers University](camden.rutgers.edu).

Contributing to CIIPro is welcomed as well as feedback for new features.  More information on contributing or 
feature suggestions can be found below.  Questions are encouraged and can be addressed to danrusso@scarletmail.rutger.edu.

### Feature Request ###

To request a feature or report a bug, please use [Issue Tracker](https://github.com/russodanielp/ciipro/issues).



### Docker ###

The preferred method of CIIPro development current is by using [Docker](https://www.docker.com/). 


SQLIte in docker: https://stackoverflow.com/questions/33711818/embed-sqlite-database-to-docker-container.

### Saving Images and deploying them using Docker ###

Saving the current image as an easy way to deploy to a server from the local development machine
First, save the current image using the following command:

```shell script
docker save ciipro:latest | gzip > ciiproimage_latest.tar.gz
```

Then, the image can be transfered to the host machine and loaded like so:

```shell script
gunzip -c ciiproimage_latest.tar.gz | docker load
```


### Color Codes ###

Deep blue - #05056F
Blue - #0505FF
Light blue - #6FA5FF
Aqua - #DAFBFF
