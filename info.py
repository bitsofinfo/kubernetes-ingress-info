#!/usr/bin/env python

__author__ = "bitsofinfo"

from kubernetes import client, config
import pprint
import argparse
import sys
import logging
import json
from twisted.web import server, resource
from twisted.internet import reactor, endpoints
import time
import threading
from diskcache import Cache


class IngressInfo(resource.Resource):
    isLeaf = True
    load_config_mode = "local"
    v1Api = None
    exclude_label_selectors = None
    include_label_selectors = None
    namespaces = None
    cache = None
    cache_ttl_seconds = 300
    host_match_on_header = None

    # initialize our client for proper k8s config
    def init(self):
        if self.load_config_mode == "local":
            config.load_kube_config()
        else:
            config.load_incluster_config()

        self.v1Api = client.ExtensionsV1beta1Api()

    # fetches the Ingress database
    def getIngressDb(self):

        if self.cache is not None:
            cachedIngressDb = self.cache.get(b'INGRESS_DB')
            if cachedIngressDb is not None:
                return cachedIngressDb


        fetchedIngresses = []

        # fetch across ALL namespaces
        if self.namespaces is None:
            if self.include_label_selectors is not None:
                logging.debug("getIngressDb() from k8s: fetching (namespace=*) only Ingress w/ label selectors: %s" % self.include_label_selectors)
                k8sIngresses = self.v1Api.list_ingress_for_all_namespaces(watch=False, \
                    label_selector=self.include_label_selectors)
                fetchedIngresses.extend(k8sIngresses.items)
            else:
                logging.debug("getIngressDb() from k8s: fetching (namespace=*)")
                k8sIngresses = self.v1Api.list_ingress_for_all_namespaces(watch=False)
                fetchedIngresses.extend(k8sIngresses.items)

        # fetch within namespace
        else:
            for namespace in self.namespaces:
                if self.include_label_selectors is not None:
                    logging.debug("getIngressDb() from k8s: fetching (namespace=%s) only Ingress w/ label selectors: %s" % namespace,self.include_label_selectors)
                    nsIngresses = self.v1Api.list_namespaced_ingress(namespace, watch=False, \
                        label_selector=self.include_label_selectors)
                    fetchedIngresses.extend(nsIngresses.items)
                else:
                    logging.debug("getIngressDb() from k8s: fetching (namespace=%s)" % namespace)
                    nsIngresses = self.v1Api.list_namespaced_ingress(namespace, watch=False)
                    fetchedIngresses.extend(nsIngresses.items)



        ingressDb = { 'unique_hosts':set() }
        for i in fetchedIngresses:

            excludeIngress = False
            if self.exclude_label_selectors is not None:
                for exlbl,exlblval in self.exclude_label_selectors.items():
                    ingressLabelNames = i.metadata.labels.keys()
                    if exlbl in ingressLabelNames and i.metadata.labels[exlbl] == exlblval:
                        logging.debug("getIngressDb() excluding Ingress: \"%s:%s\" due to exclude label: \"%s=%s\"" % (i.metadata.namespace,i.metadata.name,exlbl,exlblval))
                        excludeIngress = True
                        break;

            if excludeIngress:
                continue;

            for r in i.spec.rules:
                ingressInfo = { 'host':r.host.lower() }
                ingressDb['unique_hosts'].add(r.host.lower())

        if self.cache is not None:
            self.cache.set(b'INGRESS_DB', value=ingressDb, expire=self.cache_ttl_seconds)

        return ingressDb


    # The main servicing method
    def render_GET(self, request):

        toReturn = {}
        try:
            ingressDb = self.getIngressDb()

            requestUri = request.uri.decode('utf-8')

            # if just a root request, send the contents of the ingressDb
            if requestUri == "/":
                toReturn =  list(ingressDb['unique_hosts']) # convert to List for json...

            # otherwise we assume the request is checking a fqdn/host existence in ingressDb
            else:
                # assume the uri path is a host
                hostToCheck = requestUri.replace("/","")
                if hostToCheck.lower() in ingressDb['unique_hosts']:
                    toReturn = {'info':("'%s' found" % hostToCheck)}

                # if host-match-on-header was specified... check for it
                elif self.host_match_on_header and \
                     self.host_match_on_header.strip() != "" and \
                     requestUri.getHeader(self.host_match_on_header) and \
                     requestUri.getHeader(self.host_match_on_header).strip() != "" and \
                     requestUri.getHeader(self.host_match_on_header).lower() in ingressDb['unique_hosts']:
                    
                    toReturn = {'info':("'%s' found" % requestUri.getHeader(self.host_match_on_header))}

                # otherwise no match
                else:
                    toReturn = {'error':("'%s' 404 not found" % hostToCheck)}
                    request.setResponseCode(404)

        except Exception as e:
            error = "failure: " + str(sys.exc_info())
            toReturn = {'error':("500 failure: %s" % error)}
            request.setResponseCode(500)
            logging.exception("render_GET unexpected error: " + error)

        finally:
            return json.dumps(toReturn, indent=2).encode("UTF-8")


