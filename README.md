# kubectl-resource-container-audit (KRCA)

`kubectl-resource-container-audit` (alias `kubectl krca`) 
> Es un plugin de línea de comandos para `kubectl` que permite **auditar el uso de CPU y memoria** en contenedores de Kubernetes/OpenShift, </br>
> destacando posibles problemas de configuración de recursos mediante un sistema de **colores visuales**.

Ideal para detectar:

- Uso excesivo de CPU o memoria
- Configuraciones incorrectas o ausentes de `requests` o `limits`
- Contenedores infrautilizados o sobreasignados
- Estados de error o reinicios frecuentes

---

## 🔧 Instalación

1. **Descargar el script**:

```sh
curl -Lo /usr/local/bin/kubectl-resource-container-audit.py https://raw.githubusercontent.com/upszot/kubectl-resource-container-audit/refs/heads/master/kubectl-resource-container-audit.py

chmod +x /usr/local/bin/kubectl-resource-container-audit.py
```

2. **Crear un enlace simbólico para registrarlo como plugin de kubectl:**
```sh
sudo ln -s /usr/local/bin/kubectl-resource-container-audit.py /usr/local/bin/kubectl-krca
```
Ahora podés usar el comando como:
```sh
kubectl krca
```

🚀 Uso básico

```sh
kubectl krca --help
```
![KRCA en acción](.img/krca-help.png)

🎨 Sistema de colores

Color	Significado </br>
🔴 Rojo	Uso > danger-pct o uso > limit. Estado CrashLoopBackOff. </br>
🟡 Amarillo	Uso > warning-pct. Requests o limits no definidos. Terminated: Completed. </br>
🟢 Verde	Uso normal entre request y limit. Estado: Running. </br>
🔵 Azul	Infrautilización (< underuse-pct). Otros estados (Waiting, etc). </br>
🟣 Púrpura	Diferencia excesiva entre requests y limits. </br>



📊 Ejemplo de salida
```sh
NAMESPACE     POD              CONTAINER   CPU   REQ_CPU  LIM_CPU  MEMORY  REQ_MEM  LIM_MEM  STATUS        RESTARTS
default       app-abc-xyz      main        120m  100m     200m     90Mi    128Mi    512Mi    Running       0
default       job-123-fail     worker      10m   -        -        12Mi    -        -        CrashLoop...  4
```
Con colores según lo explicado anteriormente.

✅ Requisitos
 - Python 3.6+
 - kubectl configurado con acceso a un cluster válido
 - Acceso a permisos para listar pods y contenedores (kubectl get pods -A -o json)


🧑‍💻 Autor
Desarrollado por @upszot para entornos Kubernetes y OpenShift.

📄 Licencia
[GPL 3.0](./LICENSE)
