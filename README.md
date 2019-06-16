# kubernetes-ingress-info

This project provides a simple REST service that can be deployed to any Kubernetes cluster
that reports whether or not a `host` exists in any `Ingress` deployed to that cluster.

Its **important** that this API does **not** report on the *health* of any given `Ingress` `host`
but specifically whether or not ANY `Ingress` currently exists on the cluster where `kubernetes-ingress-info`
is deployed, regardless of if its backend is actually up. It is intended to be a very lightweight and open
endpoint to interrogate for this status.

This tool was specifically developed to serve as a endpoint for various cloud load-balancers
and DNS services to be able to auto-detect *which* Kubernetes clusters are valid for a specific `host` FQDN.
This can aid in workload migration across various clusters or just enable workloads to be deployed to subsets
of clusters out of many organizational clusters, while letting upstream DNS and or glsb based devices react
accordingly as many of these platforms rely on simple HTTP 200 OK type of "checks".

* [Use case](#usecase)
* [Install/Setup](#req)
* [Example](#example)
* [API](#api)
* [Usage](#usage)


## <a name="usecase"></a>Use case:

This tool was specifically developed to serve as a endpoint for various cloud load-balancers
and DNS services to be able to auto-detect *which* Kubernetes clusters are valid for a specific `host` FQDN.

Lets say you have two apps available at **a.b.com** and **x.y.com** and you have 3 available Kubernetes
it could potentially be deployed on, *clusterA*, *clusterB* and *clusterC*. Generally upstream from your cluster *LoadBalancers*
you will have another cloud load balancer device or you are just using some sort of DNS device to control what cluster *LoadBalancer* IPs are relevant for each application at any given time. So what you can do in this case is list all possible cluster IPs as possible targets for those FQDNs hostname, but enable/disable them based on calls to `kubernetes-ingress-info` which
resides on all clusters. For this to work, you should ensure each possible target cluster `Ingress Controller` that is behind a `LoadBalancer` has `kubernetes-ingress-info` accessible via its own unique `Ingress`.

![diag](/docs/diag1.png "Diagram1")

## <a id="req"></a>Install/Setup

Run via Docker:
https://hub.docker.com/r/bitsofinfo/kubernetes-ingress-info

Otherwise:

**Python 3.6+**

Dependencies: See [Dockerfile](Dockerfile)

When deploying to a Kubernetes cluster the `Pod` that `kubernetes-ingress-info` is
deployed as needs to run as a `serviceAccount` with (at a minimum) a binding to a
`[Cluster]Role` with the following RBAC permissions:

```
...
rules:
- apiGroups: ["extensions"]
  resources: ["ingresses"]
  verbs: ["list"]
```



## <a name="example"></a>Example:

This example will install `kubernetes-ingress-info` onto a Kubernetes cluster.
The [example.yaml](examples/example.yaml) creates a `Namespace`, `ServiceAccount`
with RBAC bindings, a `Deployment`, `Service` and an `Ingress` bound to `host: kubernetes-ingress-info.local`.

The `ServiceAccount` has the ability to `list` all `ingresses` on a cluster. You can modify
and install to your cluster however you see fit.

```
kubectl apply -f examples/example.yaml
```

Once installed, you will need a `/etc/hosts` entry or DNS setup for `kubernetes-ingress-info.local` to
point to the `LoadBalancer` configured for whatever `IngressController` consumed the example `Ingress` in `example.yaml`

Let's hit the root to get a list of all `Ingress` "hosts" on the cluster.
```
curl http://kubernetes-ingress-info.local

[
  "kubernetes-ingress-info.local",
  ....
]
```

Validate the existence of a single `host`, will return a 200
```
curl http://kubernetes-ingress-info.local/kubernetes-ingress-info.local

{
  "info": "'kubernetes-ingress-info.local' found"
}
```

How about one that does not exist? (returns a 404)
```
curl http://kubernetes-ingress-info.local/non-existant-host.com

{
  "error": "'non-existant-host.com' 404 not found"
}
```

## <a name="api"></a>API:

The API is as follows:

GET all Ingress Hosts on the cluster:
```
curl -X GET http[s]://[kubernetes-ingress-info]
```

GET a specific `host`. Returns 200 if `host` exists, or a 404 if non-existant
```
curl -X GET http[s]://[kubernetes-ingress-info]/[host]
```

## <a name="usage"></a>Usage:

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
