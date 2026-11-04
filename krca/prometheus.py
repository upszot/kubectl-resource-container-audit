#!/usr/bin/env python3
# krca/prometheus.py - Cliente para consultar Prometheus a través del proxy de Kubernetes

import json
import shutil
import subprocess
import sys
import urllib.parse
from typing import Dict, List, Optional, Tuple


class PrometheusError(Exception):
    """Excepción para errores al interactuar con Prometheus"""
    pass


class PrometheusClient:
    """
    Cliente mínimo para la API HTTP de Prometheus usando el proxy del
    API server de Kubernetes (`kubectl get --raw .../services/http:<svc>:<port>/proxy`).

    No requiere port-forward, ingress ni credenciales adicionales: reutiliza
    el kubeconfig y los permisos RBAC del usuario actual.
    """

    DEFAULT_TIMEOUT = 60
    CANDIDATE_PORTS = (9090, 9091)
    NAME_HINTS = ('prometheus', 'thanos-querier')
    PREFERRED_NAMESPACES = ('monitoring', 'openshift-monitoring', 'prometheus', 'observability')
    # Roles con los que se consulta la API. THANOS/Prometheus exponen el mismo
    # endpoint /api/v1/*, por lo que el cliente es agnóstico al backend.
    MAX_DISCOVERY_ATTEMPTS = 3

    def __init__(
        self,
        namespace: Optional[str] = None,
        service: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        kubectl_bin: Optional[str] = None,
        debug: bool = False,
    ):
        self.namespace = namespace
        self.service = service
        self.timeout = max(int(timeout or self.DEFAULT_TIMEOUT), 1)
        self.kubectl_bin = kubectl_bin or shutil.which('kubectl') or 'kubectl'
        self.debug = debug
        self._target: Optional[Tuple[str, str, int]] = None

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------
    def _log(self, message: str) -> None:
        if self.debug:
            print(f"[krca][prometheus] {message}", file=sys.stderr)

    def _run_kubectl(self, args: List[str], timeout: Optional[int] = None) -> str:
        """Ejecuta kubectl sin shell y devuelve stdout."""
        cmd = [self.kubectl_bin] + args
        try:
            result = subprocess.run(
                cmd,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout or self.timeout,
            )
            return result.stdout.strip()
        except FileNotFoundError:
            raise PrometheusError(
                "No se encontró el binario 'kubectl' en el PATH. "
                "KRCA lo necesita para acceder a Prometheus."
            )
        except subprocess.TimeoutExpired:
            raise PrometheusError(
                f"Tiempo de espera agotado al ejecutar: {' '.join(cmd)}. "
                f"Aumente --prometheus-timeout (actual: {self.timeout}s)."
            )
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or '').strip()
            lowered = stderr.lower()
            if 'forbidden' in lowered or 'unauthorized' in lowered:
                raise PrometheusError(
                    "Sin permisos para consultar Prometheus a través del proxy del API.\n"
                    "Otorgue el permiso 'get' sobre 'services/proxy' en el namespace de Prometheus:\n\n"
                    "  kubectl create role krca-prometheus-proxy \\\n"
                    "    --verb=get --resource=services/proxy -n monitoring\n"
                    "  kubectl create rolebinding krca-prometheus-proxy \\\n"
                    "    --role=krca-prometheus-proxy --user=<su-usuario> -n monitoring\n"
                )
            if 'not found' in lowered or 'notfound' in lowered:
                raise PrometheusError(
                    "No se encontró el servicio de Prometheus indicado.\n"
                    "Use --prometheus-namespace/--prometheus-service o verifique que "
                    "Prometheus esté desplegado en el cluster.\n"
                    f"Detalle: {stderr or 'sin detalle'}"
                )
            raise PrometheusError(
                f"Error ejecutando 'kubectl {' '.join(args)}': {stderr or 'sin detalle'}"
            )

    def _get_json(self, raw_path: str, timeout: Optional[int] = None) -> Dict:
        output = self._run_kubectl(['get', '--raw', raw_path], timeout=timeout)
        try:
            return json.loads(output)
        except ValueError:
            raise PrometheusError(
                f"Respuesta inválida de Prometheus (no es JSON): {output[:200]!r}"
            )

    # ------------------------------------------------------------------
    # Descubrimiento del servicio
    # ------------------------------------------------------------------
    def _list_services(self) -> List[Dict]:
        raw = self._run_kubectl(['get', 'services', '--all-namespaces', '-o', 'json'])
        try:
            return json.loads(raw).get('items', [])
        except ValueError:
            raise PrometheusError("No se pudo interpretar la lista de servicios del cluster")

    @staticmethod
    def _candidate_ports(service: Dict) -> List[int]:
        ports = []
        for port in service.get('spec', {}).get('ports', []) or []:
            number = port.get('port')
            name = (port.get('name') or '').lower()
            if isinstance(number, int) and (
                number in PrometheusClient.CANDIDATE_PORTS
                or name in ('web', 'http-web', 'http')
            ):
                ports.append(number)
        return ports

    def _score_candidate(self, service: Dict, port: int) -> int:
        metadata = service.get('metadata', {})
        name = metadata.get('name', '')
        namespace = metadata.get('namespace', '')
        score = 0

        if namespace in self.PREFERRED_NAMESPACES:
            score += 50
        if port == 9090:
            score += 10
        if name in ('prometheus-kube-prometheus-prometheus', 'prometheus-k8s', 'prometheus'):
            score += 20
        if name.startswith('thanos-querier'):
            score += 15
        if service.get('spec', {}).get('clusterIP') == 'None':
            # Los servicios headless no siempre son accesibles vía proxy
            score -= 30
        # Penalizar servicios de scrape de la kubelet (no son la API de consulta)
        if 'kubelet' in name or 'coredns' in name:
            score -= 100
        return score

    def _explicit_service_candidates(self) -> List[Tuple[str, str, int]]:
        """Resuelve --prometheus-namespace/--prometheus-service a una lista de candidatos."""
        services = self._list_services()
        explicit_ns = self.namespace
        explicit_name = self.service

        # Permitir --prometheus-service=namespace/nombre
        if explicit_name and '/' in explicit_name:
            explicit_ns, explicit_name = explicit_name.split('/', 1)

        scored = []
        for service in services:
            metadata = service.get('metadata', {})
            name = metadata.get('name', '')
            namespace = metadata.get('namespace', '')

            if explicit_name and name != explicit_name:
                continue
            if explicit_ns and namespace != explicit_ns:
                continue
            if not explicit_name and not any(hint in name.lower() for hint in self.NAME_HINTS):
                continue

            for port in self._candidate_ports(service):
                scored.append(
                    (self._score_candidate(service, port), namespace, name, port)
                )

        scored.sort(key=lambda item: item[0], reverse=True)
        return [(namespace, name, port) for _, namespace, name, port in scored]

    def resolve(self) -> Tuple[str, str, int]:
        """Descubre (y cachea) el servicio de Prometheus a utilizar."""
        if self._target:
            return self._target

        candidates = self._explicit_service_candidates()
        if not candidates:
            if self.service:
                raise PrometheusError(
                    f"No se encontró el servicio '{self.service}'"
                    f"{' en el namespace ' + self.namespace if self.namespace else ''} "
                    "con un puerto 9090/9091.\n"
                    "Verifique el nombre con: kubectl get svc -A | grep -i prometheus"
                )
            raise PrometheusError(
                "No se encontró un servicio de Prometheus en el cluster.\n"
                "Verifique que kube-prometheus-stack (o Thanos Querier) esté desplegado "
                "o indique el servicio con --prometheus-namespace/--prometheus-service."
            )

        last_error = None
        for namespace, name, port in candidates[:self.MAX_DISCOVERY_ATTEMPTS]:
            self._log(f"Probando Prometheus en {namespace}/{name}:{port}")
            try:
                self._verify(namespace, name, port)
                self._target = (namespace, name, port)
                self._log(f"Usando {namespace}/{name}:{port}")
                return self._target
            except PrometheusError as e:
                last_error = e

        # Si el usuario indicó un servicio explícito, el error debe ser explícito
        if self.service:
            raise PrometheusError(
                f"No se pudo consultar el servicio indicado ({self.service}): {last_error}"
            )
        raise PrometheusError(
            f"Se encontraron servicios candidatos pero ninguno respondió: {last_error}"
        )

    def _verify(self, namespace: str, service: str, port: int) -> None:
        """Comprueba que el endpoint responde consultando la versión/estado."""
        path = self._proxy_path(namespace, service, port, '/api/v1/query')
        payload = self._get_json(
            f"{path}?{urllib.parse.urlencode({'query': '1'})}",
            timeout=min(self.timeout, 15),
        )
        if payload.get('status') != 'success':
            raise PrometheusError(f"Prometheus respondió con estado inesperado: {payload}")

    @staticmethod
    def _proxy_path(namespace: str, service: str, port: int, api_path: str) -> str:
        return (
            f"/api/v1/namespaces/{namespace}/services/"
            f"http:{service}:{port}/proxy{api_path}"
        )

    @property
    def endpoint(self) -> str:
        namespace, service, port = self.resolve()
        return f"{namespace}/{service}:{port}"

    # ------------------------------------------------------------------
    # API de consulta
    # ------------------------------------------------------------------
    def query(self, expr: str) -> List[Dict]:
        """Consulta instantánea."""
        namespace, service, port = self.resolve()
        params = {'query': expr, 'timeout': f"{self.timeout}s"}
        path = self._proxy_path(namespace, service, port, '/api/v1/query')
        payload = self._get_json(f"{path}?{urllib.parse.urlencode(params)}")
        return self._extract_result(payload)

    def query_range(
        self,
        expr: str,
        start: float,
        end: float,
        step: int,
    ) -> List[Dict]:
        """
        Consulta de rango. Devuelve la lista de series tal cual la entrega
        Prometheus: [{'metric': {...}, 'values': [[ts, 'valor'], ...]}, ...]
        """
        namespace, service, port = self.resolve()
        params = {
            'query': expr,
            'start': f"{start:.3f}",
            'end': f"{end:.3f}",
            'step': str(int(step)),
            'timeout': f"{self.timeout}s",
        }
        path = self._proxy_path(namespace, service, port, '/api/v1/query_range')
        payload = self._get_json(f"{path}?{urllib.parse.urlencode(params)}")
        return self._extract_result(payload)

    def _extract_result(self, payload: Dict) -> List[Dict]:
        if payload.get('status') != 'success':
            error = payload.get('error') or payload.get('errorType') or 'error desconocido'
            raise PrometheusError(f"Prometheus devolvió un error: {error}")
        result = payload.get('data', {}).get('result', [])
        return result if isinstance(result, list) else []

    def health(self) -> bool:
        """Devuelve True si Prometheus responde correctamente."""
        try:
            self._verify(*self.resolve())
            return True
        except PrometheusError:
            return False
