FROM python:3.7.3-alpine

ARG GIT_TAG=master

RUN echo GIT_TAG=${GIT_TAG}

# install the checker under /usr/local/bin
RUN apk update ; \
    apk upgrade ; \
    apk add git bash build-base ; \
    echo $PATH ; \
    git clone --branch ${GIT_TAG} https://github.com/bitsofinfo/kubernetes-ingress-info.git ; \
    cd /kubernetes-ingress-info; git status; rm -rf .git; cd / ; \
    cp /kubernetes-ingress-info/*.py /usr/local/bin/ ; \
    rm -rf /kubernetes-ingress-info ; \
    pip install --upgrade pip kubernetes twisted diskcache; \
    apk del git build-base bash; \
    ls -al /usr/local/bin ; \
    chmod +x /usr/local/bin/*.py ; \
    rm -rf /var/cache/apk/* ; \
    rm -rf /root/.cache

RUN mkdir -p /opt/kubernetes-ingress-info/cache

ENV PATH="/usr/local/bin/;$PATH"
