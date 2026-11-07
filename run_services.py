"""
Multi-Service Cluster Supervisor & Deployment Runner for AgentEcom.
Coordinates and boots:
1. Service 1 (API & Web Storefront): uvicorn agentecom.api.main:app --port 8000
2. Service 2 (FastMCP Server): uvicorn agentecom.mcp.service:app --port 8001
3. Service 3 (Indexing Worker Daemon): python -m agentecom.search.run_worker

If Docker daemon is active, can also orchestrate via 'docker-compose up -d'.
"""

import os
import sys
import time
import subprocess
import signal
import shutil

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PYTHON_EXE = sys.executable

def is_docker_running() -> bool:
    """Check if Docker daemon is active and responsive."""
    try:
        res = subprocess.run(["docker", "info"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=4)
        return res.returncode == 0
    except Exception:
        return False

def deploy_docker():
    """Deploy using Docker Compose."""
    print("=" * 70)
    print("🐳 DEPLOYING AGENTECOM MICROSERVICES VIA DOCKER COMPOSE")
    print("=" * 70)
    cmd = ["docker-compose", "up", "--build", "-d"]
    subprocess.run(cmd)
    print("\n✅ Services launched in background:")
    print("   - API & Storefront: http://localhost:8000")
    print("   - FastMCP Server:   http://localhost:8001")
    print("   - Search Worker:    Running in container 'agentecom-worker'")
    print("\nRun 'docker-compose logs -f' to view aggregated live logs.")
    print("Run 'docker-compose down' to stop the stack.")

def run_local_cluster():
    """Run multi-service cluster locally using process supervisor."""
    print("=" * 70)
    print("🚀 DEPLOYING AGENTECOM MULTI-SERVICE CLUSTER (LOCAL SUPERVISOR)")
    print("=" * 70)
    print("Initializing services in synchronized mode:\n")

    processes = []

    try:
        # 1. Start Commerce API & Storefront on port 8000
        print("  [1/3] Starting Commerce API & Storefront (port 8000)...")
        api_proc = subprocess.Popen(
            [PYTHON_EXE, "-m", "uvicorn", "agentecom.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
        )
        processes.append(("Commerce API", api_proc))

        # 2. Start Dedicated FastMCP Microservice on port 8001
        print("  [2/3] Starting Dedicated FastMCP Server (port 8001)...")
        mcp_proc = subprocess.Popen(
            [PYTHON_EXE, "-m", "uvicorn", "agentecom.mcp.service:app", "--host", "0.0.0.0", "--port", "8001"]
        )
        processes.append(("FastMCP Server", mcp_proc))

        # 3. Start Search & Catalog Indexing Worker
        print("  [3/3] Starting Asynchronous Indexing Worker Daemon...")
        worker_proc = subprocess.Popen(
            [PYTHON_EXE, "-m", "agentecom.search.run_worker"]
        )
        processes.append(("Search Worker", worker_proc))

        print("\n" + "=" * 70)
        print("🟢 ALL SERVICES ARE DEPLOYED AND SYNCHRONIZED!")
        print("=" * 70)
        print("  * Storefront & AI Chat:    http://localhost:8000")
        print("  * Swagger API Docs:        http://localhost:8000/docs")
        print("  * FastMCP SSE Endpoint:    http://localhost:8001/sse")
        print("  * FastMCP Health Probe:    http://localhost:8001/health")
        print("  * Search Indexing Worker:  Active (auto-indexes updates)")
        print("\nPress Ctrl+C to stop all cluster services gracefully.\n")

        # Keep alive and monitor child processes
        while True:
            time.sleep(2)
            for name, proc in processes:
                poll = proc.poll()
                if poll is not None:
                    print(f"⚠️ Service '{name}' exited with return code {poll}.")
                    raise KeyboardInterrupt

    except KeyboardInterrupt:
        print("\n🛑 Shutting down cluster services...")
        for name, proc in processes:
            try:
                proc.terminate()
            except Exception:
                pass
        for name, proc in processes:
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        print("✅ All services stopped cleanly.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--docker":
        deploy_docker()
    elif is_docker_running():
        print("Docker Desktop daemon detected!")
        choice = input("Deploy via Docker Compose? [Y/n]: ").strip().lower()
        if choice in ["", "y", "yes"]:
            deploy_docker()
        else:
            run_local_cluster()
    else:
        run_local_cluster()
