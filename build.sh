docker rmi -f $1:$2
docker build --no-cache -t $1:$2 .
