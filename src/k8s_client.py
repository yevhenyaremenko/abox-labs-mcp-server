"""Kubernetes client initialization with in-cluster / local fallback."""

from kubernetes import client, config
from kubernetes.client import CoreV1Api, AppsV1Api


def _load_config() -> None:
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()


def core_v1() -> CoreV1Api:
    _load_config()
    return client.CoreV1Api()


def apps_v1() -> AppsV1Api:
    _load_config()
    return client.AppsV1Api()
