# kubernetes-ingress-info


## Usage:

```
bash-4.4$ python3 info.py -h

usage: info.py [-h] [-r LOAD_CONFIG_MODE] [-i INCLUDE_LABEL_SELECTORS]
               [-x EXCLUDE_LABEL_SELECTORS] [-n NAMESPACES] [-p LISTEN_PORT]
               [-l LOG_LEVEL] [-b LOG_FILE]

optional arguments:
  -h, --help            show this help message and exit
  -r LOAD_CONFIG_MODE, --load-config-mode LOAD_CONFIG_MODE
                        How the target k8s cluster config will be loaded,
                        'local' will leverage the current kubectl context from
                        '~/.kube/config', while 'cluster' will talk direct to
                        the cluster the process is executing in using the
                        Pod's configured serviceAccount which needs read
                        access to all objects of type Ingress. Default 'local'
  -i INCLUDE_LABEL_SELECTORS, --include-label-selectors INCLUDE_LABEL_SELECTORS
                        Optional comma delimited of Ingress
                        label1=value,label2=value pairs that will be used to
                        build the database of IngressInfo objects available to
                        be fetched. If specified, ONLY Ingress objects having
                        ALL specified labels will be retrieved. If not
                        specified, ALL available Ingress objects will be
                        retrieved from k8s. Excludes take precendence over
                        includes.
  -x EXCLUDE_LABEL_SELECTORS, --exclude-label-selectors EXCLUDE_LABEL_SELECTORS
                        Optional comma delimited of Ingress
                        label1=value,label2=value pairs that will be used to
                        restrict the database of IngressInfo objects available
                        to be fetched. If specified, ONLY Ingress objects NOT
                        having ANY of the specified labels will be retrieved.
                        If not specified, ALL available Ingress objects will
                        be retrieved from k8s. Excludes take precendence over
                        includes.
  -n NAMESPACES, --namespace NAMESPACES
                        Optional comma delimited of Namespaces to scope
                        Ingress fetch within
  -p LISTEN_PORT, --listen-port LISTEN_PORT
                        Port to listen on, default 8081
  -l LOG_LEVEL, --log-level LOG_LEVEL
                        log level, default DEBUG
  -b LOG_FILE, --log-file LOG_FILE
                        Path to log file, default None, STDOUT
```                        