def init(load_config_mode, \
         listen_port, \
         enable_cache, \
         cache_dir, \
         cache_ttl_seconds, \
         include_label_selectors, \
         exclude_label_selectors, \
         namespaces, \
         host_match_on_header):

    try:
        endpoint = IngressInfo()
        endpoint.load_config_mode = load_config_mode
        endpoint.include_label_selectors = include_label_selectors
        endpoint.exclude_label_selectors = exclude_label_selectors
        endpoint.namespaces = namespaces
        endpoint.host_match_on_header = host_match_on_header
        if enable_cache:
            logging.info("init() caching enabled @ %s (TTL %d seconds)" % (cache_dir, cache_ttl_seconds))
            endpoint.cache = Cache(cache_dir)
            endpoint.cache_ttl_seconds = cache_ttl_seconds
        endpoint.init()
        endpoints.serverFromString(reactor, "tcp:" + str(listen_port)).listen(server.Site(endpoint))


        # start it up
        httpdthread = threading.Thread(target=reactor.run,args=(False,))
        httpdthread.daemon = True
        httpdthread.start()

        logging.info("init() listening on %d" % listen_port)

        try:
            while True:
                time.sleep(30)
        except KeyboardInterrupt:
            print("Exiting...")


    except Exception as e:
        logging.exception("init() unexpected error: " +  str(sys.exc_info()))
        sys.exit(1)


###########################
# Main program
##########################
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--load-config-mode', dest='load_config_mode', default="local", \
        help="How the target k8s cluster config will be loaded, 'local' will leverage the current kubectl context from '~/.kube/config', while 'cluster' will talk direct to the cluster the process is executing in using the Pod's configured serviceAccount which needs read access to all objects of type Ingress. Default 'local'")
    parser.add_argument('-i', '--include-label-selectors', dest="include_label_selectors", default=None, \
        help="Optional comma delimited of Ingress label1=value,label2=value pairs that will be used to build the database of IngressInfo objects available to be fetched. If specified, ONLY Ingress objects having ALL specified labels will be retrieved. If not specified, ALL available Ingress objects will be retrieved from k8s. Excludes take precendence over includes.")
    parser.add_argument('-x', '--exclude-label-selectors', dest="exclude_label_selectors", default=None, \
        help="Optional comma delimited of Ingress label1=value,label2=value pairs that will be used to restrict the database of IngressInfo objects available to be fetched. If specified, ONLY Ingress objects NOT having ANY of the specified labels will be retrieved. If not specified, ALL available Ingress objects will be retrieved from k8s. Excludes take precendence over includes.")
    parser.add_argument('-n', '--namespace', dest="namespaces", default=None, \
        help="Optional comma delimited of Namespaces to scope Ingress fetch within")
    parser.add_argument('-m', '--host-match-on-header', dest="host_match_on_header", default=None, \
        help="Optional name of HTTP Request header who's value will be inspected for an Ingress host match, should the default path based /[host] not find a match.")
    parser.add_argument('-p', '--listen-port', dest='listen_port', \
        help="Port to listen on, default 8081", type=int, default=8081)
    parser.add_argument('-c', '--enable-cache', action='store_true', default=False, \
        help="Optional, enabling caching (uses https://github.com/grantjenks/python-diskcache)")
    parser.add_argument('-e', '--cache-ttl-seconds', dest="cache_ttl_seconds", type=int, default=30, \
        help="Optional, cache TTL in seconds")
    parser.add_argument('-d', '--cache-dir', dest="cache_dir", default="/opt/kubernetes-ingress-info/cache", \
        help="Optional, cache dir, default /opt/kubernetes-ingress-info/cache")
    parser.add_argument('-l', '--log-level', dest='log_level', default="DEBUG", \
        help="log level, default DEBUG ")
    parser.add_argument('-b', '--log-file', dest='log_file', default=None, \
        help="Path to log file, default None, STDOUT")

    args = parser.parse_args()

    dump_help = False

    if dump_help:
        parser.print_help()
        sys.exit(1)

    logging.basicConfig(level=logging.getLevelName(args.log_level),
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        filename=args.log_file,filemode='w')
    logging.Formatter.converter = time.gmtime

    dictExcludeLabelSelectors = None
    if args.exclude_label_selectors is not None:
        dictExcludeLabelSelectors = {}
        for raw in args.exclude_label_selectors.split(","):
            dictExcludeLabelSelectors[raw.split("=")[0]] = raw.split("=")[1]

    listNamespaces = None
    if args.namespaces is not None:
        listNamespaces = args.namespaces.split(",")

    # invoke!
    init(args.load_config_mode, \
         args.listen_port,
         args.enable_cache,
         args.cache_dir,
         args.cache_ttl_seconds,
         args.include_label_selectors,
         dictExcludeLabelSelectors,
         listNamespaces,
         args.host_match_on_header)
