# Jupyter Stack
#### Analytics and Data Science Notebook for the Datastack

This part can be used standalone. If the ElasticStack is running, its data can be fetched.

* [Spark 2.1.1](http://spark.apache.org/docs/2.1.1)
* [Hadoop 2.7.3](http://hadoop.apache.org/docs/r2.7.3)
* [PySpark](http://spark.apache.org/docs/2.1.1/api/python)
* [Anaconda3-5](https://www.anaconda.com/distribution/)



The easiest way to feed data into the DataStack is to use the
[datastack-adapter](https://github.com/iot-salzburg/dtz_datastack/tree/master/datastack-adapter) to stream data
from the [panta-rhei messaging system](https://github.com/iot-salzburg/dtz_datastack/tree/master/elasticStack).

## Contents

1. [Requirements](../README.md) (parent directory)
1. [Configuration](#configuration)
2. [Quickstart](#quickstart)
2. [Deployment](#deployment)


## Configuration

Set the password in `jupyter/jupyter_notebook_config.json`. Therefore, hash your 
password in the form: (password)(salt) using a sha1 hash generator, 
e.g. [hashgenerator.de](https://hashgenerator.de/). Then update the config file as shown below:

```json
{
  "NotebookApp": {
    "password": "sha1:e49e73b0eb0e:353c38d87d79527e57da1bba5f65046d0b376d95"
  }
}
```

## Quickstart

Running these commands will build, push and deploy the stack:

**Check if the paths in 'docker-compose.yml' do exist and are syncronized!**

```bash
sudo docker-compose -f jupyter/docker-compose.yml up --build
```

With these commands we can see if everything worked well:
```bash
docker-compose -f jupyter/docker-compose.yml ps
docker logs jupyter_jupyter_1
```


## Deployment

Running these commands will build, push and deploy the stack:

**Check if the paths in 'docker-compose.yml' do exist and are syncronized!**

```bash
./jupyter/start_jupyter.sh
```

With these commands we can see if everything worked well:
```bash
./jupyter/show_jupyter.sh
docker service ps jupyter_jupyter
```

##  Services

Open [http://localhost:8888](http://localhost:8888/lab) with a web browser.


### Tracing

Watch if everything worked fine with:
```bash
sudo docker service ls
sudo docker service logs -f service-name
sudo docker service ps service-name --no-trunc
```
