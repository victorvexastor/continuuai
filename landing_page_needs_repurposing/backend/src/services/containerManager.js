import Docker from 'dockerode';

const docker = new Docker({ socketPath: process.env.DOCKER_HOST || '/var/run/docker.sock' });

/**
 * Container Manager Service
 * Handles Docker container lifecycle for Jupyter sessions
 */
class ContainerManager {
    constructor() {
        this.containers = new Map();
        this.availableGPUs = new Set([0, 1, 2, 3]); // Track GPU availability
    }

    /**
     * Create and start a new Jupyter container
     */
    async createContainer(sessionId, userId) {
        try {
            const gpuId = this.allocateGPU();
            if (gpuId === null) {
                throw new Error('No GPUs available');
            }

            const port = 8000 + Math.floor(Math.random() * 1000);
            const workspacePath = `/data/workspaces/${userId}/${sessionId}`;

            // Container configuration
            const config = {
                Image: process.env.JUPYTER_IMAGE || 'jupyter/tensorflow-notebook:latest',
                name: `neuais-session-${sessionId}`,
                Env: [
                    `JUPYTER_TOKEN=${sessionId}`,
                    `NVIDIA_VISIBLE_DEVICES=${gpuId}`
                ],
                ExposedPorts: {
                    '8888/tcp': {}
                },
                HostConfig: {
                    PortBindings: {
                        '8888/tcp': [{ HostPort: port.toString() }]
                    },
                    Binds: [
                        `${workspacePath}:/home/jovyan/work`
                    ],
                    DeviceRequests: [
                        {
                            Driver: 'nvidia',
                            Count: 1,
                            DeviceIDs: [gpuId.toString()],
                            Capabilities: [['gpu']]
                        }
                    ],
                    Memory: 8 * 1024 * 1024 * 1024, // 8GB
                    NanoCPUs: 4 * 1000000000 // 4 CPUs
                }
            };

            // Simulated creation for development
            // In production, uncomment the next lines:
            // const container = await docker.createContainer(config);
            // await container.start();

            const containerInfo = {
                id: `container-${sessionId}`,
                sessionId,
                port,
                gpuIds: [gpuId],
                status: 'running',
                createdAt: new Date().toISOString()
            };

            this.containers.set(sessionId, containerInfo);

            console.log(`✅ Container created for session ${sessionId} on port ${port} with GPU ${gpuId}`);

            return containerInfo;
        } catch (error) {
            console.error('Error creating container:', error);
            throw error;
        }
    }

    /**
     * Stop and remove a container
     */
    async stopContainer(containerId) {
        try {
            const sessionId = containerId.replace('container-', '');
            const containerInfo = this.containers.get(sessionId);

            if (!containerInfo) {
                throw new Error('Container not found');
            }

            // Release GPU
            if (containerInfo.gpuIds && containerInfo.gpuIds.length > 0) {
                this.availableGPUs.add(containerInfo.gpuIds[0]);
            }

            // Simulated for development
            // In production, uncomment:
            // const container = docker.getContainer(containerId);
            // await container.stop();
            // await container.remove();

            this.containers.delete(sessionId);

            console.log(`🛑 Container ${containerId} stopped`);

            return { success: true };
        } catch (error) {
            console.error('Error stopping container:', error);
            throw error;
        }
    }

    /**
     * Get container statistics
     */
    async getContainerStats(containerId) {
        try {
            // Simulated stats for development
            // In production, replace with real Docker stats
            return {
                gpuMemory: '2.4GB / 40GB',
                gpuUtilization: '15%',
                cpuUsage: '12%',
                memoryUsage: '1.2GB / 8GB',
                uptime: this.getUptime(containerId)
            };
        } catch (error) {
            console.error('Error fetching stats:', error);
            return null;
        }
    }

    /**
     * Get container logs
     */
    async getContainerLogs(containerId) {
        try {
            // Simulated for development
            // In production, use docker.getContainer(containerId).logs()
            return [
                '[NeuAIs Colab] Container started successfully',
                '[Jupyter] Notebook server running on port 8888',
                '[GPU] CUDA device initialized',
                '[Ready] Environment ready for computation'
            ].join('\n');
        } catch (error) {
            console.error('Error fetching logs:', error);
            return '';
        }
    }

    /**
     * Allocate an available GPU
     */
    allocateGPU() {
        if (this.availableGPUs.size === 0) {
            return null;
        }

        const gpuId = Array.from(this.availableGPUs)[0];
        this.availableGPUs.delete(gpuId);
        return gpuId;
    }

    /**
     * Calculate container uptime
     */
    getUptime(containerId) {
        const sessionId = containerId.replace('container-', '');
        const container = this.containers.get(sessionId);

        if (!container) return '00:00:00';

        const start = new Date(container.createdAt);
        const now = new Date();
        const diff = now - start;

        const hours = Math.floor(diff / 3600000);
        const minutes = Math.floor((diff % 3600000) / 60000);
        const seconds = Math.floor((diff % 60000) / 1000);

        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }

    /**
     * List all active containers
     */
    listContainers() {
        return Array.from(this.containers.values());
    }
}

export default new ContainerManager();
