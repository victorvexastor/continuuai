import express from 'express';
import { v4 as uuidv4 } from 'uuid';
import containerManager from '../services/containerManager.js';

const router = express.Router();

// In-memory sessions store (replace with database in production)
const sessions = new Map();

/**
 * POST /api/sessions/create
 * Create a new notebook session
 */
router.post('/create', async (req, res) => {
    const { userId, bookingId, notebookName } = req.body;

    try {
        const sessionId = uuidv4();

        // Create container (simulated for now)
        const containerInfo = await containerManager.createContainer(sessionId, userId);

        const session = {
            id: sessionId,
            userId,
            bookingId,
            name: notebookName || 'Untitled Notebook',
            containerId: containerInfo.id,
            port: containerInfo.port,
            gpuIds: containerInfo.gpuIds,
            status: 'creating',
            workspacePath: `/data/workspaces/${userId}/${sessionId}`,
            createdAt: new Date().toISOString()
        };

        sessions.set(sessionId, session);

        // Update status to running after container starts
        setTimeout(() => {
            if (sessions.has(sessionId)) {
                session.status = 'running';
                sessions.set(sessionId, session);
            }
        }, 5000);

        res.status(201).json({ session });
    } catch (error) {
        console.error('Error creating session:', error);
        res.status(500).json({ error: 'Failed to create session' });
    }
});

/**
 * GET /api/sessions/:id
 * Get session details
 */
router.get('/:id', async (req, res) => {
    const { id } = req.params;

    const session = sessions.get(id);

    if (!session) {
        return res.status(404).json({ error: 'Session not found' });
    }

    // Get real-time stats from container
    const stats = await containerManager.getContainerStats(session.containerId);

    res.json({
        session: {
            ...session,
            stats
        }
    });
});

/**
 * DELETE /api/sessions/:id
 * Terminate a session
 */
router.delete('/:id', async (req, res) => {
    const { id } = req.params;

    const session = sessions.get(id);

    if (!session) {
        return res.status(404).json({ error: 'Session not found' });
    }

    try {
        // Stop and remove container
        await containerManager.stopContainer(session.containerId);

        session.status = 'terminated';
        session.terminatedAt = new Date().toISOString();

        sessions.set(id, session);

        res.json({ message: 'Session terminated', session });
    } catch (error) {
        console.error('Error terminating session:', error);
        res.status(500).json({ error: 'Failed to terminate session' });
    }
});

/**
 * POST /api/sessions/:id/save
 * Save notebook state
 */
router.post('/:id/save', async (req, res) => {
    const { id } = req.params;
    const { cells, metadata } = req.body;

    const session = sessions.get(id);

    if (!session) {
        return res.status(404).json({ error: 'Session not found' });
    }

    try {
        // Save to storage (simulated)
        const notebookData = {
            sessionId: id,
            cells,
            metadata,
            savedAt: new Date().toISOString()
        };

        console.log('Saving notebook:', notebookData);

        res.json({ message: 'Notebook saved', savedAt: notebookData.savedAt });
    } catch (error) {
        console.error('Error saving notebook:', error);
        res.status(500).json({ error: 'Failed to save notebook' });
    }
});

/**
 * GET /api/sessions/:id/logs
 * Get container logs
 */
router.get('/:id/logs', async (req, res) => {
    const { id } = req.params;

    const session = sessions.get(id);

    if (!session) {
        return res.status(404).json({ error: 'Session not found' });
    }

    try {
        const logs = await containerManager.getContainerLogs(session.containerId);
        res.json({ logs });
    } catch (error) {
        console.error('Error fetching logs:', error);
        res.status(500).json({ error: 'Failed to fetch logs' });
    }
});

/**
 * GET /api/sessions/user/:userId
 * Get all sessions for a user
 */
router.get('/user/:userId', (req, res) => {
    const { userId } = req.params;

    const userSessions = Array.from(sessions.values()).filter(
        session => session.userId === userId
    );

    res.json({ sessions: userSessions });
});

export default router;
