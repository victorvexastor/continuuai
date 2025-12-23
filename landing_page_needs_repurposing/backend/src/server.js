import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import dotenv from 'dotenv';
import { createServer } from 'http';
import { Server as SocketIOServer } from 'socket.io';

// Import routes
import authRoutes from './routes/auth.js';
import calendarRoutes from './routes/calendar.js';
import sessionsRoutes from './routes/sessions.js';

// Import middleware
import { errorHandler } from './middleware/error.js';
import { rateLimiter } from './middleware/rateLimiter.js';

dotenv.config();

const app = express();
const httpServer = createServer(app);
const PORT = process.env.PORT || 5000;

// WebSocket server
const io = new SocketIOServer(httpServer, {
    cors: {
        origin: process.env.FRONTEND_URL || 'http://localhost:3000',
        methods: ['GET', 'POST']
    }
});

// Middleware
app.use(helmet());
app.use(cors({
    origin: process.env.FRONTEND_URL || 'http://localhost:3000',
    credentials: true
}));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(rateLimiter);

// Routes
app.use('/api/auth', authRoutes);
app.use('/api/calendar', calendarRoutes);
app.use('/api/sessions', sessionsRoutes);

// Health check
app.get('/api/health', (req, res) => {
    res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        uptime: process.uptime()
    });
});

// WebSocket handling
io.on('connection', (socket) => {
    console.log('Client connected:', socket.id);

    socket.on('join-session', (sessionId) => {
        socket.join(`session-${sessionId}`);
        console.log(`Socket ${socket.id} joined session ${sessionId}`);
    });

    socket.on('code-execution', async (data) => {
        // Broadcast to other users in the same session
        socket.to(`session-${data.sessionId}`).emit('code-executed', data);
    });

    socket.on('cell-update', (data) => {
        // Broadcast cell updates for collaboration
        socket.to(`session-${data.sessionId}`).emit('cell-updated', data);
    });

    socket.on('disconnect', () => {
        console.log('Client disconnected:', socket.id);
    });
});

// Error handling
app.use(errorHandler);

// Start server
httpServer.listen(PORT, () => {
    console.log(`🚀 NeuAIs Colab Server running on port ${PORT}`);
    console.log(`📊 Environment: ${process.env.NODE_ENV || 'development'}`);
    console.log(`🌐 CORS enabled for: ${process.env.FRONTEND_URL || 'http://localhost:3000'}`);
});

export { io };
export default app;
