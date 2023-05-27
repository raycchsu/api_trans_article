FROM api_base:1.0

COPY api/ /BaseApi/api

RUN chmod a+wx /BaseApi/api

# Run api when the container launches
ENTRYPOINT [ "/bin/bash","/BaseApi/api/boot.sh" ]
