#!/usr/bin/env python3
# krca/kubectl.py - Módulo para interacción con Kubernetes

import json
import subprocess
from typing import Dict, List, Optional, Tuple, Union

class KubectlError(Exception):
    """Excepción personalizada para errores de kubectl"""
    pass

class KubectlClient:
    """Cliente para interactuar con kubectl"""

    @staticmethod
    def execute(cmd: str, ignore_errors: bool = False) -> str:
        """
        Ejecuta un comando de kubectl y retorna la salida
        
        Args:
            cmd: Comando completo a ejecutar
            ignore_errors: Si True, no lanza excepción en errores
            
        Returns:
            Salida del comando
            
        Raises:
            KubectlError: Si el comando falla y ignore_errors es False
        """
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            if ignore_errors:
                return ""
            error_msg = f"Error ejecutando comando: {e.cmd}\n"
            error_msg += f"Código: {e.returncode}\n"
            error_msg += f"Error: {e.stderr.strip()}"
            raise KubectlError(error_msg)

    @staticmethod
    def get_pods(namespace: Optional[str] = None, all_namespaces: bool = False) -> Dict:
        """
        Obtiene la lista de pods en formato JSON
        
        Args:
            namespace: Namespace específico (opcional)
            all_namespaces: Si True, obtiene pods de todos los namespaces
            
        Returns:
            Diccionario con la lista de pods en formato JSON
        """
        cmd = "kubectl get pods "
        if all_namespaces:
            cmd += "-A "
        elif namespace:
            cmd += f"-n {namespace} "
        else:
            cmd += f"-n {KubectlClient.get_current_namespace()} "
        cmd += "-o json"
        output = KubectlClient.execute(cmd)
        return json.loads(output)

    @staticmethod
    def get_current_namespace() -> str:
        """
        Obtiene el namespace actual del contexto
        
        Returns:
            Nombre del namespace actual
        """
        cmd = "kubectl config view --minify -o jsonpath='{..namespace}'"
        namespace = KubectlClient.execute(cmd, ignore_errors=True)
        return namespace if namespace else "default"

    @staticmethod
    def get_metrics(namespace: Optional[str] = None, all_namespaces: bool = False) -> Dict:
        """
        Obtiene las métricas de uso de recursos con validación de formatos
        
        Args:
            namespace: Namespace específico (opcional)
            all_namespaces: Si True, obtiene métricas de todos los namespaces
            
        Returns:
            Diccionario con las métricas organizadas por pod y contenedor
        """
        try:
            cmd = "kubectl top pods --no-headers --containers"
            if all_namespaces:
                cmd += " -A"
            elif namespace:
                cmd += f" -n {namespace}"
            else:
                cmd += f" -n {KubectlClient.get_current_namespace()}"
            
            output = KubectlClient.execute(cmd, ignore_errors=True)
            metrics = {}
            
            for line in output.splitlines():
                parts = line.split()
                if not parts:
                    continue
                    
                if all_namespaces and len(parts) >= 5:
                    ns, pod, container = parts[0], parts[1], parts[2]
                    cpu, memory = parts[3], parts[4]
                elif not all_namespaces and len(parts) >= 4:
                    ns = namespace or KubectlClient.get_current_namespace()
                    pod, container = parts[0], parts[1]
                    cpu, memory = parts[2], parts[3]
                else:
                    continue
                
                # Validar y normalizar el formato de memoria
                if memory != "-":
                    if memory.endswith('m'):  # Si es CPU (milicores)
                        pass  # No hacer nada, es válido
                    elif not any(x in memory for x in ['Ki', 'Mi', 'Gi']):
                        if memory.isdigit():
                            memory = f"{memory}Mi"  # Asumir MiB si no tiene unidad
                        else:
                            memory = "-"  # Valor inválido
                
                if pod not in metrics:
                    metrics[pod] = {}
                
                metrics[pod][container] = {
                    "cpu": cpu,
                    "memory": memory,
                    "namespace": ns
                }
            
            return metrics
        
        except KubectlError:
            return {}

    @staticmethod
    def get_pod_status(pod: Dict) -> Tuple[str, int]:
        """
        Obtiene el estado y conteo de reinicios de un pod
        
        Args:
            pod: Diccionario con la definición del pod
            
        Returns:
            Tupla con (estado, reinicios)
        """
        status = pod.get("status", {})
        container_statuses = status.get("containerStatuses", [])
        
        if not container_statuses:
            return "Unknown", 0
        
        # Tomamos el estado del primer contenedor
        container_status = container_statuses[0]
        state = container_status.get("state", {})
        restart_count = container_status.get("restartCount", 0)
        
        if "running" in state:
            return "Running", restart_count
        elif "waiting" in state:
            reason = state["waiting"].get("reason", "Unknown")
            return f"Waiting: {reason}", restart_count
        elif "terminated" in state:
            reason = state["terminated"].get("reason", "Unknown")
            return f"Terminated: {reason}", restart_count
        
        return "Unknown", restart_count

    @staticmethod
    def get_node_info(pod: Dict) -> Tuple[str, str]:
        """
        Obtiene información del nodo donde está alojado el pod
        
        Args:
            pod: Diccionario con la definición del pod
            
        Returns:
            Tupla con (node_ip, node_name)
        """
        try:
            node_ip = pod["status"]["hostIP"]
        except KeyError:
            node_ip = "<none>"
        
        try:
            node_name = pod["spec"]["nodeName"]
        except KeyError:
            node_name = "<none>"
        
        return node_ip, node_name

    @staticmethod
    def get_container_resources(pod: Dict) -> List[Dict]:
        """
        Extrae las configuraciones de recursos de los contenedores
        
        Args:
            pod: Diccionario con la definición del pod
            
        Returns:
            Lista de diccionarios con recursos por contenedor
        """
        containers = []
        for container in pod["spec"].get("containers", []):
            resources = container.get("resources", {})
            limits = resources.get("limits", {})
            requests = resources.get("requests", {})
            
            containers.append({
                "name": container["name"],
                "req_cpu": requests.get("cpu", "<none>"),
                "req_mem": requests.get("memory", "<none>"),
                "lim_cpu": limits.get("cpu", "<none>"),
                "lim_mem": limits.get("memory", "<none>"),
            })
        
        return containers

    @staticmethod
    def check_connection() -> bool:
        """
        Verifica la conexión con el cluster Kubernetes
        
        Returns:
            True si la conexión es exitosa, False en caso contrario
        """
        try:
            KubectlClient.execute("kubectl cluster-info")
            return True
        except KubectlError:
            return False
